/**
 * 认领策略管理页面
 *
 * 管理每个用户的客户认领上限，支持：
 * - 查看系统默认策略和所有用户专属策略
 * - 创建用户专属策略
 * - 编辑策略的认领上限
 * - 删除用户专属策略（恢复为系统默认）
 * - 权限控制（创建/编辑/删除需 STRATEGY_CREATE 权限）
 */

import {
  App as AntApp,
  Button,
  Card,
  Descriptions,
  Form,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { useAuth } from '../auth'
import {
  ApiError,
  createStrategy,
  deleteStrategy,
  listStrategies,
  listUsers,
  updateStrategy,
  type ClaimStrategy,
  type UserListItem,
} from '../lib/api-client'
import { useCan } from '../lib/permissions'

// ==================== 状态类型 ====================

type StrategiesState = {
  status: 'loading' | 'success' | 'error'
  items: ClaimStrategy[]
  message: string | null
}

// ==================== 工具函数 ====================

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error) {
    return error.message
  }
  return fallbackMessage
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  try {
    const date = new Date(value)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return value
  }
}

// ==================== 页面组件 ====================

export function ClaimStrategiesPage() {
  const { message: messageApi } = AntApp.useApp()
  const { accessToken, logout } = useAuth()
  const can = useCan()
  const canCreate = can('STRATEGY_CREATE')
  const canEdit = can('STRATEGY_EDIT')
  const canDelete = can('STRATEGY_DELETE')

  // 列表状态
  const [strategiesState, setStrategiesState] = useState<StrategiesState>({
    status: 'loading',
    items: [],
    message: null,
  })

  // 创建弹窗状态
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isCreateSubmitting, setIsCreateSubmitting] = useState(false)
  const [createForm] = Form.useForm()

  // 编辑弹窗状态
  const [editingStrategy, setEditingStrategy] = useState<ClaimStrategy | null>(null)
  const [isEditSubmitting, setIsEditSubmitting] = useState(false)
  const [editForm] = Form.useForm()

  // 删除确认弹窗状态
  const [deletingStrategy, setDeletingStrategy] = useState<ClaimStrategy | null>(null)
  const [isDeleteSubmitting, setIsDeleteSubmitting] = useState(false)

  // 用户列表（用于创建时选择用户）
  const [usersList, setUsersList] = useState<UserListItem[]>([])

  // ==================== 401 处理 ====================

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

  // ==================== 数据加载 ====================

  const loadStrategies = useCallback(async () => {
    if (!accessToken) return

    setStrategiesState((prev) => ({
      status: 'loading',
      items: prev.items,
      message: null,
    }))

    try {
      const result = await listStrategies(accessToken)
      setStrategiesState({
        status: 'success',
        items: result.items,
        message: null,
      })
    } catch (error) {
      if (await handleUnauthorized(error)) return
      setStrategiesState((prev) => ({
        status: 'error',
        items: prev.items,
        message: getErrorMessage(error, '加载认领策略失败'),
      }))
    }
  }, [accessToken, handleUnauthorized])

  useEffect(() => {
    void loadStrategies()
  }, [loadStrategies])

  // ==================== 创建弹窗 ====================

  const openCreateModal = async () => {
    if (!accessToken) return

    createForm.resetFields()
    createForm.setFieldsValue({ max_claim_count: 50 })

    // 加载用户列表
    if (usersList.length === 0) {
      try {
        const result = await listUsers(accessToken)
        setUsersList(result.items.filter((u) => u.is_active))
      } catch (error) {
        if (await handleUnauthorized(error)) return
        messageApi.error(getErrorMessage(error, '加载用户列表失败'))
      }
    }
    setIsCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setIsCreateModalOpen(false)
    createForm.resetFields()
  }

  const handleCreate = async (values: { user_id: number | null; max_claim_count: number }) => {
    if (!accessToken) return

    setIsCreateSubmitting(true)
    try {
      await createStrategy(accessToken, {
        user_id: values.user_id,
        max_claim_count: values.max_claim_count,
      })
      closeCreateModal()
      messageApi.success('认领策略创建成功')
      await loadStrategies()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '创建认领策略失败'))
    } finally {
      setIsCreateSubmitting(false)
    }
  }

  // ==================== 编辑弹窗 ====================

  const openEditModal = (strategy: ClaimStrategy) => {
    editForm.resetFields()
    editForm.setFieldsValue({ max_claim_count: strategy.max_claim_count })
    setEditingStrategy(strategy)
  }

  const closeEditModal = () => {
    setEditingStrategy(null)
    editForm.resetFields()
  }

  const handleEdit = async (values: { max_claim_count: number }) => {
    if (!accessToken || !editingStrategy) return

    setIsEditSubmitting(true)
    try {
      await updateStrategy(accessToken, editingStrategy.id, values.max_claim_count)
      closeEditModal()
      messageApi.success('认领策略更新成功')
      await loadStrategies()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '编辑认领策略失败'))
    } finally {
      setIsEditSubmitting(false)
    }
  }

  // ==================== 删除确认 ====================

  const openDeleteModal = (strategy: ClaimStrategy) => {
    setDeletingStrategy(strategy)
  }

  const closeDeleteModal = () => {
    setDeletingStrategy(null)
  }

  const handleDelete = async () => {
    if (!accessToken || !deletingStrategy) return

    setIsDeleteSubmitting(true)
    try {
      await deleteStrategy(accessToken, deletingStrategy.id)
      closeDeleteModal()
      messageApi.success('认领策略已删除，该用户将使用系统默认策略')
      await loadStrategies()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '删除认领策略失败'))
    } finally {
      setIsDeleteSubmitting(false)
    }
  }

  // ==================== 表格列定义 ====================

  // 分离默认策略和用户策略
  const defaultStrategy = strategiesState.items.find((s) => s.is_default)
  const userStrategies = strategiesState.items.filter((s) => !s.is_default)

  const columns: TableColumnsType<ClaimStrategy> = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 150,
      render: (value: string | null) => value || '-',
    },
    {
      title: '认领上限',
      dataIndex: 'max_claim_count',
      key: 'max_claim_count',
      width: 120,
    },
    {
      title: '当前已认领',
      dataIndex: 'current_claim_count',
      key: 'current_claim_count',
      width: 120,
      render: (value: number, record: ClaimStrategy) => {
        // 超过上限时标红提示
        if (value > record.max_claim_count) {
          return <Typography.Text type="danger">{value}（超限）</Typography.Text>
        }
        return value
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      render: (value: string | null) => formatDateTime(value),
    },
  ]

  // 操作列
  if (canEdit || canDelete) {
    columns.push({
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, strategy) => (
        <Space wrap>
          {canEdit ? (
            <Button size="small" onClick={() => openEditModal(strategy)}>
              编辑
            </Button>
          ) : null}
          {canDelete ? (
            <Button size="small" danger onClick={() => openDeleteModal(strategy)}>
              删除
            </Button>
          ) : null}
        </Space>
      ),
    })
  }

  // ==================== 渲染 ====================

  return (
    <>
      <Space direction="vertical" size="large" style={{ display: 'flex' }}>
        {/* 标题卡片 */}
        <Card
          title={<Typography.Title level={2} style={{ margin: 0 }}>认领策略</Typography.Title>}
          extra={
            <Space>
              <Button onClick={() => void loadStrategies()} loading={strategiesState.status === 'loading'}>
                刷新
              </Button>
              {canCreate ? (
                <Button type="primary" onClick={() => void openCreateModal()}>
                  新建策略
                </Button>
              ) : null}
            </Space>
          }
        >
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            管理每个用户的客户认领上限。删除用户策略后该用户将回退到系统默认策略。
          </Typography.Paragraph>
        </Card>

        {/* 系统默认策略 */}
        {defaultStrategy ? (
          <Card title="系统默认策略" size="small">
            <Descriptions size="small" column={2}>
              <Descriptions.Item label="认领上限">{defaultStrategy.max_claim_count}</Descriptions.Item>
              <Descriptions.Item label="操作">
                {canEdit ? (
                  <Button size="small" onClick={() => openEditModal(defaultStrategy)}>
                    编辑上限
                  </Button>
                ) : null}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        ) : null}

        {/* 错误提示 */}
        {strategiesState.status === 'error' && strategiesState.message ? (
          <Typography.Text type="danger">{strategiesState.message}</Typography.Text>
        ) : null}

        {/* 用户策略表格 */}
        <Card title="用户专属策略">
          <Table<ClaimStrategy>
            rowKey="id"
            columns={columns}
            dataSource={userStrategies}
            loading={strategiesState.status === 'loading'}
            pagination={false}
          />
        </Card>
      </Space>

      {/* 创建弹窗 */}
      <Modal
        title="新建认领策略"
        open={isCreateModalOpen}
        onCancel={closeCreateModal}
        onOk={() => void createForm.submit()}
        okText="创建"
        confirmLoading={isCreateSubmitting}
      >
        <Form form={createForm} layout="vertical" onFinish={(values) => void handleCreate(values)}>
          <Form.Item
            label="用户"
            name="user_id"
            rules={[{ required: true, message: '请选择用户' }]}
          >
            <Select
              showSearch
              placeholder="选择用户"
              optionFilterProp="label"
              options={usersList.map((u) => ({
                label: `${u.username}（ID: ${u.id}）`,
                value: u.id,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="认领上限"
            name="max_claim_count"
            rules={[{ required: true, message: '请填写认领上限' }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title={editingStrategy ? `编辑策略：${editingStrategy.username || `用户 #${editingStrategy.user_id}`}` : '编辑策略'}
        open={editingStrategy !== null}
        onCancel={closeEditModal}
        onOk={() => void editForm.submit()}
        okText="保存"
        confirmLoading={isEditSubmitting}
      >
        <Form form={editForm} layout="vertical" onFinish={(values) => void handleEdit(values)}>
          <Form.Item
            label="认领上限"
            name="max_claim_count"
            rules={[{ required: true, message: '请填写认领上限' }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 删除确认弹窗 */}
      <Modal
        title="删除认领策略"
        open={deletingStrategy !== null}
        onCancel={closeDeleteModal}
        onOk={() => void handleDelete()}
        okText="确认删除"
        okButtonProps={{ danger: true }}
        confirmLoading={isDeleteSubmitting}
      >
        <Typography.Paragraph>
          确认删除用户 <Typography.Text strong>{deletingStrategy?.username || `#${deletingStrategy?.user_id}`}</Typography.Text> 的认领策略吗？
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary">
          删除后该用户将使用系统默认策略（上限 {defaultStrategy?.max_claim_count ?? 50}）。
        </Typography.Paragraph>
      </Modal>
    </>
  )
}
