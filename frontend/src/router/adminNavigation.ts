export type AdminNavigationItem = {
  key: string
  path: string
  label: string
  permission?: string
}

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
    permission: 'user:view',
  },
  {
    key: '/roles',
    path: '/roles',
    label: '角色管理',
    permission: 'role:view',
  },
  {
    key: '/permissions',
    path: '/permissions',
    label: '权限列表',
    permission: 'permission:view',
  },
]
