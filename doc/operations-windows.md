# CRM 系统 Windows 开发环境操作手册

适用环境：Windows 10/11 本地开发

> **前端开发的详细说明**（依赖安装、开发调试、构建、测试等）请参见 [operations-frontend-windows.md](operations-frontend-windows.md)。

---

## 目录

1. [环境准备](#1-环境准备)
2. [启动服务](#2-启动服务)
3. [关闭服务](#3-关闭服务)
4. [重启服务](#4-重启服务)
5. [数据库操作](#5-数据库操作)
6. [前端构建](#6-前端构建)
7. [Tailscale Funnel（外网临时访问）](#7-tailscale-funnel外网临时访问)
8. [故障排查](#8-故障排查)
9. [命令速查表](#9-命令速查表)

---

## 1. 环境准备

### 前置依赖

| 依赖 | 最低版本 | 验证命令 |
|------|---------|---------|
| Python | 3.11+ | `python --version` 或 `py -3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Make | — | `make --version`（推荐通过 [choco](https://chocolatey.org/) 安装） |

> 如果没有 Make，也可以直接使用下方"直接命令"方式，所有 Make 命令都有对应的直接命令等价写法。

### 首次初始化

```bash
# 1. 创建 Python 虚拟环境
make venv

# 2. 安装后端依赖（包含开发工具：pytest、black、isort 等）
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt

# 3. 安装前端依赖
make install-frontend

# 4. 创建 .env 配置文件
```

### .env 配置

在项目根目录创建 `.env` 文件：

```ini
# 数据库连接
APP_DATABASE_URL=postgresql+psycopg://postgres:yanxin@localhost:5432/postgre

# JWT 密钥（本地开发用默认值即可）
APP_JWT_SECRET_KEY=change-this-secret-in-production

# Token 有效期
APP_ACCESS_TOKEN_TTL_MINUTES=30
APP_REFRESH_TOKEN_TTL_DAYS=7
```

> `.env` 已在 `.gitignore` 中，不会被提交到仓库。

---

## 2. 启动服务

前后端需要分别启动，开发时都带有热重载功能。

### 方式一：Make 命令（推荐）

```bash
# 启动后端（带热重载，占一个终端窗口）
make run-backend

# 启动前端（带热重载，另开一个终端窗口）
make run-frontend
```

### 方式二：一键后台启动

```bash
# 后台同时启动前后端，日志输出到 .run/ 目录
make run-all-bg

# 查看进程状态
make status
```

### 方式三：直接命令

```bash
# 后端
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端（新终端窗口）
npm --prefix frontend run dev
```

### 启动后访问

| 服务 | 地址 |
|------|------|
| 前端开发页面 | http://localhost:5173 |
| 后端 API | http://127.0.0.1:8000 |
| API 文档（Swagger） | http://127.0.0.1:8000/docs |

---

## 3. 关闭服务

### 前台模式

在运行 `make run-backend` 或 `make run-frontend` 的终端窗口中按 `Ctrl+C`，或直接关闭窗口。

### 后台模式

```bash
# 关闭后端
make stop-backend

# 关闭前端
make stop-frontend

# 一键关闭前后端
make stop-all
```

---

## 4. 重启服务

### 前台模式

在对应终端窗口 `Ctrl+C` 停止后，重新执行启动命令即可。

### 后台模式

```bash
make stop-all && make run-all-bg
```

### 使用 Tailscale Funnel

如果之前通过 Funnel 暴露了服务，使用专用重启脚本：

```bash
restart_funnel.cmd
```

---

## 5. 数据库操作

### 生成迁移文件

修改 Model 后，生成对应的 Alembic 迁移文件：

```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "描述变更内容"
```

### 执行迁移

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

### 同步权限数据

新增权限码后需要同步到数据库：

```bash
make seed-permissions
```

### 导入客户数据

```bash
make import-customers
```

> **警告**：数据库迁移、权限同步、数据导入都会修改数据库内容，执行前请确认连接的是正确的数据库。

---

## 6. 前端构建

### 开发模式

开发时使用 Vite 开发服务器，支持热重载：

```bash
make run-frontend
# 或
npm --prefix frontend run dev
```

### 生产构建

将前端源码编译为静态文件，输出到 `frontend/dist`：

```bash
npm --prefix frontend run build
```

构建后，后端开发服务（uvicorn）会自动托管 `frontend/dist`，访问 http://127.0.0.1:8000 即可看到构建后的前端页面。

> **注意**：开发时推荐使用前端开发服务器（端口 5173），它支持热重载。生产构建仅用于验证或部署。

---

## 7. Tailscale Funnel（外网临时访问）

用于将本地开发服务临时暴露到公网，方便外部测试或演示。

### 前提

- 已安装 Tailscale 客户端并登录
- 验证：`tailscale status`

### 启动

```bash
start_funnel.cmd
```

该脚本会依次：
1. 检查项目目录和 Python 环境
2. 在新窗口启动后端服务
3. 配置 Tailscale Serve（本地代理）
4. 启用 Tailscale Funnel（公网暴露）

启动成功后会显示：
- 本地地址：http://127.0.0.1:8000
- 公网地址：https://xxx.tailxxx.ts.net

### 关闭

```bash
stop_funnel.cmd
```

关闭 Funnel 后，后端服务窗口需要手动关闭。

### 重启

```bash
restart_funnel.cmd
```

等同于先 `stop_funnel.cmd` 再 `start_funnel.cmd`。

---

## 8. 故障排查

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| `python not found` | 确保已创建虚拟环境：`make venv` |
| `make not found` | 安装 Make（推荐 choco：`choco install make`），或使用直接命令代替 |
| `npm not found` | 安装 Node.js 并确保在 PATH 中 |
| 端口 8000 被占用 | 指定其他端口：`make run-backend BACKEND_PORT=8001` |
| 端口 5173 被占用 | Vite 会自动尝试下一个可用端口（5174、5175...） |
| 前端修改不生效 | 开发模式下检查是否在 http://localhost:5173 访问 |
| 后端 API 404 | 确认后端服务正在运行，检查请求路径是否以 `/api/v1/admin` 开头 |
| 数据库连接失败 | 检查 `.env` 中 `APP_DATABASE_URL`，确认 PostgreSQL 服务正在运行 |
| `psycopg` 相关报错 | 确认安装了 `psycopg[binary]`：`.venv/Scripts/pip.exe install "psycopg[binary]>=3.1"` |
| `ModuleNotFoundError` | 确认在虚拟环境中运行：`.venv/Scripts/python.exe` 而非系统 Python |

### 查看后台进程日志

```bash
# 后台模式的日志位于 .run/ 目录
cat .run/backend.log
cat .run/frontend.log
```

---

## 9. 命令速查表

| 操作 | Make 命令 | 直接命令 |
|------|----------|---------|
| 创建虚拟环境 | `make venv` | `py -3 -m venv .venv` |
| 安装后端依赖 | — | `.venv/Scripts/python.exe -m pip install -r requirements-dev.txt` |
| 安装前端依赖 | `make install-frontend` | `npm --prefix frontend install` |
| 启动后端 | `make run-backend` | `.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| 启动前端 | `make run-frontend` | `npm --prefix frontend run dev` |
| 后台启动前后端 | `make run-all-bg` | — |
| 停止后端 | `make stop-backend` | 关闭窗口或 `Ctrl+C` |
| 停止前端 | `make stop-frontend` | 关闭窗口或 `Ctrl+C` |
| 停止全部 | `make stop-all` | — |
| 查看进程状态 | `make status` | — |
| 前端构建 | — | `npm --prefix frontend run build` |
| 数据库迁移 | — | `.venv/Scripts/python.exe -m alembic upgrade head` |
| 生成迁移文件 | — | `.venv/Scripts/python.exe -m alembic revision --autogenerate -m "描述"` |
| 同步权限 | `make seed-permissions` | — |
| 导入客户 | `make import-customers` | — |
| 启动 Funnel | — | `start_funnel.cmd` |
| 关闭 Funnel | — | `stop_funnel.cmd` |
| 重启 Funnel | — | `restart_funnel.cmd` |
