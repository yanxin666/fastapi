/**
 * 长期客户页面
 *
 * 展示当前用户占有的长期客户列表，支持：
 * - 固定按 claimed_by=当前用户 且 claim_status=possession 筛选
 * - 跟进记录查看/创建
 * - 释放/批量释放认领
 * - 权限控制（需 CUSTOMER_CLAIM 权限访问）
 */

import {
  App as AntApp,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'

import { useAuth } from '../auth'
import {
  ApiError,
  batchReleaseCustomers,
  createFollowup,
  deleteFollowup,
  listCustomers,
  listFollowups,
  releaseCustomer,
  type CustomerDetail,
  type FollowupRecord,
} from '../lib/api-client'
import { useCan } from '../lib/permissions'

// ==================== 状态类型 ====================

type CustomersState = {
  status: 'loading' | 'success' | 'error'
  items: CustomerDetail[]
  total: number
  message: string | null
}

type FollowupsState = {
  status: 'loading' | 'success' | 'error'
  items: FollowupRecord[]
  total: number
  message: string | null
}

// ==================== 常量 ====================

const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

/** 跟进方式选项 */
const FOLLOWUP_METHOD_OPTIONS = [
  { label: '电话', value: '电话' },
  { label: '微信', value: '微信' },
  { label: '面访', value: '面访' },
  { label: '其他', value: '其他' },
]

/** 跟进意向度选项 */
const FOLLOWUP_INTENTION_OPTIONS = [
  { label: '不需要', value: '不需要' },
  { label: '无人接听', value: '无人接听' },
  { label: '拒接', value: '拒接' },
  { label: '接通挂断', value: '接通挂断' },
  { label: '加了微信未通过', value: '加了微信未通过' },
  { label: '已加上微信', value: '已加上微信' },
  { label: '电话空号', value: '电话空号' },
  { label: '微信空号', value: '微信空号' },
  { label: '无效数据', value: '无效数据' },
  { label: '走完流程', value: '走完流程' },
]

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

export function LongTermCustomersPage() {
  const { message: messageApi } = AntApp.useApp()
  const { accessToken, logout, user: currentUser } = useAuth()
  const can = useCan()
  const canRelease = can('CUSTOMER_RELEASE')
  const canFollowupView = can('FOLLOWUP_VIEW')
  const canFollowupCreate = can('FOLLOWUP_CREATE')
  const canFollowupDelete = can('FOLLOWUP_DELETE')

  // 列表状态
  const [customersState, setCustomersState] = useState<CustomersState>({
    status: 'loading',
    items: [],
    total: 0,
    message: null,
  })

  // 筛选参数
  const [keyword, setKeyword] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(DEFAULT_PAGE)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  // 行选择状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])

  // 释放状态
  const [releasingCustomerId, setReleasingCustomerId] = useState<number | null>(null)
  const [isBatchReleaseSubmitting, setIsBatchReleaseSubmitting] = useState(false)

  // 跟进记录弹窗状态
  const [followupCustomerId, setFollowupCustomerId] = useState<number | null>(null)
  const [followupsState, setFollowupsState] = useState<FollowupsState>({
    status: 'loading',
    items: [],
    total: 0,
    message: null,
  })
  const [followupPage, setFollowupPage] = useState(1)
  const [followupPageSize] = useState(10)

  // 创建跟进弹窗状态
  const [isFollowupCreateOpen, setIsFollowupCreateOpen] = useState(false)
  const [isFollowupCreateSubmitting, setIsFollowupCreateSubmitting] = useState(false)
  // 创建跟进弹窗对应的客户 ID，与 followupCustomerId（列表弹窗）独立
  const [createFollowupCustomerId, setCreateFollowupCustomerId] = useState<number | null>(null)
  const [followupForm] = Form.useForm()

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

  const loadCustomers = useCallback(async () => {
    if (!accessToken || !currentUser) return

    setCustomersState((prev) => ({
      status: 'loading',
      items: prev.items,
      total: prev.total,
      message: null,
    }))

    try {
      // 长期客户筛选：claim_status=possession
      const result = await listCustomers(accessToken, {
        keyword: keyword || undefined,
        claim_status: 'possession',
        claimed_by: currentUser.id,
        page: currentPage,
        page_size: pageSize,
      })
      setCustomersState({
        status: 'success',
        items: result.items,
        total: result.total,
        message: null,
      })
    } catch (error) {
      if (await handleUnauthorized(error)) return
      setCustomersState((prev) => ({
        status: 'error',
        items: prev.items,
        total: prev.total,
        message: getErrorMessage(error, '加载长期客户失败'),
      }))
    }
  }, [accessToken, keyword, currentUser, currentPage, pageSize, handleUnauthorized])

  useEffect(() => {
    void loadCustomers()
  }, [loadCustomers])

  // ==================== 释放操作 ====================

  const handleRelease = async (customerId: number) => {
    if (!accessToken) return

    setReleasingCustomerId(customerId)
    try {
      await releaseCustomer(accessToken, customerId)
      messageApi.success('释放成功')
      setSelectedRowKeys([])
      await loadCustomers()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '释放失败'))
    } finally {
      setReleasingCustomerId(null)
    }
  }

  const handleBatchRelease = async () => {
    if (!accessToken || selectedRowKeys.length === 0) return

    setIsBatchReleaseSubmitting(true)
    try {
      const result = await batchReleaseCustomers(accessToken, selectedRowKeys)
      if (result.failed.length === 0) {
        messageApi.success(`释放成功 ${result.success.length} 条`)
      } else if (result.success.length === 0) {
        messageApi.error('释放全部失败')
      } else {
        messageApi.warning(`释放成功 ${result.success.length} 条，失败 ${result.failed.length} 条`)
      }
      setSelectedRowKeys([])
      await loadCustomers()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '批量释放失败'))
    } finally {
      setIsBatchReleaseSubmitting(false)
    }
  }

  // ==================== 跟进记录 ====================

  const openFollowupModal = async (customerId: number) => {
    if (!accessToken) return

    setFollowupCustomerId(customerId)
    setFollowupPage(1)
    setFollowupsState({ status: 'loading', items: [], total: 0, message: null })
    await loadFollowups(customerId, 1)
  }

  const loadFollowups = async (customerId: number, page: number) => {
    if (!accessToken) return

    setFollowupsState((prev) => ({ ...prev, status: 'loading' }))
    try {
      const result = await listFollowups(accessToken, customerId, page, followupPageSize)
      setFollowupsState({ status: 'success', items: result.items, total: result.total, message: null })
    } catch (error) {
      if (await handleUnauthorized(error)) return
      setFollowupsState({ status: 'error', items: [], total: 0, message: getErrorMessage(error, '加载跟进记录失败') })
    }
  }

  const closeFollowupModal = () => {
    setFollowupCustomerId(null)
    setFollowupsState({ status: 'loading', items: [], total: 0, message: null })
  }

  const openFollowupCreateModal = () => {
    followupForm.resetFields()
    // 默认联系时间为当前时间
    followupForm.setFieldsValue({ contact_time: dayjs(), method: '电话' })
    setIsFollowupCreateOpen(true)
  }

  const closeFollowupCreateModal = () => {
    setIsFollowupCreateOpen(false)
    setCreateFollowupCustomerId(null)
    followupForm.resetFields()
  }

  const handleFollowupCreate = async (values: { contact_time: dayjs.Dayjs; method: string; intention?: string; notes?: string; next_followup_time?: dayjs.Dayjs | null }) => {
    if (!accessToken || !createFollowupCustomerId) return

    setIsFollowupCreateSubmitting(true)
    try {
      await createFollowup(accessToken, {
        customer_id: createFollowupCustomerId,
        contact_time: values.contact_time.toISOString(),
        method: values.method,
        intention: values.intention || null,
        notes: values.notes || null,
        next_followup_time: values.next_followup_time ? values.next_followup_time.toISOString() : null,
      })
      messageApi.success('跟进记录创建成功')
      closeFollowupCreateModal()
      // 如果跟进记录列表弹窗已打开，刷新列表
      if (followupCustomerId) {
        await loadFollowups(followupCustomerId, followupPage)
      }
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '创建跟进记录失败'))
    } finally {
      setIsFollowupCreateSubmitting(false)
    }
  }

  const handleFollowupDelete = async (followupId: number) => {
    if (!accessToken || !followupCustomerId) return

    try {
      await deleteFollowup(accessToken, followupId)
      messageApi.success('跟进记录已删除')
      await loadFollowups(followupCustomerId, followupPage)
    } catch (error) {
      if (await handleUnauthorized(error)) return
      messageApi.error(getErrorMessage(error, '删除跟进记录失败'))
    }
  }

  // ==================== 搜索和分页 ====================

  const handleSearch = (value: string) => {
    setKeyword(value)
    setCurrentPage(DEFAULT_PAGE)
  }

  const handlePageChange = (page: number, size: number) => {
    setCurrentPage(page)
    setPageSize(size)
  }

  // ==================== 表格列定义 ====================

  const columns: TableColumnsType<CustomerDetail> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '联系电话',
      dataIndex: 'phone',
      key: 'phone',
      width: 130,
      render: (value: string | null) => value || '-',
    },
    {
      title: '意向度',
      dataIndex: 'intention',
      key: 'intention',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '认领时间',
      dataIndex: 'assigned_at',
      key: 'assigned_at',
      width: 170,
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '最新跟进',
      dataIndex: 'followup_at',
      key: 'followup_at',
      width: 170,
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_, customer) => (
        <Space wrap>
          {canFollowupCreate ? (
            <Button size="small" type="primary" onClick={() => {
              setCreateFollowupCustomerId(customer.id)
              openFollowupCreateModal()
            }}>
              跟进
            </Button>
          ) : null}
          {canFollowupView ? (
            <Button size="small" onClick={() => void openFollowupModal(customer.id)}>
              跟进记录
            </Button>
          ) : null}
          {canRelease ? (
            <Button
              size="small"
              loading={releasingCustomerId === customer.id}
              onClick={() => void handleRelease(customer.id)}
            >
              释放
            </Button>
          ) : null}
        </Space>
      ),
    },
  ]

  // ==================== 渲染 ====================

  return (
    <>
      <Space direction="vertical" size="large" style={{ display: 'flex' }}>
        {/* 标题卡片 */}
        <Card
          title={<Typography.Title level={2} style={{ margin: 0 }}>长期客户</Typography.Title>}
          extra={
            <Button onClick={() => void loadCustomers()} loading={customersState.status === 'loading'}>
              刷新
            </Button>
          }
        >
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            当前用户占有的长期客户列表，支持跟进记录和释放操作。
          </Typography.Paragraph>
        </Card>

        {/* 错误提示 */}
        {customersState.status === 'error' && customersState.message ? (
          <Typography.Text type="danger">{customersState.message}</Typography.Text>
        ) : null}

        {/* 搜索栏 */}
        <Card size="small">
          <Space wrap>
            <Input.Search
              placeholder="搜索姓名/电话"
              allowClear
              onSearch={handleSearch}
              style={{ width: 240 }}
            />
          </Space>
        </Card>

        {/* 批量操作栏 */}
        {selectedRowKeys.length > 0 ? (
          <Card size="small">
            <Space>
              <Typography.Text>已选择 {selectedRowKeys.length} 项</Typography.Text>
              {canRelease ? (
                <Button
                  loading={isBatchReleaseSubmitting}
                  onClick={() => void handleBatchRelease()}
                >
                  批量释放（{selectedRowKeys.length} 条）
                </Button>
              ) : null}
              <Button onClick={() => { setSelectedRowKeys([]) }}>
                取消选择
              </Button>
            </Space>
          </Card>
        ) : null}

        {/* 数据表格 */}
        <Card>
          <Table<CustomerDetail>
            rowKey="id"
            columns={columns}
            dataSource={customersState.items}
            loading={customersState.status === 'loading'}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => {
                setSelectedRowKeys(keys as number[])
              },
            }}
            pagination={{
              current: currentPage,
              pageSize,
              total: customersState.total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: handlePageChange,
            }}
          />
        </Card>
      </Space>

      {/* 跟进记录弹窗 */}
      <Modal
        title={`跟进记录（客户 #${followupCustomerId}）`}
        open={followupCustomerId !== null && !isFollowupCreateOpen}
        onCancel={closeFollowupModal}
        footer={null}
        width={800}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {canFollowupCreate ? (
            <Button type="primary" onClick={openFollowupCreateModal}>
              新建跟进
            </Button>
          ) : null}

          {followupsState.status === 'error' && followupsState.message ? (
            <Typography.Text type="danger">{followupsState.message}</Typography.Text>
          ) : null}

          <Table<FollowupRecord>
            rowKey="id"
            size="small"
            loading={followupsState.status === 'loading'}
            dataSource={followupsState.items}
            pagination={{
              current: followupPage,
              pageSize: followupPageSize,
              total: followupsState.total,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page) => {
                setFollowupPage(page)
                if (followupCustomerId) void loadFollowups(followupCustomerId, page)
              },
            }}
            columns={[
              { title: '联系时间', dataIndex: 'contact_time', width: 160, render: (v: string) => formatDateTime(v) },
              { title: '方式', dataIndex: 'method', width: 80 },
              { title: '意向', dataIndex: 'intention', width: 80, render: (v: string | null) => v || '-' },
              { title: '说明', dataIndex: 'notes', ellipsis: true, render: (v: string | null) => v || '-' },
              { title: '下次跟进', dataIndex: 'next_followup_time', width: 160, render: (v: string | null) => formatDateTime(v) },
              { title: '创建人', dataIndex: 'username', width: 100, render: (v: string | null) => v || '-' },
              {
                title: '操作',
                key: 'actions',
                width: 70,
                render: (_, record) => canFollowupDelete ? (
                  <Button size="small" danger onClick={() => void handleFollowupDelete(record.id)}>
                    删除
                  </Button>
                ) : null,
              },
            ]}
          />
        </Space>
      </Modal>

      {/* 创建跟进弹窗 */}
      <Modal
        title="新建跟进记录"
        open={isFollowupCreateOpen}
        onCancel={closeFollowupCreateModal}
        onOk={() => void followupForm.submit()}
        okText="创建"
        confirmLoading={isFollowupCreateSubmitting}
        width={560}
      >
        <Form form={followupForm} layout="vertical" onFinish={(values) => void handleFollowupCreate(values)}>
          <Form.Item label="联系时间" name="contact_time" rules={[{ required: true, message: '请填写联系时间' }]}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="跟进方式" name="method" rules={[{ required: true, message: '请选择跟进方式' }]}>
            <Select options={FOLLOWUP_METHOD_OPTIONS} />
          </Form.Item>
          <Form.Item label="意向度" name="intention">
            <Select placeholder="意向度" allowClear options={FOLLOWUP_INTENTION_OPTIONS} />
          </Form.Item>
          <Form.Item label="跟进说明" name="notes">
            <Input.TextArea rows={3} placeholder="跟进说明" />
          </Form.Item>
          <Form.Item label="下次跟进时间" name="next_followup_time">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
