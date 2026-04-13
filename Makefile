# Cross-platform Makefile (macOS + Windows)

# 使用方式：
# 1) 安装后端依赖: make install-backend
# 2) 安装前端依赖: make install-frontend
# 3) 一键安装前后端: make install-all
# 4) 安装单个后端包并更新 requirements: make add-backend PKG=xxx

PYPI_INDEX_URL ?= https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY ?= https://registry.npmmirror.com

FRONTEND_DIR := frontend
VENV_DIR := .venv
RUN_DIR := .run
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000

ifeq ($(OS),Windows_NT)
	BOOTSTRAP_PYTHON := py -3
	VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
	VENV_PIP := $(VENV_DIR)/Scripts/pip.exe
else
	BOOTSTRAP_PYTHON := python3
	VENV_PYTHON := $(VENV_DIR)/bin/python
	VENV_PIP := $(VENV_DIR)/bin/pip
endif

.PHONY: help venv install-backend install-frontend install-all add-backend lock-backend run-backend run-frontend run-all-bg stop-backend stop-frontend run-all stop-all status seed-permissions import-customers

help:
	@echo "可用命令:"
	@echo "  make venv                          # 创建虚拟环境"
	@echo "  make install-backend               # 安装后端 requirements.txt"
	@echo "  make add-backend PKG=fastapi       # 安装单个后端依赖并写入 requirements.txt"
	@echo "  make lock-backend                  # 锁定当前后端依赖到 requirements.txt"
	@echo "  make install-frontend              # 安装前端依赖(frontend/package.json)"
	@echo "  make install-all                   # 安装前后端依赖"
	@echo "  make run-backend                   # 运行后端开发服务(uvicorn)"
	@echo "  make run-frontend                  # 运行前端开发服务(vite dev)"
	@echo "  make run-all-bg                    # 后台启动前后端并输出日志路径"
	@echo "  make stop-backend                  # 关闭后端开发服务"
	@echo "  make stop-frontend                 # 关闭前端开发服务"
	@echo "  make stop-all                      # 关闭前后端开发服务"
	@echo "  make status                        # 查看前后端进程状态"
	@echo "  make seed-permissions              # 同步权限码到数据库"
	@echo "  make import-customers              # 从 CSV 导入客户数据到数据库"

venv:
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

install-backend:
	$(VENV_PYTHON) -m pip install -r requirements.txt -i $(PYPI_INDEX_URL)

add-backend:
ifndef PKG
	$(error 请传入 PKG, 例如: make add-backend PKG=fastapi)
endif
	$(VENV_PYTHON) -m pip install $(PKG) -i $(PYPI_INDEX_URL)
	$(VENV_PYTHON) -m pip freeze > requirements.txt

lock-backend:
	$(VENV_PYTHON) -m pip freeze > requirements.txt

install-frontend:
	npm --prefix $(FRONTEND_DIR) config set registry $(NPM_REGISTRY)
	npm --prefix $(FRONTEND_DIR) install

install-all: install-backend install-frontend

run-backend:
	$(VENV_PYTHON) -m uvicorn app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

run-frontend:
	npm --prefix $(FRONTEND_DIR) run dev

run-all-bg:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -Command "New-Item -ItemType Directory -Path '$(RUN_DIR)' -Force | Out-Null; $$b = Start-Process -FilePath '$(VENV_PYTHON)' -ArgumentList '-m','uvicorn','app.main:app','--reload','--host','$(BACKEND_HOST)','--port','$(BACKEND_PORT)' -RedirectStandardOutput '$(RUN_DIR)/backend.log' -RedirectStandardError '$(RUN_DIR)/backend.log' -PassThru; $$b.Id | Out-File -Encoding ascii '$(RUN_DIR)/backend.pid'; $$f = Start-Process -FilePath 'npm' -ArgumentList '--prefix','$(FRONTEND_DIR)','run','dev' -RedirectStandardOutput '$(RUN_DIR)/frontend.log' -RedirectStandardError '$(RUN_DIR)/frontend.log' -PassThru; $$f.Id | Out-File -Encoding ascii '$(RUN_DIR)/frontend.pid'; Write-Host '后台启动完成'; Write-Host 'backend pid:' $$b.Id 'log: $(RUN_DIR)/backend.log'; Write-Host 'frontend pid:' $$f.Id 'log: $(RUN_DIR)/frontend.log'"
else
	@mkdir -p $(RUN_DIR)
	@nohup $(VENV_PYTHON) -m uvicorn app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT) > $(RUN_DIR)/backend.log 2>&1 & echo $$! > $(RUN_DIR)/backend.pid
	@nohup npm --prefix $(FRONTEND_DIR) run dev > $(RUN_DIR)/frontend.log 2>&1 & echo $$! > $(RUN_DIR)/frontend.pid
	@echo "后台启动完成"
	@echo "backend pid: $$(cat $(RUN_DIR)/backend.pid), log: $(RUN_DIR)/backend.log"
	@echo "frontend pid: $$(cat $(RUN_DIR)/frontend.pid), log: $(RUN_DIR)/frontend.log"
endif

stop-backend:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -Command "$$pidPath = '$(RUN_DIR)/backend.pid'; if (Test-Path $$pidPath) { $$pid = Get-Content $$pidPath -ErrorAction SilentlyContinue; if ($$pid) { $$proc = Get-Process -Id $$pid -ErrorAction SilentlyContinue; if ($$proc) { Stop-Process -Id $$pid -Force; Write-Host '已按 PID 关闭后端:' $$pid } }; Remove-Item $$pidPath -Force -ErrorAction SilentlyContinue } else { $$p = Get-CimInstance Win32_Process | Where-Object { $$_.CommandLine -match 'uvicorn\s+app.main:app' }; if ($$p) { $$p | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force }; Write-Host '已按进程名关闭后端' } }"
else
	@if [ -f $(RUN_DIR)/backend.pid ]; then \
		PID=$$(cat $(RUN_DIR)/backend.pid); \
		if kill -0 $$PID 2>/dev/null; then kill $$PID 2>/dev/null || true; echo "已按 PID 关闭后端: $$PID"; fi; \
		rm -f $(RUN_DIR)/backend.pid; \
	else \
		pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true; \
	fi
endif

stop-frontend:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -Command "$$pidPath = '$(RUN_DIR)/frontend.pid'; if (Test-Path $$pidPath) { $$pid = Get-Content $$pidPath -ErrorAction SilentlyContinue; if ($$pid) { $$proc = Get-Process -Id $$pid -ErrorAction SilentlyContinue; if ($$proc) { Stop-Process -Id $$pid -Force; Write-Host '已按 PID 关闭前端:' $$pid } }; Remove-Item $$pidPath -Force -ErrorAction SilentlyContinue } else { $$p = Get-CimInstance Win32_Process | Where-Object { $$_.CommandLine -match 'vite' -or $$_.CommandLine -match 'npm\s+.*run\s+dev' }; if ($$p) { $$p | ForEach-Object { Stop-Process -Id $$_.ProcessId -Force }; Write-Host '已按进程名关闭前端' } }"
else
	@if [ -f $(RUN_DIR)/frontend.pid ]; then \
		PID=$$(cat $(RUN_DIR)/frontend.pid); \
		if kill -0 $$PID 2>/dev/null; then kill $$PID 2>/dev/null || true; echo "已按 PID 关闭前端: $$PID"; fi; \
		rm -f $(RUN_DIR)/frontend.pid; \
	else \
		pkill -9 -f "vite" 2>/dev/null || true; \
	fi
endif

run-all:
	@echo "请分别在两个终端执行: make run-backend 和 make run-frontend"

stop-all: stop-backend stop-frontend

seed-permissions:
	$(VENV_PYTHON) -c "from app.core.db import get_session_factory; from app.authz.seed import seed_permissions; db = get_session_factory()(); \
	try: \
		seed_permissions(db); db.commit(); print('权限码已同步到数据库'); \
	except Exception as e: \
		db.rollback(); print(f'同步失败: {e}'); raise; \
	finally: \
		db.close()"

status:
ifeq ($(OS),Windows_NT)
	powershell -NoProfile -Command "$$bp = '$(RUN_DIR)/backend.pid'; $$fp = '$(RUN_DIR)/frontend.pid'; if (Test-Path $$bp) { $$bpid = Get-Content $$bp; if (Get-Process -Id $$bpid -ErrorAction SilentlyContinue) { Write-Host 'backend: running pid=' $$bpid } else { Write-Host 'backend: pid file exists but process not running' } } else { Write-Host 'backend: no pid file' }; if (Test-Path $$fp) { $$fpid = Get-Content $$fp; if (Get-Process -Id $$fpid -ErrorAction SilentlyContinue) { Write-Host 'frontend: running pid=' $$fpid } else { Write-Host 'frontend: pid file exists but process not running' } } else { Write-Host 'frontend: no pid file' }"
else
	@if [ -f $(RUN_DIR)/backend.pid ]; then \
		PID=$$(cat $(RUN_DIR)/backend.pid); \
		if kill -0 $$PID 2>/dev/null; then echo "backend: running pid=$$PID"; else echo "backend: pid 文件存在但进程未运行"; fi; \
	else echo "backend: 无 pid 文件"; fi
	@if [ -f $(RUN_DIR)/frontend.pid ]; then \
		PID=$$(cat $(RUN_DIR)/frontend.pid); \
		if kill -0 $$PID 2>/dev/null; then echo "frontend: running pid=$$PID"; else echo "frontend: pid 文件存在但进程未运行"; fi; \
	else echo "frontend: 无 pid 文件"; fi
endif


import-customers:
	$(VENV_PYTHON) scripts/import_customers.py
