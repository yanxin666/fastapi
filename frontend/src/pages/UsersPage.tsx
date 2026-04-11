import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { useAuth } from '../auth'
import {
  ApiError,
  assignUserRoles,
  createUser,
  getUserDetail,
  listRoles,
  listUsers,
  resetUserPassword,
  toggleUserActive,
  updateUser,
  type CreateUserInput,
  type RoleListItem,
  type UpdateUserInput,
  type UserListItem,
} from '../lib/api-client'

type UsersState = {
  status: 'loading' | 'success' | 'error'
  items: UserListItem[]
  message: string | null
}

type RolesState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  items: RoleListItem[]
  message: string | null
}

type PasswordFormValues = {
  password: string
}

type RoleFormValues = {
  roleIds: number[]
}

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error) {
    return error.message
  }

  return fallbackMessage
}

export function UsersPage() {
  const { message } = AntApp.useApp()
  const { accessToken, logout, permissions } = useAuth()
  const canManageUsers = permissions.includes('user:create')

  const [usersState, setUsersState] = useState<UsersState>({
    status: 'loading',
    items: [],
    message: null,
  })
  const [rolesState, setRolesState] = useState<RolesState>({
    status: 'idle',
    items: [],
    message: null,
  })

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null)
  const [roleUser, setRoleUser] = useState<UserListItem | null>(null)
  const [passwordUser, setPasswordUser] = useState<UserListItem | null>(null)

  const [isCreateSubmitting, setIsCreateSubmitting] = useState(false)
  const [isEditSubmitting, setIsEditSubmitting] = useState(false)
  const [isRoleSubmitting, setIsRoleSubmitting] = useState(false)
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false)
  const [roleDetailLoadingUserId, setRoleDetailLoadingUserId] = useState<number | null>(null)
  const [toggleLoadingUserId, setToggleLoadingUserId] = useState<number | null>(null)

  const [createForm] = Form.useForm<CreateUserInput>()
  const [editForm] = Form.useForm<UpdateUserInput>()
  const [rolesForm] = Form.useForm<RoleFormValues>()
  const [passwordForm] = Form.useForm<PasswordFormValues>()

  const handleUnauthorized = useCallback(
    async (error: unknown) => {
      if (error instanceof ApiError && error.status === 401) {
        await logout()
        return true
      }

      return false
    },
    [logout],
  )

  const loadUsers = useCallback(async () => {
    if (!accessToken) {
      return
    }

    setUsersState((currentState) => ({
      status: 'loading',
      items: currentState.items,
      message: null,
    }))

    try {
      const result = await listUsers(accessToken)
      setUsersState({ status: 'success', items: result.items, message: null })
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      setUsersState((currentState) => ({
        status: 'error',
        items: currentState.items,
        message: getErrorMessage(error, '加载用户列表失败'),
      }))
    }
  }, [accessToken, handleUnauthorized])

  const loadRoles = useCallback(async () => {
    if (!accessToken || !canManageUsers) {
      return
    }

    setRolesState((currentState) => ({
      status: 'loading',
      items: currentState.items,
      message: null,
    }))

    try {
      const result = await listRoles(accessToken)
      setRolesState({ status: 'success', items: result.items, message: null })
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      setRolesState({
        status: 'error',
        items: [],
        message: getErrorMessage(error, '加载角色列表失败'),
      })
    }
  }, [accessToken, canManageUsers, handleUnauthorized])

  useEffect(() => {
    void loadUsers()
  }, [loadUsers])

  useEffect(() => {
    if (!canManageUsers) {
      return
    }

    void loadRoles()
  }, [canManageUsers, loadRoles])

  const openCreateModal = () => {
    createForm.resetFields()
    setIsCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setIsCreateModalOpen(false)
    createForm.resetFields()
  }

  const openEditModal = (user: UserListItem) => {
    editForm.setFieldsValue({
      username: user.username,
      email: user.email,
    })
    setEditingUser(user)
  }

  const closeEditModal = () => {
    setEditingUser(null)
    editForm.resetFields()
  }

  const openPasswordModal = (user: UserListItem) => {
    passwordForm.resetFields()
    setPasswordUser(user)
  }

  const closePasswordModal = () => {
    setPasswordUser(null)
    passwordForm.resetFields()
  }

  const openRoleModal = async (user: UserListItem) => {
    if (!accessToken) {
      return
    }

    setRoleUser(user)
    setRoleDetailLoadingUserId(user.id)
    rolesForm.resetFields()

    try {
      let availableRoles = rolesState.items

      if (!availableRoles.length) {
        const rolesResult = await listRoles(accessToken)
        availableRoles = rolesResult.items
        setRolesState({ status: 'success', items: availableRoles, message: null })
      }

      const detail = await getUserDetail(accessToken, user.id)
      const assignedRoleIds = availableRoles
        .filter((role) => detail.roles.includes(role.name))
        .map((role) => role.id)

      rolesForm.setFieldsValue({ roleIds: assignedRoleIds })
    } catch (error) {
      setRoleUser(null)

      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '加载用户角色失败'))
    } finally {
      setRoleDetailLoadingUserId(null)
    }
  }

  const closeRoleModal = () => {
    setRoleUser(null)
    rolesForm.resetFields()
  }

  const handleCreateUser = async (values: CreateUserInput) => {
    if (!accessToken) {
      return
    }

    setIsCreateSubmitting(true)

    try {
      await createUser(accessToken, values)
      closeCreateModal()
      message.success('用户创建成功')
      await loadUsers()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '创建用户失败'))
    } finally {
      setIsCreateSubmitting(false)
    }
  }

  const handleEditUser = async (values: UpdateUserInput) => {
    if (!accessToken || !editingUser) {
      return
    }

    setIsEditSubmitting(true)

    try {
      await updateUser(accessToken, editingUser.id, values)
      closeEditModal()
      message.success('用户更新成功')
      await loadUsers()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '更新用户失败'))
    } finally {
      setIsEditSubmitting(false)
    }
  }

  const handleAssignRoles = async (values: RoleFormValues) => {
    if (!accessToken || !roleUser) {
      return
    }

    setIsRoleSubmitting(true)

    try {
      await assignUserRoles(accessToken, roleUser.id, values.roleIds ?? [])
      closeRoleModal()
      message.success('用户角色更新成功')
      await loadUsers()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '更新用户角色失败'))
    } finally {
      setIsRoleSubmitting(false)
    }
  }

  const handleResetPassword = async (values: PasswordFormValues) => {
    if (!accessToken || !passwordUser) {
      return
    }

    setIsPasswordSubmitting(true)

    try {
      await resetUserPassword(accessToken, passwordUser.id, values.password)
      closePasswordModal()
      message.success('密码重置成功')
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '重置密码失败'))
    } finally {
      setIsPasswordSubmitting(false)
    }
  }

  const handleToggleUserActive = async (user: UserListItem) => {
    if (!accessToken) {
      return
    }

    setToggleLoadingUserId(user.id)

    try {
      await toggleUserActive(accessToken, user.id)
      message.success(user.is_active ? '用户已禁用' : '用户已启用')
      await loadUsers()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '更新用户状态失败'))
    } finally {
      setToggleLoadingUserId(null)
    }
  }

  const columns: TableColumnsType<UserListItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '启用状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (value: boolean) => <Tag color={value ? 'green' : 'red'}>{value ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '超级管理员',
      dataIndex: 'is_superuser',
      key: 'is_superuser',
      render: (value: boolean) => <Tag color={value ? 'gold' : 'default'}>{value ? '是' : '否'}</Tag>,
    },
  ]

  if (canManageUsers) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (_, user) => (
        <Space wrap>
          <Button size="small" onClick={() => openEditModal(user)}>
            编辑
          </Button>
          <Button
            size="small"
            onClick={() => void openRoleModal(user)}
            loading={roleDetailLoadingUserId === user.id}
          >
            角色分配
          </Button>
          <Button size="small" onClick={() => openPasswordModal(user)}>
            重置密码
          </Button>
          <Button
            size="small"
            onClick={() => void handleToggleUserActive(user)}
            loading={toggleLoadingUserId === user.id}
          >
            {user.is_active ? '禁用' : '启用'}
          </Button>
        </Space>
      ),
    })
  }

  return (
    <>
      <Space direction="vertical" size="large" style={{ display: 'flex' }}>
        <Card
          title={<Typography.Title level={2} style={{ margin: 0 }}>用户管理</Typography.Title>}
          extra={
            <Space>
              <Button onClick={() => void loadUsers()} loading={usersState.status === 'loading'}>
                刷新
              </Button>
              {canManageUsers ? (
                <Button type="primary" onClick={openCreateModal}>
                  新建用户
                </Button>
              ) : null}
            </Space>
          }
        >
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            维护后台用户账号、启用状态、角色分配与密码重置。
          </Typography.Paragraph>
        </Card>

        {usersState.status === 'error' && usersState.message ? (
          <Alert type="error" message={usersState.message} showIcon />
        ) : null}

        {canManageUsers && rolesState.status === 'error' && rolesState.message ? (
          <Alert
            type="warning"
            message={rolesState.message}
            description="角色列表加载成功后才可执行角色分配操作。"
            showIcon
          />
        ) : null}

        <Card>
          <Table<UserListItem>
            rowKey="id"
            columns={columns}
            dataSource={usersState.items}
            loading={usersState.status === 'loading'}
            pagination={false}
          />
        </Card>
      </Space>

      <Modal
        title="新建用户"
        open={isCreateModalOpen}
        onCancel={closeCreateModal}
        onOk={() => void createForm.submit()}
        okText="新建用户"
        confirmLoading={isCreateSubmitting}
      >
        <Form<CreateUserInput> form={createForm} layout="vertical" onFinish={(values) => void handleCreateUser(values)}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingUser ? `编辑用户：${editingUser.username}` : '编辑用户'}
        open={editingUser !== null}
        onCancel={closeEditModal}
        onOk={() => void editForm.submit()}
        okText="保存"
        confirmLoading={isEditSubmitting}
      >
        <Form<UpdateUserInput> form={editForm} layout="vertical" onFinish={(values) => void handleEditUser(values)}>
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, message: '请输入邮箱地址' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={roleUser ? `分配角色：${roleUser.username}` : '分配角色'}
        open={roleUser !== null}
        onCancel={closeRoleModal}
        onOk={() => void rolesForm.submit()}
        okText="保存角色"
        okButtonProps={{ disabled: roleDetailLoadingUserId !== null || rolesState.status === 'error' }}
        confirmLoading={isRoleSubmitting}
      >
        <Form<RoleFormValues> form={rolesForm} layout="vertical" onFinish={(values) => void handleAssignRoles(values)}>
          <Form.Item label="角色" name="roleIds">
            <Select
              mode="multiple"
              placeholder="请选择角色"
              loading={rolesState.status === 'loading' || roleDetailLoadingUserId !== null}
              options={rolesState.items.map((role) => ({
                label: role.description ? `${role.name} (${role.description})` : role.name,
                value: role.id,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={passwordUser ? `重置密码：${passwordUser.username}` : '重置密码'}
        open={passwordUser !== null}
        onCancel={closePasswordModal}
        onOk={() => void passwordForm.submit()}
        okText="重置密码"
        confirmLoading={isPasswordSubmitting}
      >
        <Form<PasswordFormValues>
          form={passwordForm}
          layout="vertical"
          onFinish={(values) => void handleResetPassword(values)}
        >
          <Form.Item
            label="新密码"
            name="password"
            rules={[{ required: true, message: '请输入新密码' }]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
