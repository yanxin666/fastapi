# fastapi

后台管理全栈项目：
- 后端：FastAPI + SQLAlchemy + PostgreSQL + Alembic
- 前端：React + TypeScript + Vite + Ant Design

推荐统一使用项目根目录的 `Makefile` 管理依赖与启停，兼容 macOS / Windows。

## 快速开始（推荐）

### 1) 创建虚拟环境

```bash
make venv
```

### 2) 安装依赖

```bash
make install-backend
make install-frontend
```

或一键安装：

```bash
make install-all
```

### 3) 启动开发服务

前后端分别在两个终端启动：

```bash
make run-backend
make run-frontend
```

### 4) 一键后台启动（含日志和 PID）

```bash
make run-all-bg
```

后台模式会生成：
- `.run/backend.log`
- `.run/frontend.log`
- `.run/backend.pid`
- `.run/frontend.pid`

### 5) 查看状态与停止

```bash
make status
make stop-backend
make stop-frontend
make stop-all
```

## 常用 Make 命令

```bash
make help
make lock-backend
make add-backend PKG=fastapi
```

说明：
- `make add-backend PKG=xxx` 会执行安装并更新 `requirements.txt`
- `make lock-backend` 会把当前虚拟环境依赖重新冻结到 `requirements.txt`

## 镜像源配置（可选）

可在执行 Make 命令时临时覆盖：

```bash
make install-backend PYPI_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
make install-frontend NPM_REGISTRY=https://registry.npmmirror.com
```

## 不使用 Make 的等价命令（参考）

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
npm --prefix frontend install
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm --prefix frontend install
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如遇 PowerShell 执行策略问题，可执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
