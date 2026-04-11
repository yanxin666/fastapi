import { App as AntApp, ConfigProvider } from 'antd'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RolesPage } from './RolesPage'
import {
  assignRolePermissions,
  createRole,
  deleteRole,
  getRoleDetail,
  listPermissions,
  listRoles,
  updateRole,
} from '../lib/api-client'

const mockUseAuth = vi.fn()

vi.mock('../auth', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../lib/api-client', async () => {
  const actual = await vi.importActual<typeof import('../lib/api-client')>('../lib/api-client')

  return {
    ...actual,
    assignRolePermissions: vi.fn(),
    createRole: vi.fn(),
    deleteRole: vi.fn(),
    getRoleDetail: vi.fn(),
    listPermissions: vi.fn(),
    listRoles: vi.fn(),
    updateRole: vi.fn(),
  }
})

function renderRolesPage() {
  render(
    <ConfigProvider>
      <AntApp>
        <RolesPage />
      </AntApp>
    </ConfigProvider>,
  )
}

describe('RolesPage', () => {
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
      accessToken: 'access-token',
      user: null,
      permissions: ['role:view', 'role:update', 'permission:view'],
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    vi.mocked(listRoles).mockResolvedValue({
      items: [{ id: 1, name: '管理员', description: '系统管理员' }],
    })
    vi.mocked(listPermissions).mockResolvedValue({
      items: [
        { id: 11, code: 'user:view', description: '用户查看' },
        { id: 12, code: 'user:create', description: '用户创建' },
        { id: 21, code: 'role:view', description: '角色查看' },
      ],
    })
    vi.mocked(getRoleDetail).mockResolvedValue({
      id: 1,
      name: '管理员',
      description: '系统管理员',
      permissions: ['user:view'],
    })
    vi.mocked(assignRolePermissions).mockResolvedValue({ success: true })
    vi.mocked(createRole).mockResolvedValue({ id: 2, name: '审计员', description: '审计角色' })
    vi.mocked(updateRole).mockResolvedValue({ id: 1, name: '管理员', description: '系统管理员' })
    vi.mocked(deleteRole).mockResolvedValue({ success: true })
  })

  it('groups permissions by code prefix and preselects assigned permissions', async () => {
    renderRolesPage()
    const user = userEvent.setup()

    await screen.findByText('管理员')
    await user.click(screen.getByRole('button', { name: '权限分配' }))

    expect(await screen.findByRole('button', { name: '全选全部权限' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /^user/ })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /^role/ })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: '用户查看' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: '用户创建' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: '角色查看' })).not.toBeChecked()
    expect(screen.getByText('已选择 1 / 3 项')).toBeInTheDocument()
  }, 10000)

  it('toggles a permission group on and off', async () => {
    renderRolesPage()
    const user = userEvent.setup()

    await screen.findByText('管理员')
    await user.click(screen.getByRole('button', { name: '权限分配' }))

    const userGroupCheckbox = await screen.findByRole('checkbox', { name: /^user/ })

    await user.click(userGroupCheckbox)
    expect(screen.getByRole('checkbox', { name: '用户查看' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: '用户创建' })).toBeChecked()
    expect(screen.getByText('已选择 2 / 3 项')).toBeInTheDocument()

    await user.click(userGroupCheckbox)
    expect(screen.getByRole('checkbox', { name: '用户查看' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: '用户创建' })).not.toBeChecked()
    expect(screen.getByText('已选择 0 / 3 项')).toBeInTheDocument()
  }, 10000)

  it('selects all permissions and submits selected ids', async () => {
    renderRolesPage()
    const user = userEvent.setup()

    await screen.findByText('管理员')
    await user.click(screen.getByRole('button', { name: '权限分配' }))
    await user.click(await screen.findByRole('button', { name: '全选全部权限' }))
    await user.click(screen.getByRole('button', { name: '保存权限' }))

    await waitFor(() => {
      expect(assignRolePermissions).toHaveBeenCalledWith('access-token', 1, [11, 12, 21])
    })
  }, 10000)
})
