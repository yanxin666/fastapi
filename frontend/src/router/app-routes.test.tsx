import { App as AntApp, ConfigProvider } from 'antd'
import { MemoryRouter, Outlet } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AppRoutes } from './AppRoutes'
import { adminNavigationItems } from './adminNavigation'

const mockUseAuth = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../layouts/AdminLayout', () => ({
  AdminLayout: () => (
    <div>
      <div>Admin Layout</div>
      <Outlet />
    </div>
  ),
}))

// 懒加载页面组件的 mock：lazy() 使用动态 import，需要 mock 整个模块
vi.mock('../pages/LoginPage', () => ({
  LoginPage: () => <div>Admin Login</div>,
}))
vi.mock('../pages/DashboardPage', () => ({
  DashboardPage: () => <div>Dashboard Page</div>,
}))
vi.mock('../pages/ForbiddenPage', () => ({
  ForbiddenPage: () => <div>Forbidden Page</div>,
}))
vi.mock('../pages/NotFoundPage', () => ({
  NotFoundPage: () => <div>Not Found Page</div>,
}))
vi.mock('../pages/UsersPage', () => ({
  UsersPage: () => <div>Users Page</div>,
}))
vi.mock('../pages/RolesPage', () => ({
  RolesPage: () => <div>Roles Page</div>,
}))
vi.mock('../pages/PermissionsPage', () => ({
  PermissionsPage: () => <div>Permissions Page</div>,
}))

function renderRoutes(initialEntry: string) {
  render(
    <ConfigProvider>
      <AntApp>
        <MemoryRouter initialEntries={[initialEntry]}>
          <AppRoutes />
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>,
  )
}

describe('app routing', () => {
  beforeEach(() => {
    mockUseAuth.mockReset()
    mockUseAuth.mockReturnValue({
      accessToken: null,
      user: null,
      permissions: [],
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  it('exposes Chinese admin navigation labels', () => {
    expect(adminNavigationItems).toEqual([
      { key: '/', path: '/', label: '控制台' },
      { key: '/users', path: '/users', label: '用户管理', permission: 'user:view' },
      { key: '/roles', path: '/roles', label: '角色管理', permission: 'role:view' },
      { key: '/permissions', path: '/permissions', label: '权限列表', permission: 'permission:view' },
      { key: '/customers', path: '/customers', label: '客户公海', permission: 'customer:view' },
      { key: '/my-customers', path: '/my-customers', label: '我的客户', permission: 'customer:claim' },
      { key: '/long-term-customers', path: '/long-term-customers', label: '长期客户', permission: 'customer:claim' },
      { key: '/claim-strategies', path: '/claim-strategies', label: '认领策略', permission: 'strategy:view' },
    ])
  })

  it('renders the login route for unauthenticated visitors', async () => {
    renderRoutes('/login')

    await waitFor(() => {
      expect(screen.getByText('Admin Login')).toBeInTheDocument()
    })
  })

  it('redirects unauthenticated visitors to the login route', async () => {
    renderRoutes('/users')

    await waitFor(() => {
      expect(screen.getByText('Admin Login')).toBeInTheDocument()
    })
  })

  it('redirects authenticated visitors away from the login route', async () => {
    mockUseAuth.mockReturnValue({
      accessToken: 'access-token',
      user: {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        is_active: true,
        is_superuser: true,
        roles: ['admin'],
        permissions: ['user:view'],
      },
      permissions: ['user:view'],
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    renderRoutes('/login')

    await waitFor(() => {
      expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    })
  })

  it('renders the protected page when the user has the required permission', async () => {
    mockUseAuth.mockReturnValue({
      accessToken: 'access-token',
      user: {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        is_active: true,
        is_superuser: true,
        roles: ['admin'],
        permissions: ['user:view', 'role:view'],
      },
      permissions: ['user:view', 'role:view'],
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    renderRoutes('/users')

    await waitFor(() => {
      expect(screen.getByText('Users Page')).toBeInTheDocument()
    })
    expect(screen.getByText('Admin Layout')).toBeInTheDocument()
  })

  it('redirects to the forbidden page when the user lacks the required permission', async () => {
    mockUseAuth.mockReturnValue({
      accessToken: 'access-token',
      user: {
        id: 1,
        username: 'viewer',
        email: 'viewer@example.com',
        is_active: true,
        is_superuser: false,
        roles: ['viewer'],
        permissions: [],
      },
      permissions: [],
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    renderRoutes('/permissions')

    await waitFor(() => {
      expect(screen.getByText('Forbidden Page')).toBeInTheDocument()
    })
  })

  it('renders the not found page for unknown routes', async () => {
    renderRoutes('/missing')

    await waitFor(() => {
      expect(screen.getByText('Not Found Page')).toBeInTheDocument()
    })
  })
})
