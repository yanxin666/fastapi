import { Alert, Button, Card, Space, Table, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { useAuth } from '../auth'
import { ApiError, type PermissionListItem, listPermissions } from '../lib/api-client'

type PermissionsState = {
  status: 'loading' | 'success' | 'error'
  items: PermissionListItem[]
  message: string | null
}

const columns = [
  {
    title: 'ID',
    dataIndex: 'id',
    key: 'id',
  },
  {
    title: '编码',
    dataIndex: 'code',
    key: 'code',
  },
  {
    title: '描述',
    dataIndex: 'description',
    key: 'description',
    render: (value: string | null) => value || '-',
  },
]

export function PermissionsPage() {
  const { accessToken, logout } = useAuth()
  const [permissionsState, setPermissionsState] = useState<PermissionsState>({
    status: 'loading',
    items: [],
    message: null,
  })

  const loadPermissions = async () => {
    if (!accessToken) {
      return
    }

    setPermissionsState({ status: 'loading', items: [], message: null })

    try {
      const result = await listPermissions(accessToken)
      setPermissionsState({ status: 'success', items: result.items, message: null })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await logout()
        return
      }

      setPermissionsState({
        status: 'error',
        items: [],
        message: error instanceof Error ? error.message : '加载权限列表失败',
      })
    }
  }

  useEffect(() => {
    void loadPermissions()
  }, [accessToken])

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <Card
        title={<Typography.Title level={2} style={{ margin: 0 }}>权限列表</Typography.Title>}
        extra={
          <Button
            onClick={() => void loadPermissions()}
            loading={permissionsState.status === 'loading'}
          >
            刷新
          </Button>
        }
      >
        <Typography.Paragraph style={{ marginBottom: 0 }}>
          查看系统内可分配的权限编码与说明。
        </Typography.Paragraph>
      </Card>

      {permissionsState.status === 'error' && permissionsState.message ? (
        <Alert type="error" message={permissionsState.message} showIcon />
      ) : null}

      <Card>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={permissionsState.items}
          loading={permissionsState.status === 'loading'}
          pagination={false}
        />
      </Card>
    </Space>
  )
}
