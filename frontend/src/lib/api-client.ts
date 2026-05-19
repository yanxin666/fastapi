import { getApiBaseUrl } from '../config/api'

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(status: number, message: string, payload: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export type HealthResponse = {
  status: string
}

export type AdminUser = {
  id: number
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
  roles: string[]
  permissions: string[]
}

export type LoginResponse = {
  accessToken: string
  refreshToken: string
  tokenType: string
  user: AdminUser
}

export type RefreshTokenResponse = {
  accessToken: string
  refreshToken: string
  tokenType: string
}

export type UserListItem = {
  id: number
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
}

export type UserDetail = UserListItem & {
  roles: string[]
}

export type CreateUserInput = {
  username: string
  email: string
  password: string
}

export type UpdateUserInput = {
  username: string
  email: string
}

export type RoleListItem = {
  id: number
  name: string
  description: string | null
}

export type RoleDetail = RoleListItem & {
  permissions: string[]
}

export type CreateRoleInput = {
  name: string
  description: string | null
}

export type UpdateRoleInput = {
  name: string
  description: string | null
}

export type PermissionListItem = {
  id: number
  code: string
  description: string | null
}

type ListResponse<T> = {
  items: T[]
}

type PaginatedResponse<T> = {
  items: T[]
  total: number
}

type RequestOptions = {
  accessToken?: string
  body?: unknown
  errorMessage: string
  method?: 'POST'
}

type LoginResponseDto = {
  access_token: string
  refresh_token: string
  token_type: string
  user: AdminUser
}

type RefreshTokenResponseDto = {
  access_token: string
  refresh_token: string
  token_type: string
}

function getErrorMessage(payload: unknown, fallbackMessage: string): string {
  if (payload && typeof payload === 'object') {
    if ('message' in payload && typeof payload.message === 'string') {
      return payload.message
    }

    if ('detail' in payload && typeof payload.detail === 'string') {
      return payload.detail
    }
  }

  return fallbackMessage
}

async function readResponsePayload(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null
  }

  try {
    return await response.json()
  } catch {
    return null
  }
}

async function requestJson<T>(path: string, options: RequestOptions): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (options.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`
  }

  const requestInit: RequestInit = { headers }

  if (options.method) {
    requestInit.method = options.method
  }

  if (options.body !== undefined) {
    requestInit.method = requestInit.method ?? 'POST'
    requestInit.body = JSON.stringify(options.body)
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, requestInit)
  const payload = await readResponsePayload(response)

  if (!response.ok) {
    throw new ApiError(response.status, getErrorMessage(payload, options.errorMessage), payload)
  }

  return payload as T
}

export async function getAdminHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health', {
    errorMessage: 'Failed to fetch admin health status',
  })
}

export async function loginAdmin(credentials: {
  username: string
  password: string
}): Promise<LoginResponse> {
  const payload = await requestJson<LoginResponseDto>('/auth/login', {
    method: 'POST',
    body: credentials,
    errorMessage: 'Failed to log in',
  })

  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    tokenType: payload.token_type,
    user: payload.user,
  }
}

export async function refreshAdminToken(refreshToken: string): Promise<RefreshTokenResponse> {
  const payload = await requestJson<RefreshTokenResponseDto>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    errorMessage: 'Failed to refresh session',
  })

  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    tokenType: payload.token_type,
  }
}

export async function logoutAdmin(refreshToken: string): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>('/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    errorMessage: 'Failed to log out',
  })
}

export async function getCurrentAdminUser(accessToken: string): Promise<AdminUser> {
  return requestJson<AdminUser>('/auth/me', {
    accessToken,
    errorMessage: 'Failed to fetch current admin user',
  })
}

export async function listUsers(accessToken: string): Promise<ListResponse<UserListItem>> {
  return requestJson<ListResponse<UserListItem>>('/users', {
    accessToken,
    errorMessage: 'Failed to load users',
  })
}

export async function getUserDetail(accessToken: string, userId: number): Promise<UserDetail> {
  return requestJson<UserDetail>(`/users/${userId}`, {
    accessToken,
    errorMessage: 'Failed to load user details',
  })
}

export async function createUser(accessToken: string, input: CreateUserInput): Promise<UserListItem> {
  return requestJson<UserListItem>('/users', {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: 'Failed to create user',
  })
}

export async function updateUser(
  accessToken: string,
  userId: number,
  input: UpdateUserInput,
): Promise<UserListItem> {
  return requestJson<UserListItem>(`/users/${userId}/update`, {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: 'Failed to update user',
  })
}

export async function assignUserRoles(
  accessToken: string,
  userId: number,
  roleIds: number[],
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/users/${userId}/roles`, {
    accessToken,
    method: 'POST',
    body: { role_ids: roleIds },
    errorMessage: 'Failed to assign roles',
  })
}

export async function toggleUserActive(accessToken: string, userId: number): Promise<UserListItem> {
  return requestJson<UserListItem>(`/users/${userId}/toggle-active`, {
    accessToken,
    method: 'POST',
    errorMessage: 'Failed to update user status',
  })
}

export async function resetUserPassword(
  accessToken: string,
  userId: number,
  password: string,
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/users/${userId}/reset-password`, {
    accessToken,
    method: 'POST',
    body: { password },
    errorMessage: 'Failed to reset password',
  })
}

export async function listRoles(accessToken: string): Promise<ListResponse<RoleListItem>> {
  return requestJson<ListResponse<RoleListItem>>('/roles', {
    accessToken,
    errorMessage: 'Failed to load roles',
  })
}

export async function getRoleDetail(accessToken: string, roleId: number): Promise<RoleDetail> {
  return requestJson<RoleDetail>(`/roles/${roleId}`, {
    accessToken,
    errorMessage: 'Failed to load role details',
  })
}

export async function createRole(accessToken: string, input: CreateRoleInput): Promise<RoleListItem> {
  return requestJson<RoleListItem>('/roles', {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: 'Failed to create role',
  })
}

export async function updateRole(
  accessToken: string,
  roleId: number,
  input: UpdateRoleInput,
): Promise<RoleListItem> {
  return requestJson<RoleListItem>(`/roles/${roleId}/update`, {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: 'Failed to update role',
  })
}

export async function assignRolePermissions(
  accessToken: string,
  roleId: number,
  permissionIds: number[],
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/roles/${roleId}/permissions`, {
    accessToken,
    method: 'POST',
    body: { permission_ids: permissionIds },
    errorMessage: 'Failed to assign permissions',
  })
}

export async function deleteRole(accessToken: string, roleId: number): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/roles/${roleId}/delete`, {
    accessToken,
    method: 'POST',
    errorMessage: 'Failed to delete role',
  })
}

export async function listPermissions(accessToken: string): Promise<ListResponse<PermissionListItem>> {
  return requestJson<ListResponse<PermissionListItem>>('/permissions', {
    accessToken,
    errorMessage: 'Failed to load permissions',
  })
}

// ==================== 客户管理 ====================

export type CustomerListItem = {
  id: number
  name: string | null
  phone: string | null
  wechat: string | null
  intention: string | null
  feedback_status: string | null
  customer_stage: string | null
  owner: string | null
  source_name: string | null
  created_at: string | null
}

export type CustomerDetail = {
  id: number
  // 认领信息
  user_id: number | null
  claim_status: 'claimed' | 'unclaimed' | 'possession'
  claim_user_name: string | null
  followup_at: string | null
  // 基本信息
  name: string | null
  phone: string | null
  wechat: string | null
  wechat_status: string | null
  qq: string | null
  province: string | null
  region: string | null
  grade: string | null
  remark: string | null
  tag: string | null
  // 意向与状态
  intention: string | null
  feedback_status: string | null
  customer_stage: string | null
  // 来源与归属
  source_name: string | null
  owner: string | null
  primary_project: string | null
  project: string | null
  business_dept: string | null
  call_dept: string | null
  call_group: string | null
  advertiser: string | null
  landing_page: string | null
  // 分配信息
  assign_method: string | null
  assign_type: string | null
  assigned_at: string | null
  creator: string | null
  creator_org: string | null
  // 咨询信息
  first_consultant: string | null
  last_consultant: string | null
  first_assign_org: string | null
  first_assign_person: string | null
  first_assign_time: string | null
  last_first_consult_time: string | null
  last_first_consult_person: string | null
  // 统计追踪
  registration_count: number
  daily_outbound_count: number
  daily_connected_count: number
  daily_connected_duration: number
  ip: string | null
  ip_province: string | null
  ip_city: string | null
  // 聊天记录
  raw_chat_records: string | null
  chat_records: string | null
  // 系统字段
  original_id: string | null
  is_deleted: boolean
  deleted_at: string | null
  created_at: string | null
  updated_at: string | null
}

/** 创建/编辑客户时的输入类型，所有业务字段均可选 */
export type CustomerInput = {
  name?: string | null
  phone?: string | null
  wechat?: string | null
  wechat_status?: string | null
  qq?: string | null
  province?: string | null
  region?: string | null
  grade?: string | null
  remark?: string | null
  tag?: string | null
  intention?: string | null
  feedback_status?: string | null
  customer_stage?: string | null
  source_name?: string | null
  owner?: string | null
  primary_project?: string | null
  project?: string | null
  business_dept?: string | null
  call_dept?: string | null
  call_group?: string | null
  advertiser?: string | null
  landing_page?: string | null
  assign_method?: string | null
  assign_type?: string | null
  assigned_at?: string | null
  creator?: string | null
  creator_org?: string | null
  first_consultant?: string | null
  last_consultant?: string | null
  first_assign_org?: string | null
  first_assign_person?: string | null
  first_assign_time?: string | null
  last_first_consult_time?: string | null
  last_first_consult_person?: string | null
  registration_count?: number | null
  daily_outbound_count?: number | null
  daily_connected_count?: number | null
  daily_connected_duration?: number | null
  ip?: string | null
  ip_province?: string | null
  ip_city?: string | null
  raw_chat_records?: string | null
  chat_records?: string | null
  original_id?: string | null
}

type ListCustomersParams = {
  keyword?: string
  feedback_status?: string
  customer_stage?: string
  claim_status?: string
  claimed_by?: number
  customer_tag?: string
  page?: number
  page_size?: number
}

export async function listCustomers(
  accessToken: string,
  params?: ListCustomersParams,
): Promise<PaginatedResponse<CustomerDetail>> {
  // 构建查询参数，仅传入非空值
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.feedback_status) searchParams.set('feedback_status', params.feedback_status)
  if (params?.customer_stage) searchParams.set('customer_stage', params.customer_stage)
  if (params?.claim_status) searchParams.set('claim_status', params.claim_status)
  if (params?.claimed_by) searchParams.set('claimed_by', String(params.claimed_by))
  if (params?.customer_tag) searchParams.set('customer_tag', params.customer_tag)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))

  const query = searchParams.toString()
  const path = `/customers${query ? `?${query}` : ''}`

  return requestJson<PaginatedResponse<CustomerDetail>>(path, {
    accessToken,
    errorMessage: '获取客户列表失败',
  })
}

export async function getCustomerDetail(
  accessToken: string,
  customerId: number,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}`, {
    accessToken,
    errorMessage: '获取客户详情失败',
  })
}

export async function createCustomer(
  accessToken: string,
  input: CustomerInput,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>('/customers', {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: '创建客户失败',
  })
}

export async function updateCustomer(
  accessToken: string,
  customerId: number,
  input: CustomerInput,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}/update`, {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: '编辑客户失败',
  })
}

export async function deleteCustomer(
  accessToken: string,
  customerId: number,
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/customers/${customerId}/delete`, {
    accessToken,
    method: 'POST',
    errorMessage: '删除客户失败',
  })
}

// ==================== 客户认领/释放/调配 ====================

export async function claimCustomer(
  accessToken: string,
  customerId: number,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}/claim`, {
    accessToken,
    method: 'POST',
    errorMessage: '认领客户失败',
  })
}

export type BatchResult = {
  success: number[]
  failed: { id: number; reason: string }[]
}

export async function batchClaimCustomers(
  accessToken: string,
  customerIds: number[],
): Promise<BatchResult> {
  return requestJson<BatchResult>('/customers/batch-claim', {
    accessToken,
    method: 'POST',
    body: { customer_ids: customerIds },
    errorMessage: '批量认领失败',
  })
}

export async function releaseCustomer(
  accessToken: string,
  customerId: number,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}/release`, {
    accessToken,
    method: 'POST',
    errorMessage: '释放认领失败',
  })
}

/** 锁定客户（转为长期客户） */
export async function possessionCustomer(
  accessToken: string,
  customerId: number,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}/possession`, {
    accessToken,
    method: 'POST',
    errorMessage: '锁定客户失败',
  })
}

export async function batchReleaseCustomers(
  accessToken: string,
  customerIds: number[],
): Promise<BatchResult> {
  return requestJson<BatchResult>('/customers/batch-release', {
    accessToken,
    method: 'POST',
    body: { customer_ids: customerIds },
    errorMessage: '批量释放失败',
  })
}

export async function assignCustomer(
  accessToken: string,
  customerId: number,
  targetUserId: number,
): Promise<CustomerDetail> {
  return requestJson<CustomerDetail>(`/customers/${customerId}/assign`, {
    accessToken,
    method: 'POST',
    body: { target_user_id: targetUserId },
    errorMessage: '调配客户失败',
  })
}

// ==================== 认领策略 ====================

export type ClaimStrategy = {
  id: number
  user_id: number | null
  username: string | null
  max_claim_count: number
  current_claim_count: number
  is_default: boolean
  created_at: string | null
  updated_at: string | null
}

export type CreateStrategyInput = {
  user_id: number | null
  max_claim_count: number
}

export async function listStrategies(
  accessToken: string,
): Promise<ListResponse<ClaimStrategy>> {
  return requestJson<ListResponse<ClaimStrategy>>('/strategies', {
    accessToken,
    errorMessage: '获取认领策略失败',
  })
}

export async function createStrategy(
  accessToken: string,
  input: CreateStrategyInput,
): Promise<ClaimStrategy> {
  return requestJson<ClaimStrategy>('/strategies', {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: '创建认领策略失败',
  })
}

export async function updateStrategy(
  accessToken: string,
  strategyId: number,
  maxClaimCount: number,
): Promise<ClaimStrategy> {
  return requestJson<ClaimStrategy>(`/strategies/${strategyId}/update`, {
    accessToken,
    method: 'POST',
    body: { max_claim_count: maxClaimCount },
    errorMessage: '编辑认领策略失败',
  })
}

export async function deleteStrategy(
  accessToken: string,
  strategyId: number,
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/strategies/${strategyId}/delete`, {
    accessToken,
    method: 'POST',
    errorMessage: '删除认领策略失败',
  })
}

// ==================== 跟进记录 ====================

export type FollowupRecord = {
  id: number
  customer_id: number
  user_id: number
  username: string | null
  contact_time: string
  method: string
  intention: string | null
  notes: string | null
  next_followup_time: string | null
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export type FollowupInput = {
  customer_id: number
  contact_time: string
  method: string
  intention?: string | null
  notes?: string | null
  next_followup_time?: string | null
}

export async function listFollowups(
  accessToken: string,
  customerId: number,
  page?: number,
  pageSize?: number,
): Promise<PaginatedResponse<FollowupRecord>> {
  const searchParams = new URLSearchParams()
  searchParams.set('customer_id', String(customerId))
  if (page) searchParams.set('page', String(page))
  if (pageSize) searchParams.set('page_size', String(pageSize))

  return requestJson<PaginatedResponse<FollowupRecord>>(
    `/followups?${searchParams.toString()}`,
    {
      accessToken,
      errorMessage: '获取跟进记录失败',
    },
  )
}

export async function createFollowup(
  accessToken: string,
  input: FollowupInput,
): Promise<FollowupRecord> {
  return requestJson<FollowupRecord>('/followups', {
    accessToken,
    method: 'POST',
    body: input,
    errorMessage: '创建跟进记录失败',
  })
}

export async function deleteFollowup(
  accessToken: string,
  followupId: number,
): Promise<{ success: boolean }> {
  return requestJson<{ success: boolean }>(`/followups/${followupId}/delete`, {
    accessToken,
    method: 'POST',
    errorMessage: '删除跟进记录失败',
  })
}
