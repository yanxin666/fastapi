import { App as AntApp, ConfigProvider } from 'antd'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LoginPage } from './LoginPage'

const mockUseAuth = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderLoginPage(initialEntry: string | { pathname: string; search?: string; state?: unknown }) {
  render(
    <ConfigProvider>
      <AntApp>
        <MemoryRouter initialEntries={[initialEntry as never]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Dashboard Page</div>} />
            <Route path="/roles" element={<div>Roles Page</div>} />
          </Routes>
        </MemoryRouter>
      </AntApp>
    </ConfigProvider>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    )

    mockUseAuth.mockReset()
    mockUseAuth.mockReturnValue({
      accessToken: null,
      user: null,
      permissions: [],
      isLoading: false,
      login: vi.fn().mockResolvedValue({
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        is_active: true,
        is_superuser: false,
        roles: [],
        permissions: [],
      }),
      logout: vi.fn(),
    })
  })

  it('renders Chinese login copy', () => {
    renderLoginPage('/login')

    expect(screen.getByRole('heading', { name: '后台登录' })).toBeInTheDocument()
    expect(screen.getByText('请使用管理员账号登录后台管理系统。')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /登\s*录/ })).toBeInTheDocument()
  })

  it('redirects to the dashboard after a successful login without a previous target', async () => {
    const login = vi.fn().mockResolvedValue({
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      is_active: true,
      is_superuser: false,
      roles: [],
      permissions: [],
    })
    mockUseAuth.mockReturnValue({
      accessToken: null,
      user: null,
      permissions: [],
      isLoading: false,
      login,
      logout: vi.fn(),
    })

    renderLoginPage('/login')
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('请输入用户名'), 'admin')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'secret123')
    await user.click(screen.getByRole('button', { name: /登\s*录/ }))

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({ username: 'admin', password: 'secret123' })
    })
    expect(await screen.findByText('Dashboard Page')).toBeInTheDocument()
  })

  it('redirects to the previous protected route after a successful login', async () => {
    const login = vi.fn().mockResolvedValue({
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      is_active: true,
      is_superuser: false,
      roles: [],
      permissions: [],
    })
    mockUseAuth.mockReturnValue({
      accessToken: null,
      user: null,
      permissions: [],
      isLoading: false,
      login,
      logout: vi.fn(),
    })

    renderLoginPage({
      pathname: '/login',
      state: { from: { pathname: '/roles', search: '?source=login' } },
    })
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText('请输入用户名'), 'admin')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'secret123')
    await user.click(screen.getByRole('button', { name: /登\s*录/ }))

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({ username: 'admin', password: 'secret123' })
    })
    expect(await screen.findByText('Roles Page')).toBeInTheDocument()
  })
})
