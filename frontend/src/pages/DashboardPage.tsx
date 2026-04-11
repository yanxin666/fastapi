import { Button, Card, Descriptions, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { useAuth } from '../auth'
import { getAdminHealth } from '../lib/api-client'

type HealthState = {
  status: 'loading' | 'success' | 'error'
  message: string
}

const LOADING_MESSAGE = '正在检查后台服务状态...'
const ERROR_MESSAGE = '无法连接后台服务'

export function DashboardPage() {
  const { user } = useAuth()
  const [healthState, setHealthState] = useState<HealthState>({
    status: 'loading',
    message: LOADING_MESSAGE,
  })

  const refreshHealth = async () => {
    setHealthState({ status: 'loading', message: LOADING_MESSAGE })

    try {
      const result = await getAdminHealth()
      setHealthState({ status: 'success', message: result.status === 'ok' ? '连接正常' : result.status })
    } catch {
      setHealthState({ status: 'error', message: ERROR_MESSAGE })
    }
  }

  useEffect(() => {
    void refreshHealth()
  }, [])

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <Card>
        <Typography.Title level={2}>控制台</Typography.Title>
        <Typography.Paragraph>
          查看当前登录账号信息与后台服务运行状态。
        </Typography.Paragraph>
        <Descriptions column={1} size="small">
          <Descriptions.Item label="用户名">{user?.username ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user?.email ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="角色">
            {user?.roles.length ? (
              <Space wrap>
                {user.roles.map((role) => (
                  <Tag key={role} color="blue">
                    {role}
                  </Tag>
                ))}
              </Space>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="权限数量">{user?.permissions.length ?? 0}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="后台服务状态"
        extra={
          <Button onClick={() => void refreshHealth()} loading={healthState.status === 'loading'}>
            刷新
          </Button>
        }
      >
        <Descriptions column={1}>
          <Descriptions.Item label="检查项">后台服务连通性</Descriptions.Item>
          <Descriptions.Item label="状态">{healthState.message}</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
