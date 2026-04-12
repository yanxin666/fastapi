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

ifeq ($(OS),Windows_NT)
	BOOTSTRAP_PYTHON := py -3
	VENV_PYTHON := $(VENV_DIR)/Scripts/python.exe
	VENV_PIP := $(VENV_DIR)/Scripts/pip.exe
else
	BOOTSTRAP_PYTHON := python3
	VENV_PYTHON := $(VENV_DIR)/bin/python
	VENV_PIP := $(VENV_DIR)/bin/pip
endif

.PHONY: help venv install-backend install-frontend install-all add-backend lock-backend

help:
	@echo "可用命令:"
	@echo "  make venv                          # 创建虚拟环境"
	@echo "  make install-backend               # 安装后端 requirements.txt"
	@echo "  make add-backend PKG=fastapi       # 安装单个后端依赖并写入 requirements.txt"
	@echo "  make lock-backend                  # 锁定当前后端依赖到 requirements.txt"
	@echo "  make install-frontend              # 安装前端依赖(frontend/package.json)"
	@echo "  make install-all                   # 安装前后端依赖"

venv:
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

install-backend:
	$(VENV_PYTHON) -m pip install -r requirements.txt -i $(PYPI_INDEX_URL)

add-backend:
	@if [ -z "$(PKG)" ]; then echo "请传入 PKG，例如: make add-backend PKG=fastapi"; exit 1; fi
	$(VENV_PYTHON) -m pip install $(PKG) -i $(PYPI_INDEX_URL)
	$(VENV_PYTHON) -m pip freeze > requirements.txt

lock-backend:
	$(VENV_PYTHON) -m pip freeze > requirements.txt

install-frontend:
	npm --prefix $(FRONTEND_DIR) config set registry $(NPM_REGISTRY)
	npm --prefix $(FRONTEND_DIR) install

install-all: install-backend install-frontend
