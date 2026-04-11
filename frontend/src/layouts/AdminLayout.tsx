import { Button, Layout, Menu, Space, Typography } from 'antd'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { adminNavigationItems } from '../router/adminNavigation'

const { Content, Header, Sider } = Layout

export function AdminLayout() {
  const { logout, permissions, user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const visibleNavigationItems = adminNavigationItems.filter(
    (item) => !item.permission || permissions.includes(item.permission),
  )

  const selectedKey =
    visibleNavigationItems
      .filter((item) => (item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)))
      .sort((left, right) => right.path.length - left.path.length)[0]?.key ?? '/'

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth="0">
        <div style={{ color: '#fff', fontSize: 18, fontWeight: 600, padding: '16px 24px' }}>
          后台管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={visibleNavigationItems.map((item) => ({
            key: item.key,
            label: <Link to={item.path}>{item.label}</Link>,
          }))}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Typography.Title level={4} style={{ margin: 0 }}>
            后台管理
          </Typography.Title>
          <Space size="middle">
            <div style={{ textAlign: 'right' }}>
              <Typography.Text strong>{user?.username}</Typography.Text>
              <br />
              <Typography.Text type="secondary">{user?.email}</Typography.Text>
            </div>
            <Button onClick={() => void handleLogout()}>退出登录</Button>
          </Space>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
