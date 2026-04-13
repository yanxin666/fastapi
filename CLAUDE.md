# CLAUDE.md

## 用途
这是一个后台管理类全栈项目：
- 后端：FastAPI + SQLAlchemy + PostgreSQL + Alembic
- 前端：React + TypeScript + Vite + Ant Design
- 前端构建产物位于 `frontend/dist`，由 FastAPI 直接托管

本文件用于约束 Claude / AI 在本仓库中的默认工作方式。

## 强约束
1. **涉及数据库写操作的命令，执行前必须告知风险并等待用户确认。**
   - 包括但不限于：运行 pytest、执行 alembic 迁移、运行 seed 脚本、执行任何 SQL
   - 必须先说明：会影响哪个数据库、是否会修改或删除现有数据
   - 用户明确同意后才能执行，绝不擅自运行

2. 涉及行为变更时，优先使用 TDD。
   - 先写或先改测试
   - 先确认测试因预期原因失败
   - 再做最小实现让测试通过

2. 未实际执行验证前，不要宣称“已完成”。
   - 后端改动：至少运行相关 pytest
   - 前端改动：至少运行前端测试和 build
   - UI 改动：如果条件允许，额外做浏览器手工验证

3. 保持当前项目既有 API 风格。
   - 查询使用 `GET`
   - 所有变更统一使用 `POST`
   - 不要为新的后台接口引入 `PUT`、`PATCH`、`DELETE`

4. 优先沿用现有模式，不要轻易新增抽象。
   - 复用已有页面模式、API client 模式、权限控制模式
   - 除非确实能明显减少重复，否则不要新增一次性 helper

## 项目结构速览
### 后端
- `app/main.py`
  - 应用入口
  - 注册中间件
  - 自动注册路由
  - 托管前端构建产物

- `app/init.py`
  - 递归扫描 `app/api/**`
  - 自动注册导出的 `router`
  - 若模块声明了 `router_prefix_setting`，则按配置追加前缀

- `app/core/config.py`
  - 配置入口
  - 读取 `.env`
  - 环境变量前缀为 `APP_`

- `app/middleware/jwt.py`
  - Bearer Token 解析
  - 当前用户获取
  - `require_permissions(...)` 权限校验

- `app/api/auth/auth.py`
  - 后台登录 / 刷新 token / 登出 / 当前用户接口

- `app/api/system/users.py`
  - 用户管理相关后台接口

- `app/api/system/roles.py`
  - 角色管理相关后台接口

- `app/api/system/permissions.py`
  - 权限列表相关接口

- `tests/test_auth_api.py`
  - 当前后台 auth/admin 相关核心集成测试文件

### 前端
- `frontend/src/auth.tsx`
  - 登录态上下文
  - `localStorage` session 持久化
  - 页面启动时自动拉取当前用户
  - access token 过期时尝试 refresh

- `frontend/src/lib/api-client.ts`
  - 前端统一 API 层
  - 统一处理认证请求和 `ApiError`
  - 页面中不要零散直接写 `fetch`

- `frontend/src/router/AppRoutes.tsx`
  - 公共路由 / 受保护路由
  - 基于权限的路由守卫

- `frontend/src/router/adminNavigation.ts`
  - 基于权限过滤的后台导航

- `frontend/src/pages/UsersPage.tsx`
  - 后台 CRUD 页面主要参考实现

- `frontend/src/pages/RolesPage.tsx`
  - 角色 CRUD 页面，结构应尽量与 `UsersPage.tsx` 保持一致

## 核心约定
### 路由注册规则
新增后端 API 模块时：
- 放在 `app/api/**` 下
- 导出 `router`
- 如果属于后台管理接口，通常声明：

```python
router_prefix_setting = "admin_api_prefix"
```

当前后台接口前缀默认是：

```text
/api/v1/admin
```

### 配置规则
重要配置位于 `app/core/config.py`。
常用环境变量包括：
- `APP_DATABASE_URL`
- `APP_JWT_SECRET_KEY`
- `APP_ACCESS_TOKEN_TTL_MINUTES`
- `APP_REFRESH_TOKEN_TTL_DAYS`

### 权限规则
后台访问基于权限字符串控制。
当前常见权限码包括：
- `user:view`
- `user:create`
- `role:view`
- `role:create`
- `role:update`
- `role:delete`
- `permission:view`

新增受保护功能时，至少同时检查三层：
1. 后端接口权限
2. 前端路由访问权限
3. 前端按钮/操作显隐权限

## API 规则
后台接口必须与现有风格保持一致。

示例：
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users/{id}/update`
- `POST /api/v1/admin/users/{id}/toggle-active`
- `GET /api/v1/admin/roles`
- `POST /api/v1/admin/roles/{id}/permissions`
- `POST /api/v1/admin/roles/{id}/delete`

错误处理约定：
- 后端尽量返回清晰的 `detail`
- 前端 `ApiError` 会统一映射后端 `message/detail`
- 优先返回可以直接展示给用户的错误消息

## 前端约定
1. 所有 API 访问优先走 `frontend/src/lib/api-client.ts`
2. 优先复用现有 CRUD 页面结构：
   - 列表 loading 状态
   - 错误状态
   - 基于 Modal 的创建/编辑流程
   - 各操作独立提交 loading
   - 遇到 401 时 logout
3. 权限控制遵循既有模式：
   - 路由层在 `AppRoutes.tsx`
   - 导航层在 `adminNavigation.ts`
   - 页面内按钮和操作单独控制显隐
4. 默认 API base URL 为：

```text
/api/v1/admin
```

## 全栈改动检查清单
新增或修改后台功能时，通常要同步考虑以下层次：
1. 后端路由和业务逻辑
2. 后端集成测试 `tests/test_auth_api.py`
3. 前端 API client `frontend/src/lib/api-client.ts`
4. 前端页面 UI
5. 如有需要，再补路由守卫和导航权限

## 验证命令
### 后端测试

> **警告**：当前测试会 TRUNCATE 数据库表（清空数据），使用的是 .env 中的 APP_DATABASE_URL 指向的数据库。运行前必须确认用户已知晓风险。

```bash
"D:/project/python/fastapi/.venv/Scripts/python.exe" -m pytest "D:/project/python/fastapi/tests/test_auth_api.py" -q
```

按功能筛选示例：
```bash
"D:/project/python/fastapi/.venv/Scripts/python.exe" -m pytest "D:/project/python/fastapi/tests/test_auth_api.py" -q -k "role or permission"
```

### 前端测试
```bash
npm --prefix "D:/project/python/fastapi/frontend" test
```

### 前端构建
```bash
npm --prefix "D:/project/python/fastapi/frontend" run build
```

### 后端开发服务
```bash
"D:/project/python/fastapi/.venv/Scripts/python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端开发服务
```bash
npm --prefix "D:/project/python/fastapi/frontend" run dev
```

## 前端构建产物托管规则
当 `frontend/dist` 存在时，`app/main.py` 会托管 SPA：
- `/assets` 挂载静态资源
- `/favicon.svg` 单独提供
- `/` 和非 `/api/*` 路径回退到 `index.html`
- `/api/*` 路径不会回退到前端页面

这意味着：
- 如果想让集成环境中的前端修改生效，通常需要先构建前端

## 当前功能快照
当前后台已具备：
- 登录 / 刷新 / 登出
- 受保护路由
- 基于权限的导航
- 用户管理页面
- 角色管理页面
- 权限列表页面

当前角色管理已支持：
- 列表
- 新建
- 编辑
- 分配权限
- 删除

当前角色删除规则：
- 使用 `POST /roles/{role_id}/delete`
- 若角色仍被用户引用，后端会阻止删除

## 在本仓库中的推荐工作方式
- 改代码前先读现有实现，再决定是否复用模式
- 只做最小但完整的改动
- 保持前后端数据契约一致
- 通过真实命令验证，不靠主观判断
- 如果已有相似功能，优先复制其结构，再做针对性修改
- 代码的编写必须有注释，尤其是涉及业务逻辑的部分，注释应该清晰说明为什么这样做，而不仅仅是做了什么
- 菜单栏、CURD功能、权限、按钮、操作等尽量都用中文描述，保持一致性和可读性
