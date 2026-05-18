/**
 * 权限定义与策略模块
 *
 * 对标后端 app/authz/codes.py 和 app/authz/policy.py，
 * 是前端权限的唯一定义和策略来源。
 *
 * 新增权限时，只需更新本文件 + 后端 codes.py + 后端 policy.py，
 * 页面组件通过 useCan() Hook 使用权限，不直接引用权限码字符串。
 */

import { useCallback, useMemo } from 'react'

import { useAuth } from '../auth'

// ==================== Layer 1: 权限码定义 ====================
// 对标后端 app/authz/codes.py 的 PermissionCode 枚举
// 新增权限时必须同步更新此处和后端枚举

export const PERMISSIONS = {
  // 用户管理
  USER_VIEW: 'user:view',
  /** 查看用户列表和详情 */
  USER_CREATE: 'user:create',
  /** 创建用户、编辑用户、分配角色、启用/禁用用户、重置密码 */

  // 角色管理
  ROLE_VIEW: 'role:view',
  /** 查看角色列表和详情 */
  ROLE_CREATE: 'role:create',
  /** 创建角色 */
  ROLE_UPDATE: 'role:update',
  /** 更新角色信息、分配角色权限 */
  ROLE_DELETE: 'role:delete',
  /** 删除角色 */

  // 权限管理
  PERMISSION_VIEW: 'permission:view',
  /** 查看权限列表 */

  // 客户管理
  CUSTOMER_VIEW: 'customer:view',
  /** 查看客户列表和详情 */
  CUSTOMER_CREATE: 'customer:create',
  /** 创建客户 */
  CUSTOMER_UPDATE: 'customer:update',
  /** 编辑客户 */
  CUSTOMER_DELETE: 'customer:delete',
  /** 删除客户（软删除） */
  CUSTOMER_CLAIM: 'customer:claim',
  /** 从公海认领客户、释放认领 */
  CUSTOMER_ASSIGN: 'customer:assign',
  /** 主管调配：将客户分配给指定用户 */

  // 认领策略
  STRATEGY_VIEW: 'strategy:view',
  /** 查看认领策略 */
  STRATEGY_CREATE: 'strategy:create',
  /** 创建、编辑、删除认领策略 */

  // 跟进记录
  FOLLOWUP_VIEW: 'followup:view',
  /** 查看跟进记录 */
  FOLLOWUP_CREATE: 'followup:create',
  /** 创建、删除跟进记录 */
} as const

/** 权限码类型，从常量自动推导，用于类型约束 */
export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

/** 权限中文标签映射，用于页面展示 */
export const PERMISSION_LABELS: Record<PermissionCode, string> = {
  [PERMISSIONS.USER_VIEW]: '查看用户',
  [PERMISSIONS.USER_CREATE]: '管理用户',
  [PERMISSIONS.ROLE_VIEW]: '查看角色',
  [PERMISSIONS.ROLE_CREATE]: '创建角色',
  [PERMISSIONS.ROLE_UPDATE]: '编辑角色',
  [PERMISSIONS.ROLE_DELETE]: '删除角色',
  [PERMISSIONS.PERMISSION_VIEW]: '查看权限',
  [PERMISSIONS.CUSTOMER_VIEW]: '查看客户',
  [PERMISSIONS.CUSTOMER_CREATE]: '创建客户',
  [PERMISSIONS.CUSTOMER_UPDATE]: '编辑客户',
  [PERMISSIONS.CUSTOMER_DELETE]: '删除客户',
  [PERMISSIONS.CUSTOMER_CLAIM]: '认领客户',
  [PERMISSIONS.CUSTOMER_ASSIGN]: '调配客户',
  [PERMISSIONS.STRATEGY_VIEW]: '查看认领策略',
  [PERMISSIONS.STRATEGY_CREATE]: '管理认领策略',
  [PERMISSIONS.FOLLOWUP_VIEW]: '查看跟进记录',
  [PERMISSIONS.FOLLOWUP_CREATE]: '管理跟进记录',
}

// ==================== Layer 2: 权限策略映射 ====================
// 对标后端 app/authz/policy.py 的端点策略映射
// 定义前端各操作和路由需要的权限，页面不直接引用权限码

/**
 * 操作权限策略
 *
 * 定义页面中每个操作需要什么权限。
 * 页面通过 useCan('OPERATION_KEY') 判断是否有权执行操作，
 * 不再直接引用权限码字符串。
 *
 * 当前 user:create 覆盖所有用户管理操作（创建、编辑、分配角色等），
 * 将来拆分粒度时只需修改此处的映射关系，页面代码无需变动。
 */
export const OPERATION_POLICIES = {
  // 用户管理操作
  USER_CREATE: PERMISSIONS.USER_CREATE,
  USER_EDIT: PERMISSIONS.USER_CREATE,
  USER_ASSIGN_ROLES: PERMISSIONS.USER_CREATE,
  USER_TOGGLE_ACTIVE: PERMISSIONS.USER_CREATE,
  USER_RESET_PASSWORD: PERMISSIONS.USER_CREATE,
  // 角色管理操作
  ROLE_CREATE: PERMISSIONS.ROLE_CREATE,
  ROLE_EDIT: PERMISSIONS.ROLE_UPDATE,
  ROLE_DELETE: PERMISSIONS.ROLE_DELETE,
  ROLE_ASSIGN_PERMISSIONS: PERMISSIONS.ROLE_UPDATE,
  // 权限管理操作
  PERMISSION_VIEW: PERMISSIONS.PERMISSION_VIEW,
  // 客户管理操作
  CUSTOMER_VIEW: PERMISSIONS.CUSTOMER_VIEW,
  CUSTOMER_CREATE: PERMISSIONS.CUSTOMER_CREATE,
  CUSTOMER_EDIT: PERMISSIONS.CUSTOMER_UPDATE,
  CUSTOMER_DELETE: PERMISSIONS.CUSTOMER_DELETE,
  // 认领/释放/调配操作
  CUSTOMER_CLAIM: PERMISSIONS.CUSTOMER_CLAIM,
  CUSTOMER_BATCH_CLAIM: PERMISSIONS.CUSTOMER_CLAIM,
  CUSTOMER_RELEASE: PERMISSIONS.CUSTOMER_CLAIM,
  CUSTOMER_BATCH_RELEASE: PERMISSIONS.CUSTOMER_CLAIM,
  CUSTOMER_ASSIGN: PERMISSIONS.CUSTOMER_ASSIGN,
  /** 锁定客户（转为长期客户） */
  CUSTOMER_POSSESSION: PERMISSIONS.CUSTOMER_CLAIM,
  // 认领策略操作
  STRATEGY_CREATE: PERMISSIONS.STRATEGY_CREATE,
  STRATEGY_EDIT: PERMISSIONS.STRATEGY_CREATE,
  STRATEGY_DELETE: PERMISSIONS.STRATEGY_CREATE,
  // 跟进记录操作
  FOLLOWUP_VIEW: PERMISSIONS.FOLLOWUP_VIEW,
  FOLLOWUP_CREATE: PERMISSIONS.FOLLOWUP_CREATE,
  FOLLOWUP_DELETE: PERMISSIONS.FOLLOWUP_CREATE,
} as const

/** 操作键类型，页面通过此键查询权限，而非直接使用权限码 */
export type OperationKey = keyof typeof OPERATION_POLICIES

/**
 * 路由权限策略
 *
 * 定义哪些路由需要什么权限才能访问。
 * 对标后端 PolicyRouter 的端点→权限映射。
 * AppRoutes 和 adminNavigation 都从这里读取权限配置，
 * 避免路由守卫和导航菜单出现权限不一致。
 */
export const ROUTE_POLICIES = {
  '/users': PERMISSIONS.USER_VIEW,
  '/roles': PERMISSIONS.ROLE_VIEW,
  '/permissions': PERMISSIONS.PERMISSION_VIEW,
  '/customers': PERMISSIONS.CUSTOMER_VIEW,
  '/my-customers': PERMISSIONS.CUSTOMER_CLAIM,
  '/long-term-customers': PERMISSIONS.CUSTOMER_CLAIM,
  '/claim-strategies': PERMISSIONS.STRATEGY_VIEW,
} as const

/** 受保护路由路径类型 */
export type ProtectedRoutePath = keyof typeof ROUTE_POLICIES

// ==================== Layer 3: 权限检查 Hook ====================
// 对标后端 PolicyRouter 的自动注入机制
// 页面通过 Hook 间接使用权限，不直接引用权限码字符串

/**
 * 操作权限检查 Hook
 *
 * 用法：const can = useCan()
 *       can('USER_CREATE')  → true/false
 *
 * 页面不再写 permissions.includes('user:create')，
 * 而是写 can('USER_CREATE')，权限码的映射关系全在 OPERATION_POLICIES 中维护。
 *
 * 超级用户自动拥有所有操作权限，与后端 require_permissions 的 is_superuser 短路逻辑一致，
 * 避免后端放行但前端拦截的不一致问题。
 */
export function useCan() {
  const { user, permissions } = useAuth()
  const permSet = useMemo(() => new Set(permissions), [permissions])

  // 超级用户拥有全部权限，与后端 is_superuser 短路逻辑保持一致
  const isSuperuser = user?.is_superuser ?? false

  const can = useCallback(
    (operation: OperationKey) => isSuperuser || permSet.has(OPERATION_POLICIES[operation]),
    [isSuperuser, permSet],
  )

  return can
}

/**
 * 权限集合 Hook
 *
 * 返回当前用户权限的 Set 视图，用于需要直接按权限码判断的场景
 * （如路由守卫、导航过滤等）。
 * 页面内的操作权限检查应优先使用 useCan()。
 *
 * 超级用户的 has() 调用始终返回 true，与后端 is_superuser 短路逻辑一致。
 */
export function usePermissions() {
  const { user, permissions } = useAuth()
  const isSuperuser = user?.is_superuser ?? false
  const permSet = useMemo(() => new Set(permissions), [permissions])

  // 超级用户时返回一个 has() 始终为 true 的对象，
  // 因为调用方只用 has() 做权限检查，不需要完整 Set 的其他方法
  return useMemo(
    () =>
      isSuperuser
        ? ({ has: () => true } as unknown as Set<string>)
        : permSet,
    [isSuperuser, permSet],
  )
}
