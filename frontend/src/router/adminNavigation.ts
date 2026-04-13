import { ROUTE_POLICIES, type PermissionCode } from '../lib/permissions'

export type AdminNavigationItem = {
  key: string
  path: string
  label: string
  permission?: PermissionCode
}

// 导航项的权限配置引用 ROUTE_POLICIES，
// 确保路由守卫和导航菜单的权限始终一致
export const adminNavigationItems: AdminNavigationItem[] = [
  {
    key: '/',
    path: '/',
    label: '控制台',
  },
  {
    key: '/users',
    path: '/users',
    label: '用户管理',
    permission: ROUTE_POLICIES['/users'],
  },
  {
    key: '/roles',
    path: '/roles',
    label: '角色管理',
    permission: ROUTE_POLICIES['/roles'],
  },
  {
    key: '/permissions',
    path: '/permissions',
    label: '权限列表',
    permission: ROUTE_POLICIES['/permissions'],
  },
  {
    key: '/customers',
    path: '/customers',
    label: '客户管理',
    permission: ROUTE_POLICIES['/customers'],
  },
]
