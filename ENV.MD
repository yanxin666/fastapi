# ENV.MD

## 用途

本文档用于说明当前项目迁移到其他 Windows 电脑时，所需的系统环境、运行依赖、环境变量、初始化步骤与验证命令。

项目类型：

- 后端：FastAPI + SQLAlchemy + PostgreSQL + Alembic
- 前端：React + TypeScript + Vite + Ant Design
- 前端构建产物：`frontend/dist`，由 FastAPI 直接托管

---

## 1. Windows 机器基础环境

建议目标机器至少具备以下软件：

| 组件         | 当前环境版本                    | 说明        |
|------------|---------------------------|-----------|
| Windows    | Windows 10 Pro 10.0.19045 | 当前开发机系统   |
| Python     | 3.12.3                    | 后端运行环境    |
| Node.js    | 24.14.1                   | 前端构建与测试   |
| npm        | 11.11.0                   | 前端包管理     |
| PostgreSQL | 需安装本地或可访问实例               | 后端主数据库    |
| Git        | 建议安装                      | 方便拉取与更新项目 |

> 建议新机器优先安装与当前一致的大版本：Python 3.12.x、Node.js 24.x、npm 11.x。

---

## 2. 当前项目所需后端依赖

### 2.1 Python 虚拟环境

在项目根目录执行：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
```

### 2.2 安装 Python 依赖

当前仓库已有：

- `requirements.txt`

Windows 机器优先使用：

```cmd
pip install -r requirements.txt
```

### 2.3 额外说明

当前代码实际运行还依赖以下核心包：

- `SQLAlchemy==2.0.44`
- `alembic==1.18.4`
- `psycopg==3.2.12`
- `psycopg-binary==3.2.12`
- `PyJWT==2.10.1`

其中：

- `SQLAlchemy`：ORM 与数据库会话管理
- `alembic`：数据库迁移
- `psycopg` / `psycopg-binary`：PostgreSQL 驱动
- `PyJWT`：JWT 编解码

---

## 3. 当前项目所需前端依赖

前端目录：`frontend`

初始化命令：

```cmd
npm --prefix "D:/project/python/fastapi/frontend" install
```

当前前端直接依赖与开发依赖如下：

### 3.1 前端运行依赖

- `antd@6.3.5`
- `react@19.2.5`
- `react-dom@19.2.5`
- `react-router-dom@7.14.0`

### 3.2 前端开发 / 构建 / 测试依赖

- `@eslint/js@9.39.4`
- `@testing-library/jest-dom@6.9.1`
- `@testing-library/react@16.3.2`
- `@testing-library/user-event@14.6.1`
- `@types/node@24.12.2`
- `@types/react@19.2.14`
- `@types/react-dom@19.2.3`
- `@vitejs/plugin-react@6.0.1`
- `@vitest/coverage-v8@4.1.4`
- `eslint@9.39.4`
- `eslint-plugin-react-hooks@7.0.1`
- `eslint-plugin-react-refresh@0.5.2`
- `globals@17.4.0`
- `jsdom@29.0.2`
- `typescript@6.0.2`
- `typescript-eslint@8.58.1`
- `vite@8.0.8`
- `vitest@4.1.4`

---

## 4. 数据库依赖

项目当前使用 PostgreSQL。

### 4.1 当前连接方式

代码默认数据库连接配置位于：

- `app/core/config.py`

配置项：

- `APP_DATABASE_URL`

连接串格式：

```text
postgresql+psycopg://<用户名>:<密码>@<主机>:<端口>/<数据库名>
```

示例：

```text
postgresql+psycopg://postgres:your_password@localhost:5432/postgre
```

### 4.2 迁移到新机器前需要准备

- 已安装 PostgreSQL
- 已创建目标数据库
- 已确认用户名、密码、端口可用
- 可通过 `APP_DATABASE_URL` 正确连接

### 4.3 初始化数据库结构

安装完依赖并配置好 `.env` 后执行：

```cmd
.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 5. 环境变量

项目配置使用：

- 环境变量前缀：`APP_`
- 配置文件：项目根目录 `.env`

当前仓库里 **没有现成的 `.env` 文件**，迁移到新机器时需要手动新建。

推荐新建 `D:\project\python\fastapi\.env`，内容示例：

```env
APP_APP_NAME=FastAPI Service
APP_APP_ENV=development
APP_APP_VERSION=0.1.0
APP_API_V1_PREFIX=/api/v1
APP_DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/postgre
APP_JWT_SECRET_KEY=replace-with-a-long-random-secret
APP_JWT_ALGORITHM=HS256
APP_ACCESS_TOKEN_TTL_MINUTES=30
APP_REFRESH_TOKEN_TTL_DAYS=7
```

### 5.1 配置项说明

| 变量名                            | 默认值                                | 是否建议显式配置 | 说明                 |
|--------------------------------|------------------------------------|----------|--------------------|
| `APP_APP_NAME`                 | `FastAPI Service`                  | 否        | 应用名称               |
| `APP_APP_ENV`                  | `development`                      | 建议       | 运行环境标识             |
| `APP_APP_VERSION`              | `0.1.0`                            | 否        | 应用版本               |
| `APP_API_V1_PREFIX`            | `/api/v1`                          | 否        | API 前缀             |
| `APP_DATABASE_URL`             | 代码内有本地默认值                          | **强烈建议** | PostgreSQL 连接串     |
| `APP_JWT_SECRET_KEY`           | `change-this-secret-in-production` | **强烈建议** | JWT 密钥             |
| `APP_JWT_ALGORITHM`            | `HS256`                            | 否        | JWT 算法             |
| `APP_ACCESS_TOKEN_TTL_MINUTES` | `30`                               | 否        | access token 过期分钟数 |
| `APP_REFRESH_TOKEN_TTL_DAYS`   | `7`                                | 否        | refresh token 过期天数 |

---

## 6. Windows 新机器初始化步骤

### 6.1 拉取项目后初始化后端

```cmd
cd /D D:\project\python\fastapi
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install SQLAlchemy==2.0.44 alembic==1.18.4 psycopg==3.2.12 psycopg-binary==3.2.12 PyJWT==2.10.1
```

### 6.2 配置 `.env`

在项目根目录创建 `.env`，至少配置：

- `APP_DATABASE_URL`
- `APP_JWT_SECRET_KEY`

### 6.3 初始化数据库

```cmd
.venv\Scripts\python.exe -m alembic upgrade head
```

### 6.4 安装前端依赖

```cmd
npm --prefix "D:/project/python/fastapi/frontend" install
```

### 6.5 构建前端

```cmd
npm --prefix "D:/project/python/fastapi/frontend" run build
```

### 6.6 启动后端

```cmd
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 6.7 前端开发模式（可选）

如果只做前端开发，也可以单独启动：

```cmd
npm --prefix "D:/project/python/fastapi/frontend" run dev
```

---

## 7. 当前虚拟环境实际安装快照（Python）

以下为当前机器 `.venv` 中实际安装包版本，可作为迁移核对基准：

```text
alembic==1.18.4
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.12.1
black==26.1.0
certifi==2026.1.4
click==8.3.1
colorama==0.4.6
contextvars==2.4
dnspython==2.8.0
email-validator==2.3.0
fastapi==0.128.4
fastapi-cli==0.0.20
fastapi-cloud-cli==0.11.0
fastar==0.8.0
greenlet==3.4.0
h11==0.16.0
httpcore==1.0.9
httptools==0.7.1
httpx==0.28.1
idna==3.11
immutables==0.21
iniconfig==2.3.0
isort==7.0.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.10
markdown-it-py==4.0.0
MarkupSafe==3.0.3
mdurl==0.1.2
mypy_extensions==1.1.0
orjson==3.11.7
packaging==26.0
pathspec==1.0.4
platformdirs==4.5.1
pluggy==1.6.0
psycopg==3.2.12
psycopg-binary==3.2.12
pydantic==2.12.5
pydantic-extra-types==2.11.0
pydantic-settings==2.12.0
pydantic_core==2.41.5
Pygments==2.19.2
PyJWT==2.10.1
pytest==8.4.2
python-dotenv==1.2.1
python-multipart==0.0.22
pytokens==0.4.1
PyYAML==6.0.3
rich==14.3.2
rich-toolkit==0.18.1
rignore==0.7.6
sentry-sdk==2.52.0
setuptools==82.0.1
shellingham==1.5.4
SQLAlchemy==2.0.44
starlette==0.52.1
typer==0.21.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2026.1
ujson==5.11.0
urllib3==2.6.3
uvicorn==0.40.0
watchfiles==1.1.1
websockets==16.0
wheel==0.46.3
```

---

## 8. 当前前端直接依赖快照（npm）

以下为当前机器 `frontend` 目录直接依赖快照：

```text
@eslint/js@9.39.4
@testing-library/jest-dom@6.9.1
@testing-library/react@16.3.2
@testing-library/user-event@14.6.1
@types/node@24.12.2
@types/react-dom@19.2.3
@types/react@19.2.14
@vitejs/plugin-react@6.0.1
@vitest/coverage-v8@4.1.4
antd@6.3.5
eslint-plugin-react-hooks@7.0.1
eslint-plugin-react-refresh@0.5.2
eslint@9.39.4
globals@17.4.0
jsdom@29.0.2
react-dom@19.2.5
react-router-dom@7.14.0
react@19.2.5
typescript-eslint@8.58.1
typescript@6.0.2
vite@8.0.8
vitest@4.1.4
```

---

## 9. 迁移完成后的验证命令

### 9.1 后端测试

```cmd
"D:/project/python/fastapi/.venv/Scripts/python.exe" -m pytest "D:/project/python/fastapi/tests/test_auth_api.py" -q
```

### 9.2 前端测试

```cmd
npm --prefix "D:/project/python/fastapi/frontend" test
```

### 9.3 前端构建

```cmd
npm --prefix "D:/project/python/fastapi/frontend" run build
```

### 9.4 启动服务

```cmd
"D:/project/python/fastapi/.venv/Scripts/python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 10. 迁移注意事项

- Windows 下不要安装 `uvloop`，当前项目已通过 `requirements.txt` 避开该依赖。
- 若 PowerShell 激活虚拟环境时报执行策略错误，可执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

- 只有执行过前端 `build` 后，FastAPI 才会直接托管最新的前端页面。
- 如果数据库连接失败，优先检查：
    - PostgreSQL 服务是否启动
    - `APP_DATABASE_URL` 是否正确
    - 数据库用户权限是否足够
    - 目标数据库是否已创建
