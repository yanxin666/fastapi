import {
  App as AntApp,
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useAuth } from '../auth'
import {
  ApiError,
  assignRolePermissions,
  createRole,
  deleteRole,
  getRoleDetail,
  listPermissions,
  listRoles,
  updateRole,
  type CreateRoleInput,
  type PermissionListItem,
  type RoleListItem,
  type UpdateRoleInput,
} from '../lib/api-client'

type RolesState = {
  status: 'loading' | 'success' | 'error'
  items: RoleListItem[]
  message: string | null
}

type PermissionsState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  items: PermissionListItem[]
  message: string | null
}

type PermissionFormValues = {
  permissionIds: number[]
}

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error) {
    return error.message
  }

  return fallbackMessage
}

function getPermissionGroupKey(permissionCode: string): string {
  const separatorIndex = permissionCode.indexOf(':')

  if (separatorIndex === -1) {
    return permissionCode
  }

  return permissionCode.slice(0, separatorIndex)
}

export function RolesPage() {
  const { message } = AntApp.useApp()
  const { accessToken, logout, permissions } = useAuth()
  const canCreateRoles = permissions.includes('role:create')
  const canUpdateRoles = permissions.includes('role:update')
  const canDeleteRoles = permissions.includes('role:delete')
  const canViewPermissions = permissions.includes('permission:view')

  const [rolesState, setRolesState] = useState<RolesState>({
    status: 'loading',
    items: [],
    message: null,
  })
  const [permissionsState, setPermissionsState] = useState<PermissionsState>({
    status: 'idle',
    items: [],
    message: null,
  })

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleListItem | null>(null)
  const [permissionRole, setPermissionRole] = useState<RoleListItem | null>(null)
  const [deletingRole, setDeletingRole] = useState<RoleListItem | null>(null)

  const [isCreateSubmitting, setIsCreateSubmitting] = useState(false)
  const [isEditSubmitting, setIsEditSubmitting] = useState(false)
  const [isPermissionSubmitting, setIsPermissionSubmitting] = useState(false)
  const [isDeleteSubmitting, setIsDeleteSubmitting] = useState(false)
  const [permissionDetailLoadingRoleId, setPermissionDetailLoadingRoleId] = useState<number | null>(null)

  const [createForm] = Form.useForm<CreateRoleInput>()
  const [editForm] = Form.useForm<UpdateRoleInput>()
  const [permissionsForm] = Form.useForm<PermissionFormValues>()
  const selectedPermissionIds = Form.useWatch('permissionIds', permissionsForm) ?? []

  const permissionGroups = useMemo(() => {
    const groups = new Map<string, PermissionListItem[]>()

    permissionsState.items.forEach((permission) => {
      const groupKey = getPermissionGroupKey(permission.code)
      const currentGroup = groups.get(groupKey)

      if (currentGroup) {
        currentGroup.push(permission)
        return
      }

      groups.set(groupKey, [permission])
    })

    return Array.from(groups.entries()).map(([groupKey, items]) => ({
      groupKey,
      items,
    }))
  }, [permissionsState.items])

  const allPermissionIds = useMemo(
    () => permissionsState.items.map((permission) => permission.id),
    [permissionsState.items],
  )

  const isPermissionSelectionDisabled =
    permissionsState.status === 'loading' || permissionDetailLoadingRoleId !== null

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

  const loadRoles = useCallback(async () => {
    if (!accessToken) {
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

      setRolesState((currentState) => ({
        status: 'error',
        items: currentState.items,
        message: getErrorMessage(error, '加载角色列表失败'),
      }))
    }
  }, [accessToken, handleUnauthorized])

  const loadPermissions = useCallback(async () => {
    if (!accessToken || !canUpdateRoles || !canViewPermissions) {
      return
    }

    setPermissionsState((currentState) => ({
      status: 'loading',
      items: currentState.items,
      message: null,
    }))

    try {
      const result = await listPermissions(accessToken)
      setPermissionsState({ status: 'success', items: result.items, message: null })
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      setPermissionsState({
        status: 'error',
        items: [],
        message: getErrorMessage(error, '加载权限列表失败'),
      })
    }
  }, [accessToken, canUpdateRoles, canViewPermissions, handleUnauthorized])

  useEffect(() => {
    void loadRoles()
  }, [loadRoles])

  useEffect(() => {
    if (!canUpdateRoles || !canViewPermissions) {
      return
    }

    void loadPermissions()
  }, [canUpdateRoles, canViewPermissions, loadPermissions])

  const openCreateModal = () => {
    createForm.setFieldsValue({ description: null, name: '' })
    setIsCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setIsCreateModalOpen(false)
    createForm.resetFields()
  }

  const openEditModal = (role: RoleListItem) => {
    editForm.setFieldsValue({
      name: role.name,
      description: role.description,
    })
    setEditingRole(role)
  }

  const closeEditModal = () => {
    setEditingRole(null)
    editForm.resetFields()
  }

  const openPermissionsModal = async (role: RoleListItem) => {
    if (!accessToken || !canViewPermissions) {
      return
    }

    setPermissionRole(role)
    setPermissionDetailLoadingRoleId(role.id)
    permissionsForm.resetFields()

    try {
      let availablePermissions = permissionsState.items

      if (!availablePermissions.length) {
        const permissionsResult = await listPermissions(accessToken)
        availablePermissions = permissionsResult.items
        setPermissionsState({ status: 'success', items: availablePermissions, message: null })
      }

      const detail = await getRoleDetail(accessToken, role.id)
      const assignedPermissionIds = availablePermissions
        .filter((permission) => detail.permissions.includes(permission.code))
        .map((permission) => permission.id)

      permissionsForm.setFieldsValue({ permissionIds: assignedPermissionIds })
    } catch (error) {
      setPermissionRole(null)

      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '加载角色权限失败'))
    } finally {
      setPermissionDetailLoadingRoleId(null)
    }
  }

  const closePermissionsModal = () => {
    setPermissionRole(null)
    permissionsForm.resetFields()
  }

  const openDeleteModal = (role: RoleListItem) => {
    setDeletingRole(role)
  }

  const closeDeleteModal = () => {
    setDeletingRole(null)
  }

  const handleCreateRole = async (values: CreateRoleInput) => {
    if (!accessToken) {
      return
    }

    setIsCreateSubmitting(true)

    try {
      await createRole(accessToken, {
        name: values.name,
        description: values.description?.trim() ? values.description.trim() : null,
      })
      closeCreateModal()
      message.success('角色创建成功')
      await loadRoles()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '创建角色失败'))
    } finally {
      setIsCreateSubmitting(false)
    }
  }

  const handleEditRole = async (values: UpdateRoleInput) => {
    if (!accessToken || !editingRole) {
      return
    }

    setIsEditSubmitting(true)

    try {
      await updateRole(accessToken, editingRole.id, {
        name: values.name,
        description: values.description?.trim() ? values.description.trim() : null,
      })
      closeEditModal()
      message.success('角色更新成功')
      await loadRoles()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '更新角色失败'))
    } finally {
      setIsEditSubmitting(false)
    }
  }

  const handleAssignPermissions = async (values: PermissionFormValues) => {
    if (!accessToken || !permissionRole) {
      return
    }

    setIsPermissionSubmitting(true)

    try {
      await assignRolePermissions(accessToken, permissionRole.id, values.permissionIds ?? [])
      closePermissionsModal()
      message.success('角色权限更新成功')
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '更新角色权限失败'))
    } finally {
      setIsPermissionSubmitting(false)
    }
  }

  const updateSelectedPermissionIds = (permissionIds: number[]) => {
    permissionsForm.setFieldsValue({ permissionIds })
  }

  const handleTogglePermission = (permissionId: number, checked: boolean) => {
    const nextPermissionIds = checked
      ? [...selectedPermissionIds, permissionId]
      : selectedPermissionIds.filter((currentPermissionId) => currentPermissionId !== permissionId)

    updateSelectedPermissionIds(Array.from(new Set(nextPermissionIds)))
  }

  const handleTogglePermissionGroup = (groupPermissionIds: number[], checked: boolean) => {
    const nextPermissionIds = checked
      ? Array.from(new Set([...selectedPermissionIds, ...groupPermissionIds]))
      : selectedPermissionIds.filter((permissionId) => !groupPermissionIds.includes(permissionId))

    updateSelectedPermissionIds(nextPermissionIds)
  }

  const handleSelectAllPermissions = () => {
    updateSelectedPermissionIds(allPermissionIds)
  }

  const handleClearAllPermissions = () => {
    updateSelectedPermissionIds([])
  }

  const handleDeleteRole = async () => {
    if (!accessToken || !deletingRole) {
      return
    }

    setIsDeleteSubmitting(true)

    try {
      await deleteRole(accessToken, deletingRole.id)
      closeDeleteModal()
      message.success('角色删除成功')
      await loadRoles()
    } catch (error) {
      if (await handleUnauthorized(error)) {
        return
      }

      message.error(getErrorMessage(error, '删除角色失败'))
    } finally {
      setIsDeleteSubmitting(false)
    }
  }

  const columns: TableColumnsType<RoleListItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (value: string | null) => value || '-',
    },
  ]

  if (canUpdateRoles || canDeleteRoles) {
    columns.push({
      title: '操作',
      key: 'actions',
      render: (_, role) => (
        <Space wrap>
          {canUpdateRoles ? (
            <Button size="small" onClick={() => openEditModal(role)}>
              编辑
            </Button>
          ) : null}
          {canUpdateRoles && canViewPermissions ? (
            <Button
              size="small"
              onClick={() => void openPermissionsModal(role)}
              loading={permissionDetailLoadingRoleId === role.id}
            >
              权限分配
            </Button>
          ) : null}
          {canDeleteRoles ? (
            <Button size="small" danger onClick={() => openDeleteModal(role)}>
              删除
            </Button>
          ) : null}
        </Space>
      ),
    })
  }

  return (
    <>
      <Space direction="vertical" size="large" style={{ display: 'flex' }}>
        <Card
          title={<Typography.Title level={2} style={{ margin: 0 }}>角色管理</Typography.Title>}
          extra={
            <Space>
              <Button onClick={() => void loadRoles()} loading={rolesState.status === 'loading'}>
                刷新
              </Button>
              {canCreateRoles ? (
                <Button type="primary" onClick={openCreateModal}>
                  新建角色
                </Button>
              ) : null}
            </Space>
          }
        >
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            维护后台角色信息及其权限分配关系。
          </Typography.Paragraph>
        </Card>

        {rolesState.status === 'error' && rolesState.message ? (
          <Alert type="error" message={rolesState.message} showIcon />
        ) : null}

        {canUpdateRoles && !canViewPermissions ? (
          <Alert
            type="info"
            message="当前账号无法分配权限"
            description="当前账号虽然可以编辑角色，但缺少 permission:view 权限，因此无法加载权限列表。"
            showIcon
          />
        ) : null}

        {canDeleteRoles ? (
          <Alert
            type="info"
            message="删除角色为永久操作"
            description="角色仍被用户引用时，必须先解除用户关联后才能删除。"
            showIcon
          />
        ) : null}

        {canUpdateRoles && canViewPermissions && permissionsState.status === 'error' && permissionsState.message ? (
          <Alert
            type="warning"
            message={permissionsState.message}
            description="权限列表加载成功后才可执行权限分配操作。"
            showIcon
          />
        ) : null}

        <Card>
          <Table<RoleListItem>
            rowKey="id"
            columns={columns}
            dataSource={rolesState.items}
            loading={rolesState.status === 'loading'}
            pagination={false}
          />
        </Card>
      </Space>

      <Modal
        title="新建角色"
        open={isCreateModalOpen}
        onCancel={closeCreateModal}
        onOk={() => void createForm.submit()}
        okText="新建角色"
        confirmLoading={isCreateSubmitting}
      >
        <Form<CreateRoleInput> form={createForm} layout="vertical" onFinish={(values) => void handleCreateRole(values)}>
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input placeholder="请输入角色描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRole ? `编辑角色：${editingRole.name}` : '编辑角色'}
        open={editingRole !== null}
        onCancel={closeEditModal}
        onOk={() => void editForm.submit()}
        okText="保存"
        confirmLoading={isEditSubmitting}
      >
        <Form<UpdateRoleInput> form={editForm} layout="vertical" onFinish={(values) => void handleEditRole(values)}>
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input placeholder="请输入角色描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={permissionRole ? `分配权限：${permissionRole.name}` : '分配权限'}
        open={permissionRole !== null}
        onCancel={closePermissionsModal}
        onOk={() => void permissionsForm.submit()}
        okText="保存权限"
        okButtonProps={{
          disabled: permissionDetailLoadingRoleId !== null || permissionsState.status === 'error',
        }}
        confirmLoading={isPermissionSubmitting}
      >
        <Form<PermissionFormValues>
          form={permissionsForm}
          layout="vertical"
          onFinish={(values) => void handleAssignPermissions(values)}
        >
          <Form.Item label="权限" name="permissionIds" hidden>
            <Input />
          </Form.Item>

          <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
            <Space wrap align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
              <Space wrap>
                <Button
                  type="primary"
                  onClick={handleSelectAllPermissions}
                  disabled={isPermissionSelectionDisabled || permissionsState.status === 'error'}
                >
                  全选全部权限
                </Button>
                <Button onClick={handleClearAllPermissions} disabled={isPermissionSelectionDisabled}>
                  清空已选
                </Button>
              </Space>
              <Typography.Text type="secondary">
                已选择 {selectedPermissionIds.length} / {permissionsState.items.length} 项
              </Typography.Text>
            </Space>

            {permissionsState.status === 'success' && permissionGroups.length ? (
              <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                {permissionGroups.map((group) => {
                  const groupPermissionIds = group.items.map((permission) => permission.id)
                  const selectedCount = groupPermissionIds.filter((permissionId) => selectedPermissionIds.includes(permissionId)).length
                  const isGroupChecked = selectedCount > 0 && selectedCount === groupPermissionIds.length
                  const isGroupIndeterminate = selectedCount > 0 && selectedCount < groupPermissionIds.length

                  return (
                    <Card
                      key={group.groupKey}
                      size="small"
                      title={
                        <Space wrap>
                          <Checkbox
                            checked={isGroupChecked}
                            indeterminate={isGroupIndeterminate}
                            disabled={isPermissionSelectionDisabled}
                            onChange={(event) => {
                              handleTogglePermissionGroup(groupPermissionIds, event.target.checked)
                            }}
                          >
                            {group.groupKey}
                          </Checkbox>
                          <Typography.Text type="secondary">
                            已选 {selectedCount} / {groupPermissionIds.length}
                          </Typography.Text>
                        </Space>
                      }
                    >
                      <Space direction="vertical" size="small" style={{ display: 'flex' }}>
                        {group.items.map((permission) => (
                          <Checkbox
                            key={permission.id}
                            checked={selectedPermissionIds.includes(permission.id)}
                            disabled={isPermissionSelectionDisabled}
                            onChange={(event) => {
                              handleTogglePermission(permission.id, event.target.checked)
                            }}
                          >
                            {permission.description ?? permission.code}
                          </Checkbox>
                        ))}
                      </Space>
                    </Card>
                  )
                })}
              </Space>
            ) : null}
          </Space>
        </Form>
      </Modal>

      <Modal
        title={deletingRole ? `删除角色：${deletingRole.name}` : '删除角色'}
        open={deletingRole !== null}
        onCancel={closeDeleteModal}
        onOk={() => void handleDeleteRole()}
        okText="删除角色"
        okButtonProps={{ danger: true }}
        confirmLoading={isDeleteSubmitting}
      >
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          此操作将永久删除角色 <Typography.Text strong>{deletingRole?.name}</Typography.Text>。
        </Typography.Paragraph>
      </Modal>
    </>
  )
}
