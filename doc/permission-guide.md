# 权限系统维护指南

## 整体架构

权限系统采用前后端对称的三层架构，定义和策略都集中管理，页面/端点代码不直接引用权限码字符串。

```
后端                                  前端
─────────────────────────            ─────────────────────────
Layer 1: 权限码定义                    Layer 1: 权限码定义
  app/authz/codes.py                   frontend/src/lib/permissions.ts
  PermissionCode 枚举                  PERMISSIONS 常量

Layer 2: 策略映射                      Layer 2: 策略映射
  app/authz/policy.py                  frontend/src/lib/permissions.ts
  端点 → 权限码                        OPERATION_POLICIES (操作 → 权限码)
                                      ROUTE_POLICIES (路由 → 权限码)

Layer 3: 自动执行                      Layer 3: 自动执行
  app/authz/router.py                  frontend/src/lib/permissions.ts
  PolicyRouter 自动注入权限依赖         useCan() / usePermissions() Hook
  端点函数零权限代码                    页面组件不直接引用权限码字符串
```

### 权限数据模型

```
Permission (权限) ←多对多→ Role (角色) ←多对多→ User (用户)
   code: "user:view"       name: "admin"        username: "admin"
```

权限不直接分配给用户，而是通过角色间接分配。

### 超级用户

User 模型有 `is_superuser` 字段，超级用户绕过所有权限检查：
- 后端：`app/middleware/jwt.py` 的 `require_permissions` 函数在查询权限前短路返回
- 前端：`useCan()` 和 `usePermissions()` Hook 对超级用户始终返回 true

两侧行为一致，不会出现后端放行但前端拦截的情况。

---

## 当前权限码清单

| 权限码 | 中文含义 | 覆盖的操作 |
|--------|---------|-----------|
| `user:view` | 查看用户 | 用户列表、用户详情 |
| `user:create` | 管理用户 | 创建用户、编辑用户、分配角色、启用/禁用、重置密码 |
| `role:view` | 查看角色 | 角色列表、角色详情 |
| `role:create` | 创建角色 | 新建角色 |
| `role:update` | 编辑角色 | 编辑角色信息、分配角色权限 |
| `role:delete` | 删除角色 | 删除角色 |
| `permission:view` | 查看权限 | 权限列表 |

> 注意：`user:create` 当前覆盖了 5 种操作，粒度较粗。如需拆分见下方"远期规划"章节。

---

## 后端权限关键文件

| 文件 | 作用 | 改动频率 |
|------|------|---------|
| `app/authz/codes.py` | 权限码定义（PermissionCode 枚举） | 新增权限时改 |
| `app/authz/policy.py` | 端点→权限策略映射 | 新增端点时改 |
| `app/authz/router.py` | PolicyRouter，自动注入权限依赖 | 几乎不改 |
| `app/authz/dependencies.py` | 枚举到字符串的桥接 | 几乎不改 |
| `app/authz/seed.py` | 权限种子数据同步 | 新增权限后运行 |
| `app/middleware/jwt.py` | 权限校验核心（require_permissions） | 几乎不改 |
| `app/models/permission.py` | Permission 数据模型 | 几乎不改 |

### 后端权限执行流程

```
请求到达
  ↓
PolicyRouter.add_api_route() 已在启动时注入 Depends(require_permission_group(...))
  ↓
require_permission_group([PermissionCode.USER_VIEW])
  ↓  (枚举转字符串)
require_permissions("user:view")
  ↓
  ├─ Depends(get_current_user) → 401 如果未登录
  ↓
  ├─ user.is_superuser? → 直接放行
  ↓
  ├─ 查询 User→Role→Permission 获取用户权限码集合
  ↓
  └─ set(required).issubset(user_permissions)? → 403 如果权限不足
```

---

## 前端权限关键文件

| 文件 | 作用 | 改动频率 |
|------|------|---------|
| `frontend/src/lib/permissions.ts` | **权限唯一来源**：定义 + 策略 + Hook | 新增权限时改 |
| `frontend/src/router/AppRoutes.tsx` | 路由守卫，引用 ROUTE_POLICIES | 新增受保护路由时改 |
| `frontend/src/router/adminNavigation.ts` | 导航菜单，引用 ROUTE_POLICIES | 新增菜单项时改 |
| `frontend/src/layouts/AdminLayout.tsx` | 导航过滤，用 usePermissions() | 几乎不改 |
| 页面组件（UsersPage 等） | 操作权限，用 useCan() | 新增操作按钮时改 |

### 前端权限检查方式

```tsx
// 1. 页面操作权限 — 使用 useCan()
import { useCan } from '../lib/permissions'
const can = useCan()
can('USER_CREATE')   // → true/false

// 2. 路由守卫 / 导航过滤 — 使用 usePermissions()
import { usePermissions } from '../lib/permissions'
const perms = usePermissions()
perms.has('user:view')  // → true/false

// 3. 路由配置 — 引用 ROUTE_POLICIES
import { ROUTE_POLICIES } from '../lib/permissions'
<Route element={<PermissionRoute permission={ROUTE_POLICIES['/users']} />}>
```

### 前端权限数据流

```
后端 GET /auth/me → AdminUser.permissions: string[]
  → AuthProvider (auth.tsx) 存入 localStorage
  → useAuth().permissions
    → useCan() — 操作权限检查（页面用）
    → usePermissions() — 权限码直接判断（路由/导航用）
```

---

## 新增权限操作手册

以新增 `user:delete`（删除用户）权限为例。

### 第一步：后端 — 添加权限码

**文件**：`app/authz/codes.py`

```python
class PermissionCode(StrEnum):
    # ... 已有的权限码 ...
    USER_DELETE = "user:delete"
    """删除用户"""
```

### 第二步：后端 — 添加端点策略映射

**文件**：`app/authz/policy.py`，在 `build_default_policy_resolver()` 函数的字典中添加：

```python
"app.api.system.users:delete_user": EndpointPolicy(
    permissions=(PermissionCode.USER_DELETE,)
),
```

### 第三步：后端 — 添加路由处理函数

**文件**：`app/api/system/users.py`

```python
@router.post("/{user_id}/delete")
def delete_user(user_id: int, ...):
    ...
```

> 注意：路由函数本身不需要写任何权限代码，PolicyRouter 会自动注入。

### 第四步：后端 — 同步权限码到数据库

```bash
make seed-permissions
```

这会将新权限码 `user:delete` 插入数据库的 `permissions` 表。

### 第五步：前端 — 更新权限定义和策略

**文件**：`frontend/src/lib/permissions.ts`，这一步完成前端所有权限配置：

```ts
// Layer 1: 添加权限码常量
export const PERMISSIONS = {
  // ... 已有的权限码 ...
  USER_DELETE: 'user:delete',
  /** 删除用户 */
} as const

// 添加中文标签
export const PERMISSION_LABELS: Record<PermissionCode, string> = {
  // ... 已有的标签 ...
  [PERMISSIONS.USER_DELETE]: '删除用户',
}

// Layer 2: 添加操作策略映射
export const OPERATION_POLICIES = {
  // ... 已有的操作 ...
  USER_DELETE: PERMISSIONS.USER_DELETE,
} as const
```

### 第六步：前端 — 页面使用权限

**文件**：页面组件（如 `UsersPage.tsx`）

```tsx
import { useCan } from '../lib/permissions'

const can = useCan()

// 控制删除按钮显隐
{can('USER_DELETE') && <Button danger onClick={...}>删除</Button>}
```

### 第七步（如需）：前端 — 添加路由/导航

如果新权限对应一个新页面，还需要：

**`permissions.ts`**：添加路由策略

```ts
export const ROUTE_POLICIES = {
  // ... 已有的路由 ...
  '/new-page': PERMISSIONS.USER_DELETE,
} as const
```

**`AppRoutes.tsx`**：添加路由守卫

```tsx
<Route element={<PermissionRoute permission={ROUTE_POLICIES['/new-page']} />}>
  <Route path="new-page" element={<NewPage />} />
</Route>
```

**`adminNavigation.ts`**：添加导航项

```ts
{
  key: '/new-page',
  path: '/new-page',
  label: '新页面',
  permission: ROUTE_POLICIES['/new-page'],
}
```

### 第八步：构建验证

```bash
# 前端构建（包含类型检查）
npm --prefix frontend run build
```

---

## 拆分权限粒度（远期规划）

当前 `user:create` 覆盖 5 种操作，粒度较粗。当需要区分"谁能创建用户"和"谁能重置密码"时，需要拆分。

### 拆分步骤

**1. 后端 codes.py 添加细粒度权限码**

```python
USER_UPDATE = "user:update"
"""编辑用户"""
USER_ASSIGN_ROLES = "user:assign_roles"
"""分配用户角色"""
USER_TOGGLE_ACTIVE = "user:toggle_active"
"""启用/禁用用户"""
USER_RESET_PASSWORD = "user:reset_password"
"""重置用户密码"""
```

**2. 后端 policy.py 更新映射**

将原来映射到 `USER_CREATE` 的端点改为映射到各自的细粒度权限码。

**3. 数据库迁移**

编写 Alembic 迁移，将新权限码插入 `permissions` 表，并将原来拥有 `user:create` 的角色的 `role_permissions` 补上新权限码（向后兼容）。

**4. 前端只需改 permissions.ts**

```ts
// 只需修改 OPERATION_POLICIES 的映射，页面代码不用动
export const OPERATION_POLICIES = {
  USER_CREATE: PERMISSIONS.USER_CREATE,
  USER_EDIT: PERMISSIONS.USER_UPDATE,           // 原来是 USER_CREATE
  USER_ASSIGN_ROLES: PERMISSIONS.USER_ASSIGN_ROLES, // 原来是 USER_CREATE
  USER_TOGGLE_ACTIVE: PERMISSIONS.USER_TOGGLE_ACTIVE, // 原来是 USER_CREATE
  USER_RESET_PASSWORD: PERMISSIONS.USER_RESET_PASSWORD, // 原来是 USER_CREATE
} as const
```

> 页面组件用的是操作键 `can('USER_EDIT')`，不是权限码字符串，所以映射关系变了页面代码不需要改。

---

## 权限三层检查清单

新增受保护功能时，必须同时检查三层：

| 层 | 后端 | 前端 |
|----|------|------|
| 接口/路由 | `policy.py` 端点策略 | `AppRoutes.tsx` 路由守卫 |
| 导航/菜单 | — | `adminNavigation.ts` 菜单过滤 |
| 操作/按钮 | — | 页面组件 `can('XXX')` |

每一层缺一不可，否则会出现：
- 后端有权限但前端看不到按钮 → 功能存在但不可达
- 前端有按钮但后端没权限 → 点击后 403
- 路由有守卫但导航没配置 → 直接输入 URL 可访问但菜单看不到

---

## 常见问题

### Q: 前后端权限码不一致怎么办？

后端 `codes.py` 是权限码的唯一来源，前端 `permissions.ts` 必须与后端保持同步。两者的权限码字符串必须完全一致（如 `'user:view'`），否则前端检查通过但后端拒绝，或反之。

### Q: 超级用户在前端为什么能看到所有按钮？

`useCan()` 和 `usePermissions()` 内部检查 `user.is_superuser`，超级用户时自动返回 true，与后端 `require_permissions` 的短路逻辑保持一致。

### Q: 数据库中没有权限数据怎么办？

运行 `make seed-permissions`，会将 `PermissionCode` 枚举中定义的所有权限码同步到数据库。已存在的会更新描述，不存在的会插入，不会删除多余数据。

### Q: 新增权限后忘记运行 seed 怎么办？

权限码只存在于代码中，数据库里没有对应记录的话，角色管理页面无法分配该权限。运行 `make seed-permissions` 即可补上。
