import { beforeEach, describe, expect, it, vi } from 'vitest'

async function loadApiClient() {
  vi.resetModules()
  return import('./api-client')
}

describe('admin api client', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/api/v1/admin/')
  })

  it('requests the health endpoint from the configured admin base url', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { getAdminHealth } = await loadApiClient()

    await expect(getAdminHealth()).resolves.toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/health', {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  })

  it('posts login credentials and maps token fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer',
        user: {
          id: 1,
          username: 'admin',
          email: 'admin@example.com',
          is_active: true,
          is_superuser: true,
          roles: ['admin'],
          permissions: ['user:view'],
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { loginAdmin } = await loadApiClient()

    await expect(loginAdmin({ username: 'admin', password: 'secret' })).resolves.toEqual({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      tokenType: 'bearer',
      user: {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        is_active: true,
        is_superuser: true,
        roles: ['admin'],
        permissions: ['user:view'],
      },
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username: 'admin', password: 'secret' }),
    })
  })

  it('sends the bearer token when fetching the current admin user', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        is_active: true,
        is_superuser: true,
        roles: ['admin'],
        permissions: ['user:view', 'role:view'],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { getCurrentAdminUser } = await loadApiClient()

    await expect(getCurrentAdminUser('access-token')).resolves.toMatchObject({
      username: 'admin',
      permissions: ['user:view', 'role:view'],
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/auth/me', {
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
    })
  })

  it('posts refresh token payload when refreshing the session', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'next-access-token',
        refresh_token: 'next-refresh-token',
        token_type: 'bearer',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { refreshAdminToken } = await loadApiClient()

    await expect(refreshAdminToken('refresh-token')).resolves.toEqual({
      accessToken: 'next-access-token',
      refreshToken: 'next-refresh-token',
      tokenType: 'bearer',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: 'refresh-token' }),
    })
  })

  it('posts refresh token payload when logging out', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { logoutAdmin } = await loadApiClient()

    await expect(logoutAdmin('refresh-token')).resolves.toEqual({ success: true })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: 'refresh-token' }),
    })
  })

  it('uses backend error messages for failed list requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ message: 'Permission denied' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { ApiError, listUsers } = await loadApiClient()

    await expect(listUsers('access-token')).rejects.toMatchObject({
      name: ApiError.name,
      status: 403,
      message: 'Permission denied',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/users', {
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
    })
  })

  it('posts user creation payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: 2,
        username: 'editor',
        email: 'editor@example.com',
        is_active: true,
        is_superuser: false,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { createUser } = await loadApiClient()

    await expect(
      createUser('access-token', {
        username: 'editor',
        email: 'editor@example.com',
        password: 'secret123',
      }),
    ).resolves.toMatchObject({
      id: 2,
      username: 'editor',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({
        username: 'editor',
        email: 'editor@example.com',
        password: 'secret123',
      }),
    })
  })

  it('requests user details from the detail endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 2,
        username: 'editor',
        email: 'editor@example.com',
        is_active: true,
        is_superuser: false,
        roles: ['auditor'],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { getUserDetail } = await loadApiClient()

    await expect(getUserDetail('access-token', 2)).resolves.toEqual({
      id: 2,
      username: 'editor',
      email: 'editor@example.com',
      is_active: true,
      is_superuser: false,
      roles: ['auditor'],
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/users/2', {
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
    })
  })

  it('posts user update payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 2,
        username: 'editor-updated',
        email: 'editor-updated@example.com',
        is_active: true,
        is_superuser: false,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { updateUser } = await loadApiClient()

    await expect(
      updateUser('access-token', 2, {
        username: 'editor-updated',
        email: 'editor-updated@example.com',
      }),
    ).resolves.toMatchObject({
      username: 'editor-updated',
      email: 'editor-updated@example.com',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/users/2/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({
        username: 'editor-updated',
        email: 'editor-updated@example.com',
      }),
    })
  })

  it('posts user role assignment payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { assignUserRoles } = await loadApiClient()

    await expect(assignUserRoles('access-token', 2, [3, 4])).resolves.toEqual({ success: true })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/users/2/roles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({ role_ids: [3, 4] }),
    })
  })

  it('posts toggle user active request without a body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 2,
        username: 'editor',
        email: 'editor@example.com',
        is_active: false,
        is_superuser: false,
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { toggleUserActive } = await loadApiClient()

    await expect(toggleUserActive('access-token', 2)).resolves.toMatchObject({ is_active: false })

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/admin/users/2/toggle-active',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer access-token',
        },
      },
    )
  })

  it('requests role details from the detail endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 2,
        name: 'auditor',
        description: 'audit role',
        permissions: ['user:create', 'user:view'],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { getRoleDetail } = await loadApiClient()

    await expect(getRoleDetail('access-token', 2)).resolves.toEqual({
      id: 2,
      name: 'auditor',
      description: 'audit role',
      permissions: ['user:create', 'user:view'],
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/roles/2', {
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
    })
  })

  it('posts role creation payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        id: 2,
        name: 'auditor',
        description: 'audit role',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { createRole } = await loadApiClient()

    await expect(
      createRole('access-token', {
        name: 'auditor',
        description: 'audit role',
      }),
    ).resolves.toEqual({
      id: 2,
      name: 'auditor',
      description: 'audit role',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/roles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({
        name: 'auditor',
        description: 'audit role',
      }),
    })
  })

  it('posts role update payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: 2,
        name: 'auditor-updated',
        description: 'updated audit role',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { updateRole } = await loadApiClient()

    await expect(
      updateRole('access-token', 2, {
        name: 'auditor-updated',
        description: 'updated audit role',
      }),
    ).resolves.toEqual({
      id: 2,
      name: 'auditor-updated',
      description: 'updated audit role',
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/roles/2/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({
        name: 'auditor-updated',
        description: 'updated audit role',
      }),
    })
  })

  it('posts role permission assignment payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { assignRolePermissions } = await loadApiClient()

    await expect(assignRolePermissions('access-token', 2, [3, 4])).resolves.toEqual({ success: true })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/roles/2/permissions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
      body: JSON.stringify({ permission_ids: [3, 4] }),
    })
  })

  it('posts role delete request without a body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { deleteRole } = await loadApiClient()

    await expect(deleteRole('access-token', 2)).resolves.toEqual({ success: true })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/admin/roles/2/delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer access-token',
      },
    })
  })
})
