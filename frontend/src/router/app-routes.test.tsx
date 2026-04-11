import { App as AntApp, ConfigProvider } from 'antd'
import { MemoryRouter, Outlet } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
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

vi.mock('../pages/DashboardPage', () => ({
  DashboardPage: () => <div>Dashboard Page</div>,
}))

vi.mock('../pages/LoginPage', () => ({
  LoginPage: () => <div>Admin Login</div>,
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
    ])
  })

  it('renders the login route for unauthenticated visitors', () => {
    renderRoutes('/login')

    expect(screen.getByText('Admin Login')).toBeInTheDocument()
  })

  it('redirects unauthenticated visitors to the login route', () => {
    renderRoutes('/users')

    expect(screen.getByText('Admin Login')).toBeInTheDocument()
  })

  it('redirects authenticated visitors away from the login route', () => {
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

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
  })

  it('renders the protected page when the user has the required permission', () => {
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

    expect(screen.getByText('Users Page')).toBeInTheDocument()
    expect(screen.getByText('Admin Layout')).toBeInTheDocument()
  })

  it('redirects to the forbidden page when the user lacks the required permission', () => {
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

    expect(screen.getByText('Forbidden Page')).toBeInTheDocument()
  })

  it('renders the not found page for unknown routes', () => {
    renderRoutes('/missing')

    expect(screen.getByText('Not Found Page')).toBeInTheDocument()
  })
})
