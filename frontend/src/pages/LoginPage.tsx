import { Alert, Button, Card, Form, Input, Space, Spin, Typography } from 'antd'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'

import { useAuth } from '../auth'
import { ApiError } from '../lib/api-client'

type LoginFormValues = {
  username: string
  password: string
}

type LoginLocationState = {
  from?: {
    pathname?: string
    search?: string
  }
}

export function LoginPage() {
  const { isLoading, login, user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const redirectTarget = (() => {
    const state = location.state as LoginLocationState | null
    const pathname = state?.from?.pathname

    if (!pathname) {
      return '/'
    }

    return `${pathname}${state?.from?.search ?? ''}`
  })()

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  const handleFinish = async (values: LoginFormValues) => {
    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      await login(values)
      navigate(redirectTarget, { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('登录失败')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <Card style={{ width: '100%', maxWidth: 420 }}>
        <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
          <div>
            <Typography.Title level={2}>后台登录</Typography.Title>
            <Typography.Paragraph>
              请使用管理员账号登录后台管理系统。
            </Typography.Paragraph>
          </div>

          {errorMessage ? <Alert type="error" message={errorMessage} showIcon /> : null}

          <Form<LoginFormValues> layout="vertical" onFinish={(values) => void handleFinish(values)}>
            <Form.Item
              label="用户名"
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input autoComplete="username" placeholder="请输入用户名" />
            </Form.Item>

            <Form.Item
              label="密码"
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password autoComplete="current-password" placeholder="请输入密码" />
            </Form.Item>

            <Button block type="primary" htmlType="submit" loading={isSubmitting}>
              登录
            </Button>
          </Form>
        </Space>
      </Card>
    </div>
  )
}
