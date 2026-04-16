# CRM 前端服务操作手册 — Windows 开发环境

适用环境：Windows 10/11 本地开发

---

## 目录

1. [技术栈与项目结构](#1-技术栈与项目结构)
2. [环境准备与依赖安装](#2-环境准备与依赖安装)
3. [启动前端开发服务](#3-启动前端开发服务)
4. [关闭前端开发服务](#4-关闭前端开发服务)
5. [重启前端开发服务](#5-重启前端开发服务)
6. [前后端联调](#6-前后端联调)
7. [前端构建](#7-前端构建)
8. [前端测试](#8-前端测试)
9. [常见问题](#9-常见问题)
10. [命令速查表](#10-命令速查表)

---

## 1. 技术栈与项目结构

### 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 19 |
| 语言 | TypeScript 6 |
| 构建工具 | Vite 8 |
| UI 组件库 | Ant Design 6 |
| 路由 | React Router DOM 7 |
| 测试 | Vitest + Testing Library |

### 目录结构

```
frontend/
├── src/
│   ├── auth.tsx           # 登录态上下文，token 刷新逻辑
│   ├── lib/
│   │   └── api-client.ts  # 统一 API 层，所有请求走这里
│   ├── router/
│   │   ├── AppRoutes.tsx   # 路由定义与权限守卫
│   │   └── adminNavigation.ts  # 后台导航菜单与权限过滤
│   ├── pages/             # 页面组件
│   │   ├── UsersPage.tsx  # 用户管理（CRUD 参考实现）
│   │   └── RolesPage.tsx  # 角色管理
│   └── test/
│       └── setup.ts       # 测试环境配置
├── package.json
├── vite.config.ts
└── dist/                  # 构建产物（git 已忽略）
```

### 前端与后端的契约

- API 基础路径：`/api/v1/admin`
- 认证方式：Bearer Token（Authorization 请求头）
- 所有 API 调用通过 `src/lib/api-client.ts` 统一处理，页面中不直接写 `fetch`
- API 请求路径示例：
  - `GET /api/v1/admin/users` — 查询
  - `POST /api/v1/admin/users/{id}/update` — 变更

---

## 2. 环境准备与依赖安装

### 前置依赖

| 依赖 | 最低版本 | 验证命令 |
|------|---------|---------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |

### 安装前端依赖

```bash
# 方式一：Make 命令
make install-frontend

# 方式二：直接命令
npm --prefix frontend install
```

安装速度慢时，配置国内镜像（Makefile 已内置此配置）：

```bash
npm --prefix frontend config set registry https://registry.npmmirror.com
npm --prefix frontend install
```

---

## 3. 启动前端开发服务

开发服务使用 Vite，支持热重载（修改代码后浏览器自动更新）。

```bash
# 方式一：Make 命令
make run-frontend

# 方式二：直接命令
npm --prefix frontend run dev
```

启动后终端会显示：

```
  VITE v8.x.x  ready

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

访问 http://localhost:5173 即可看到页面。

> Vite 默认端口 5173，如果被占用会自动递增（5174、5175...），终端会显示实际端口。

---

## 4. 关闭前端开发服务

### 前台模式

在运行 `make run-frontend` 的终端窗口中按 `Ctrl+C`。

### 后台模式

```bash
make stop-frontend
```

---

## 5. 重启前端开发服务

### 前台模式

`Ctrl+C` 停止后，重新执行启动命令。

### 后台模式

```bash
make stop-frontend && make run-frontend
```

---

## 6. 前后端联调

开发时前端和后端需要同时运行，Vite 会自动将 API 请求代理到后端。

### 操作步骤

1. **启动后端**（一个终端窗口）

   ```bash
   make run-backend
   ```

2. **启动前端**（另一个终端窗口）

   ```bash
   make run-frontend
   ```

3. **浏览器访问** http://localhost:5173

### 两种访问方式对比

| 访问地址 | 模式 | 适用场景 |
|---------|------|---------|
| http://localhost:5173 | Vite 开发服务 | **日常开发**，修改即生效，热重载 |
| http://127.0.0.1:8000 | FastAPI 托管 | 验证构建结果，需先 `npm run build` |

> 开发时务必访问 5173 端口，8000 端口是构建后的静态文件，修改源码不会自动生效。

---

## 7. 前端构建

### 构建命令

```bash
npm --prefix frontend run build
```

构建产物输出到 `frontend/dist/`：

```
frontend/dist/
├── index.html              # SPA 入口
└── assets/
    ├── index-DgR888s2.css  # 样式文件（文件名含内容哈希）
    └── index-CSUL2sTb.js   # JavaScript 文件（文件名含内容哈希）
```

### 验证构建结果

构建完成后，访问 http://127.0.0.1:8000 可以看到构建后的页面（需要后端正在运行）。

### 何时需要构建

| 场景 | 是否需要构建 |
|------|------------|
| 日常开发调试 | 不需要，用 5173 端口 |
| 验证构建后是否正常 | 需要 |
| 部署到生产服务器 | 需要，构建后上传 `dist/` |
| 修改了前端代码想看 8000 端口的效果 | 需要 |

### FastAPI 托管逻辑

当 `frontend/dist/index.html` 存在时，`app/main.py` 会自动：

1. `/assets/*` → 返回静态资源（JS、CSS、图片）
2. `/favicon.svg` → 返回网站图标
3. `/` → 返回 `index.html`
4. `/api/*` → 不回退，返回 404（由后端路由处理）
5. 其他路径 → 返回 `index.html`（SPA 路由回退）

---

## 8. 前端测试

### 运行测试

```bash
npm --prefix frontend test
```

### 代码检查

```bash
npm --prefix frontend run lint
```

### TypeScript 类型检查

```bash
cd frontend && npx tsc --noEmit
```

### 构建前建议的检查流程

```bash
# 1. 类型检查
cd frontend && npx tsc --noEmit

# 2. lint 检查
npm run lint

# 3. 单元测试
npm test

# 4. 构建
npm run build
```

---

## 9. 常见问题

| 问题 | 解决方案 |
|------|---------|
| `npm install` 很慢 | 配置国内镜像：`npm --prefix frontend config set registry https://registry.npmmirror.com` |
| `npm run build` 报 TypeScript 错误 | 先运行 `cd frontend && npx tsc --noEmit` 查看具体类型错误 |
| 构建产物体积过大（>500KB 警告） | 正常现象，gzip 后通常 300-400KB，生产环境 Nginx 会做 gzip 压缩 |
| 构建后页面空白 | 检查 `frontend/dist/index.html` 是否存在；检查浏览器控制台是否有资源加载错误 |
| 修改代码后页面不更新 | 确认访问的是 http://localhost:5173（开发模式），而非 8000 |
| API 请求 404 | 确认后端正在运行，检查请求路径是否以 `/api/v1/admin` 开头 |
| API 请求 401/403 | Token 过期，重新登录；或检查当前用户是否有对应权限 |
| 登录后页面空白 | 打开浏览器控制台查看错误，常见原因是权限不足导致路由无匹配 |
| Vite 端口被占用 | Vite 自动递增端口，查看终端输出的实际地址；或手动指定：`npx vite --port 3000` |
| `node_modules` 损坏 | 删除后重装：`rm -rf frontend/node_modules && npm --prefix frontend install` |

---

## 10. 命令速查表

| 操作 | Make 命令 | 直接命令 |
|------|----------|---------|
| 安装依赖 | `make install-frontend` | `npm --prefix frontend install` |
| 启动开发服务 | `make run-frontend` | `npm --prefix frontend run dev` |
| 停止开发服务 | `make stop-frontend` | 终端 `Ctrl+C` |
| 前端构建 | — | `npm --prefix frontend run build` |
| 运行测试 | — | `npm --prefix frontend test` |
| 代码检查 | — | `npm --prefix frontend run lint` |
| 类型检查 | — | `cd frontend && npx tsc --noEmit` |
