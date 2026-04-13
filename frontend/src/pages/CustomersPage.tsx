/**
 * 客户管理页面
 *
 * 提供客户数据的 CRUD 操作界面，支持：
 * - 列表查询（后端分页、关键词搜索、状态/阶段筛选）
 * - 详情弹窗（查看全部字段）
 * - 创建/编辑（Modal 表单，按业务分组展示字段）
 * - 软删除（确认弹窗，删除后从列表消失）
 * - 权限控制（创建/编辑/删除按钮根据权限显隐）
 */

import {
  App as AntApp,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
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
  createCustomer,
  deleteCustomer,
  getCustomerDetail,
  listCustomers,
  updateCustomer,
  type CustomerDetail,
  type CustomerInput,
} from '../lib/api-client'
import { useCan } from '../lib/permissions'

// ==================== 状态类型 ====================

type CustomersState = {
  status: 'loading' | 'success' | 'error'
  items: CustomerDetail[]
  total: number
  message: string | null
}

type DetailState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  data: CustomerDetail | null
  message: string | null
}

// ==================== 常量 ====================

/** 反馈状态选项 */
const FEEDBACK_STATUS_OPTIONS = [
  { label: '有效', value: '有效' },
  { label: '无效', value: '无效' },
]

/** 客户阶段选项 */
const CUSTOMER_STAGE_OPTIONS = [
  { label: '回访', value: '回访' },
  { label: '报名', value: '报名' },
]

/** 意向度选项 */
const INTENTION_OPTIONS = [
  { label: '没有咨询', value: '没有咨询' },
  { label: '不需要', value: '不需要' },
  { label: '无人接听', value: '无人接听' },
  { label: '有意向', value: '有意向' },
  { label: '待跟进', value: '待跟进' },
]

/** 微信状态选项 */
const WECHAT_STATUS_OPTIONS = [
  { label: '未添加', value: '未添加' },
  { label: '已加上微信', value: '已加上微信' },
]

/** 分配方式选项 */
const ASSIGN_METHOD_OPTIONS = [
  { label: '手动', value: '手动' },
  { label: '自动', value: '自动' },
]

/** 分配类型选项 */
const ASSIGN_TYPE_OPTIONS = [
  { label: '公海领取', value: '公海领取' },
  { label: '主管调配', value: '主管调配' },
]

/** 默认分页参数 */
const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

// ==================== 工具函数 ====================

function getErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof Error) {
    return error.message
  }
  return fallbackMessage
}

/** 格式化日期时间字符串，用于展示 */
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

export function CustomersPage() {
  const { message } = AntApp.useApp()
  const { accessToken, logout } = useAuth()
  const can = useCan()
  const canView = can('CUSTOMER_VIEW')
  const canCreate = can('CUSTOMER_CREATE')
  const canEdit = can('CUSTOMER_EDIT')
  const canDelete = can('CUSTOMER_DELETE')

  // 列表状态
  const [customersState, setCustomersState] = useState<CustomersState>({
    status: 'loading',
    items: [],
    total: 0,
    message: null,
  })

  // 筛选参数
  const [keyword, setKeyword] = useState<string>('')
  const [filterFeedbackStatus, setFilterFeedbackStatus] = useState<string | undefined>(undefined)
  const [filterCustomerStage, setFilterCustomerStage] = useState<string | undefined>(undefined)
  const [currentPage, setCurrentPage] = useState(DEFAULT_PAGE)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  // 详情弹窗状态
  const [detailState, setDetailState] = useState<DetailState>({
    status: 'idle',
    data: null,
    message: null,
  })
  const [detailCustomerId, setDetailCustomerId] = useState<number | null>(null)

  // 创建/编辑弹窗状态
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<CustomerDetail | null>(null)
  const [isCreateSubmitting, setIsCreateSubmitting] = useState(false)
  const [isEditSubmitting, setIsEditSubmitting] = useState(false)

  // 删除确认弹窗状态
  const [deletingCustomer, setDeletingCustomer] = useState<CustomerDetail | null>(null)
  const [isDeleteSubmitting, setIsDeleteSubmitting] = useState(false)

  // 表单实例
  const [createForm] = Form.useForm<CustomerInput>()
  const [editForm] = Form.useForm<CustomerInput>()

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
    if (!accessToken) return

    setCustomersState((prev) => ({
      status: 'loading',
      items: prev.items,
      total: prev.total,
      message: null,
    }))

    try {
      const result = await listCustomers(accessToken, {
        keyword: keyword || undefined,
        feedback_status: filterFeedbackStatus,
        customer_stage: filterCustomerStage,
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
        message: getErrorMessage(error, '加载客户列表失败'),
      }))
    }
  }, [accessToken, keyword, filterFeedbackStatus, filterCustomerStage, currentPage, pageSize, handleUnauthorized])

  useEffect(() => {
    void loadCustomers()
  }, [loadCustomers])

  // ==================== 详情弹窗 ====================

  const openDetailModal = async (customerId: number) => {
    if (!accessToken) return

    setDetailCustomerId(customerId)
    setDetailState({ status: 'loading', data: null, message: null })

    try {
      const detail = await getCustomerDetail(accessToken, customerId)
      setDetailState({ status: 'success', data: detail, message: null })
    } catch (error) {
      if (await handleUnauthorized(error)) {
        setDetailCustomerId(null)
        return
      }
      setDetailState({
        status: 'error',
        data: null,
        message: getErrorMessage(error, '加载客户详情失败'),
      })
    }
  }

  const closeDetailModal = () => {
    setDetailCustomerId(null)
    setDetailState({ status: 'idle', data: null, message: null })
  }

  // ==================== 创建/编辑弹窗 ====================

  const openCreateModal = () => {
    createForm.resetFields()
    setIsCreateModalOpen(true)
  }

  const closeCreateModal = () => {
    setIsCreateModalOpen(false)
    createForm.resetFields()
  }

  const openEditModal = async (customer: CustomerDetail) => {
    if (!accessToken) return

    // 编辑时直接用列表项的数据填充表单
    editForm.setFieldsValue({
      ...customer,
      assigned_at: customer.assigned_at?.slice(0, 19) || undefined,
      first_assign_time: customer.first_assign_time?.slice(0, 19) || undefined,
      last_first_consult_time: customer.last_first_consult_time?.slice(0, 19) || undefined,
    })
    setEditingCustomer(customer)
  }

  const closeEditModal = () => {
    setEditingCustomer(null)
    editForm.resetFields()
  }

  const handleCreate = async (values: CustomerInput) => {
    if (!accessToken) return

    setIsCreateSubmitting(true)
    try {
      await createCustomer(accessToken, values)
      closeCreateModal()
      message.success('客户创建成功')
      await loadCustomers()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      message.error(getErrorMessage(error, '创建客户失败'))
    } finally {
      setIsCreateSubmitting(false)
    }
  }

  const handleEdit = async (values: CustomerInput) => {
    if (!accessToken || !editingCustomer) return

    setIsEditSubmitting(true)
    try {
      await updateCustomer(accessToken, editingCustomer.id, values)
      closeEditModal()
      message.success('客户更新成功')
      await loadCustomers()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      message.error(getErrorMessage(error, '编辑客户失败'))
    } finally {
      setIsEditSubmitting(false)
    }
  }

  // ==================== 删除确认 ====================

  const openDeleteModal = (customer: CustomerDetail) => {
    setDeletingCustomer(customer)
  }

  const closeDeleteModal = () => {
    setDeletingCustomer(null)
  }

  const handleDelete = async () => {
    if (!accessToken || !deletingCustomer) return

    setIsDeleteSubmitting(true)
    try {
      await deleteCustomer(accessToken, deletingCustomer.id)
      closeDeleteModal()
      message.success('客户已删除')
      await loadCustomers()
    } catch (error) {
      if (await handleUnauthorized(error)) return
      message.error(getErrorMessage(error, '删除客户失败'))
    } finally {
      setIsDeleteSubmitting(false)
    }
  }

  // ==================== 搜索和筛选 ====================

  const handleSearch = (value: string) => {
    setKeyword(value)
    setCurrentPage(DEFAULT_PAGE)
  }

  const handleFilterChange = (
    type: 'feedback_status' | 'customer_stage',
    value: string | undefined,
  ) => {
    if (type === 'feedback_status') {
      setFilterFeedbackStatus(value)
    } else {
      setFilterCustomerStage(value)
    }
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
      title: '反馈状态',
      dataIndex: 'feedback_status',
      key: 'feedback_status',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '客户阶段',
      dataIndex: 'customer_stage',
      key: 'customer_stage',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '归属人',
      dataIndex: 'owner',
      key: 'owner',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '来源',
      dataIndex: 'source_name',
      key: 'source_name',
      width: 100,
      render: (value: string | null) => value || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (value: string | null) => formatDateTime(value),
    },
  ]

  // 操作列
  if (canView || canEdit || canDelete) {
    columns.push({
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_, customer) => (
        <Space wrap>
          {canView ? (
            <Button size="small" onClick={() => void openDetailModal(customer.id)}>
              详情
            </Button>
          ) : null}
          {canEdit ? (
            <Button size="small" onClick={() => void openEditModal(customer)}>
              编辑
            </Button>
          ) : null}
          {canDelete ? (
            <Button size="small" danger onClick={() => openDeleteModal(customer)}>
              删除
            </Button>
          ) : null}
        </Space>
      ),
    })
  }

  // ==================== 客户表单（创建/编辑共用） ====================

  const renderCustomerForm = (formInstance: typeof createForm, onFinish: (values: CustomerInput) => void) => (
    <Form form={formInstance} layout="vertical" onFinish={(values) => void onFinish(values)}>
      <Typography.Title level={5}>基本信息</Typography.Title>
      <Space direction="vertical" size="small" style={{ display: 'flex' }}>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="姓名" name="name" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="姓名" />
          </Form.Item>
          <Form.Item label="联系电话" name="phone" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="联系电话" />
          </Form.Item>
          <Form.Item label="微信" name="wechat" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="微信" />
          </Form.Item>
          <Form.Item label="微信状态" name="wechat_status" style={{ marginBottom: 0, width: 160 }}>
            <Select placeholder="微信状态" allowClear options={WECHAT_STATUS_OPTIONS} />
          </Form.Item>
        </Space>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="QQ" name="qq" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="QQ" />
          </Form.Item>
          <Form.Item label="省份" name="province" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="省份" />
          </Form.Item>
          <Form.Item label="地域" name="region" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="地域" />
          </Form.Item>
          <Form.Item label="年级" name="grade" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="年级" />
          </Form.Item>
        </Space>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="意向度" name="intention" style={{ marginBottom: 0, width: 160 }}>
            <Select placeholder="意向度" allowClear options={INTENTION_OPTIONS} />
          </Form.Item>
          <Form.Item label="反馈状态" name="feedback_status" style={{ marginBottom: 0, width: 160 }}>
            <Select placeholder="反馈状态" allowClear options={FEEDBACK_STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="客户阶段" name="customer_stage" style={{ marginBottom: 0, width: 160 }}>
            <Select placeholder="客户阶段" allowClear options={CUSTOMER_STAGE_OPTIONS} />
          </Form.Item>
          <Form.Item label="标签" name="tag" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="标签" />
          </Form.Item>
        </Space>
        <Form.Item label="备注" name="remark" style={{ marginBottom: 0 }}>
          <Input.TextArea rows={2} placeholder="备注" />
        </Form.Item>
      </Space>

      <Typography.Title level={5} style={{ marginTop: 16 }}>来源与归属</Typography.Title>
      <Space direction="vertical" size="small" style={{ display: 'flex' }}>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="来源名称" name="source_name" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="来源名称" />
          </Form.Item>
          <Form.Item label="归属人" name="owner" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="归属人" />
          </Form.Item>
          <Form.Item label="一级项目" name="primary_project" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="一级项目" />
          </Form.Item>
          <Form.Item label="项目" name="project" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="项目" />
          </Form.Item>
        </Space>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="事业部" name="business_dept" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="事业部" />
          </Form.Item>
          <Form.Item label="呼叫部" name="call_dept" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="呼叫部" />
          </Form.Item>
          <Form.Item label="呼叫组" name="call_group" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="呼叫组" />
          </Form.Item>
          <Form.Item label="广告商" name="advertiser" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="广告商" />
          </Form.Item>
        </Space>
        <Form.Item label="着陆页" name="landing_page" style={{ marginBottom: 0 }}>
          <Input placeholder="着陆页" />
        </Form.Item>
      </Space>

      <Typography.Title level={5} style={{ marginTop: 16 }}>分配信息</Typography.Title>
      <Space wrap style={{ display: 'flex' }}>
        <Form.Item label="分配方式" name="assign_method" style={{ marginBottom: 0, width: 160 }}>
          <Select placeholder="分配方式" allowClear options={ASSIGN_METHOD_OPTIONS} />
        </Form.Item>
        <Form.Item label="分配类型" name="assign_type" style={{ marginBottom: 0, width: 160 }}>
          <Select placeholder="分配类型" allowClear options={ASSIGN_TYPE_OPTIONS} />
        </Form.Item>
        <Form.Item label="分配时间" name="assigned_at" style={{ marginBottom: 0, width: 200 }}>
          <Input placeholder="YYYY-MM-DD HH:MM:SS" />
        </Form.Item>
      </Space>

      <Typography.Title level={5} style={{ marginTop: 16 }}>咨询信息</Typography.Title>
      <Space direction="vertical" size="small" style={{ display: 'flex' }}>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="首次咨询师" name="first_consultant" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="首次咨询师" />
          </Form.Item>
          <Form.Item label="最后咨询师" name="last_consultant" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="最后咨询师" />
          </Form.Item>
          <Form.Item label="首次分配归属机构" name="first_assign_org" style={{ marginBottom: 0, width: 180 }}>
            <Input placeholder="首次分配归属机构" />
          </Form.Item>
        </Space>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="首次分配归属人" name="first_assign_person" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="首次分配归属人" />
          </Form.Item>
          <Form.Item label="首次分配时间" name="first_assign_time" style={{ marginBottom: 0, width: 200 }}>
            <Input placeholder="YYYY-MM-DD HH:MM:SS" />
          </Form.Item>
          <Form.Item label="最后首咨分配归属人" name="last_first_consult_person" style={{ marginBottom: 0, width: 200 }}>
            <Input placeholder="最后首咨分配归属人" />
          </Form.Item>
        </Space>
      </Space>

      <Typography.Title level={5} style={{ marginTop: 16 }}>其他信息</Typography.Title>
      <Space direction="vertical" size="small" style={{ display: 'flex' }}>
        <Space wrap style={{ display: 'flex' }}>
          <Form.Item label="创建人" name="creator" style={{ marginBottom: 0, width: 160 }}>
            <Input placeholder="创建人" />
          </Form.Item>
          <Form.Item label="创建人归属机构" name="creator_org" style={{ marginBottom: 0, width: 180 }}>
            <Input placeholder="创建人归属机构" />
          </Form.Item>
          <Form.Item label="原系统客户ID" name="original_id" style={{ marginBottom: 0, width: 180 }}>
            <Input placeholder="原系统客户ID" />
          </Form.Item>
        </Space>
      </Space>
    </Form>
  )

  // ==================== 渲染 ====================

  return (
    <>
      <Space direction="vertical" size="large" style={{ display: 'flex' }}>
        {/* 标题卡片 */}
        <Card
          title={<Typography.Title level={2} style={{ margin: 0 }}>客户管理</Typography.Title>}
          extra={
            <Space>
              <Button onClick={() => void loadCustomers()} loading={customersState.status === 'loading'}>
                刷新
              </Button>
              {canCreate ? (
                <Button type="primary" onClick={openCreateModal}>
                  新建客户
                </Button>
              ) : null}
            </Space>
          }
        >
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            管理客户基本信息、意向状态、来源归属等数据。
          </Typography.Paragraph>
        </Card>

        {/* 错误提示 */}
        {customersState.status === 'error' && customersState.message ? (
          <Typography.Text type="danger">{customersState.message}</Typography.Text>
        ) : null}

        {/* 搜索和筛选栏 */}
        <Card size="small">
          <Space wrap>
            <Input.Search
              placeholder="搜索姓名/电话"
              allowClear
              onSearch={handleSearch}
              style={{ width: 240 }}
            />
            <Select
              placeholder="反馈状态"
              allowClear
              options={FEEDBACK_STATUS_OPTIONS}
              onChange={(value) => handleFilterChange('feedback_status', value)}
              style={{ width: 140 }}
            />
            <Select
              placeholder="客户阶段"
              allowClear
              options={CUSTOMER_STAGE_OPTIONS}
              onChange={(value) => handleFilterChange('customer_stage', value)}
              style={{ width: 140 }}
            />
          </Space>
        </Card>

        {/* 数据表格 */}
        <Card>
          <Table<CustomerDetail>
            rowKey="id"
            columns={columns}
            dataSource={customersState.items}
            loading={customersState.status === 'loading'}
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

      {/* 详情弹窗 */}
      <Modal
        title={detailState.data ? `客户详情：${detailState.data.name || detailState.data.id}` : '客户详情'}
        open={detailCustomerId !== null}
        onCancel={closeDetailModal}
        footer={null}
        width={720}
      >
        {detailState.status === 'loading' ? (
          <Typography.Text>加载中...</Typography.Text>
        ) : detailState.status === 'error' ? (
          <Typography.Text type="danger">{detailState.message}</Typography.Text>
        ) : detailState.data ? (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="ID">{detailState.data.id}</Descriptions.Item>
            <Descriptions.Item label="姓名">{detailState.data.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="联系电话">{detailState.data.phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="微信">{detailState.data.wechat || '-'}</Descriptions.Item>
            <Descriptions.Item label="微信状态">{detailState.data.wechat_status || '-'}</Descriptions.Item>
            <Descriptions.Item label="QQ">{detailState.data.qq || '-'}</Descriptions.Item>
            <Descriptions.Item label="省份">{detailState.data.province || '-'}</Descriptions.Item>
            <Descriptions.Item label="地域">{detailState.data.region || '-'}</Descriptions.Item>
            <Descriptions.Item label="年级">{detailState.data.grade || '-'}</Descriptions.Item>
            <Descriptions.Item label="意向度">{detailState.data.intention || '-'}</Descriptions.Item>
            <Descriptions.Item label="反馈状态">{detailState.data.feedback_status || '-'}</Descriptions.Item>
            <Descriptions.Item label="客户阶段">{detailState.data.customer_stage || '-'}</Descriptions.Item>
            <Descriptions.Item label="标签" span={2}>{detailState.data.tag || '-'}</Descriptions.Item>
            <Descriptions.Item label="备注" span={2}>{detailState.data.remark || '-'}</Descriptions.Item>
            <Descriptions.Item label="来源名称">{detailState.data.source_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="归属人">{detailState.data.owner || '-'}</Descriptions.Item>
            <Descriptions.Item label="一级项目">{detailState.data.primary_project || '-'}</Descriptions.Item>
            <Descriptions.Item label="项目">{detailState.data.project || '-'}</Descriptions.Item>
            <Descriptions.Item label="事业部">{detailState.data.business_dept || '-'}</Descriptions.Item>
            <Descriptions.Item label="呼叫部">{detailState.data.call_dept || '-'}</Descriptions.Item>
            <Descriptions.Item label="呼叫组">{detailState.data.call_group || '-'}</Descriptions.Item>
            <Descriptions.Item label="广告商">{detailState.data.advertiser || '-'}</Descriptions.Item>
            <Descriptions.Item label="着陆页" span={2}>{detailState.data.landing_page || '-'}</Descriptions.Item>
            <Descriptions.Item label="分配方式">{detailState.data.assign_method || '-'}</Descriptions.Item>
            <Descriptions.Item label="分配类型">{detailState.data.assign_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="分配时间">{formatDateTime(detailState.data.assigned_at)}</Descriptions.Item>
            <Descriptions.Item label="创建人">{detailState.data.creator || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建人归属机构">{detailState.data.creator_org || '-'}</Descriptions.Item>
            <Descriptions.Item label="首次咨询师">{detailState.data.first_consultant || '-'}</Descriptions.Item>
            <Descriptions.Item label="最后咨询师">{detailState.data.last_consultant || '-'}</Descriptions.Item>
            <Descriptions.Item label="首次分配归属机构">{detailState.data.first_assign_org || '-'}</Descriptions.Item>
            <Descriptions.Item label="首次分配归属人">{detailState.data.first_assign_person || '-'}</Descriptions.Item>
            <Descriptions.Item label="首次分配时间">{formatDateTime(detailState.data.first_assign_time)}</Descriptions.Item>
            <Descriptions.Item label="最后首咨分配时间">{formatDateTime(detailState.data.last_first_consult_time)}</Descriptions.Item>
            <Descriptions.Item label="最后首咨分配归属人">{detailState.data.last_first_consult_person || '-'}</Descriptions.Item>
            <Descriptions.Item label="报名次数">{detailState.data.registration_count}</Descriptions.Item>
            <Descriptions.Item label="当日外呼次数">{detailState.data.daily_outbound_count}</Descriptions.Item>
            <Descriptions.Item label="当日呼通次数">{detailState.data.daily_connected_count}</Descriptions.Item>
            <Descriptions.Item label="当日接通时长(秒)">{detailState.data.daily_connected_duration}</Descriptions.Item>
            <Descriptions.Item label="IP">{detailState.data.ip || '-'}</Descriptions.Item>
            <Descriptions.Item label="IP省份">{detailState.data.ip_province || '-'}</Descriptions.Item>
            <Descriptions.Item label="IP城市">{detailState.data.ip_city || '-'}</Descriptions.Item>
            <Descriptions.Item label="原系统客户ID" span={2}>{detailState.data.original_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDateTime(detailState.data.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatDateTime(detailState.data.updated_at)}</Descriptions.Item>
          </Descriptions>
        ) : null}
      </Modal>

      {/* 创建弹窗 */}
      <Modal
        title="新建客户"
        open={isCreateModalOpen}
        onCancel={closeCreateModal}
        onOk={() => void createForm.submit()}
        okText="创建"
        confirmLoading={isCreateSubmitting}
        width={720}
      >
        {renderCustomerForm(createForm, handleCreate)}
      </Modal>

      {/* 编辑弹窗 */}
      <Modal
        title={editingCustomer ? `编辑客户：${editingCustomer.name || editingCustomer.id}` : '编辑客户'}
        open={editingCustomer !== null}
        onCancel={closeEditModal}
        onOk={() => void editForm.submit()}
        okText="保存"
        confirmLoading={isEditSubmitting}
        width={720}
      >
        {renderCustomerForm(editForm, handleEdit)}
      </Modal>

      {/* 删除确认弹窗 */}
      <Modal
        title="删除客户"
        open={deletingCustomer !== null}
        onCancel={closeDeleteModal}
        onOk={() => void handleDelete()}
        okText="确认删除"
        okButtonProps={{ danger: true }}
        confirmLoading={isDeleteSubmitting}
      >
        <Typography.Paragraph>
          确认删除客户 <Typography.Text strong>{deletingCustomer?.name || deletingCustomer?.id}</Typography.Text> 吗？
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary">
          此操作为软删除，删除后客户数据仍可在数据库中恢复。
        </Typography.Paragraph>
      </Modal>
    </>
  )
}
