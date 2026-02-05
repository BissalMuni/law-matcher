import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme, Dropdown, Space, Avatar } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  AlertOutlined,
  CheckSquareOutlined,
  SyncOutlined,
  TeamOutlined,
  BarChartOutlined,
  BookOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { useAuth } from '../../contexts/AuthContext'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/ordinances',
    icon: <FileTextOutlined />,
    label: '자치법규',
  },
  {
    key: '/laws',
    icon: <BookOutlined />,
    label: '상위법령',
  },
  {
    key: '/amendments',
    icon: <AlertOutlined />,
    label: '개정법령',
  },
  {
    key: '/reviews',
    icon: <CheckSquareOutlined />,
    label: '개정 검토',
  },
  {
    key: '/departments',
    icon: <TeamOutlined />,
    label: '부서별관리',
  },
  {
    key: '/statistics',
    icon: <BarChartOutlined />,
    label: '통계정보',
  },
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '대시보드',
  },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  const handleLogout = () => {
    logout()
    navigate('/landing')
  }

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '프로필',
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '로그아웃',
      onClick: handleLogout,
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <h1 style={{ fontSize: collapsed ? 16 : 18, margin: 0 }}>
            {collapsed ? 'LM' : 'Law Matcher'}
          </h1>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <h2 style={{ margin: 0 }}>OLM 자치법규 개정 검토 시스템</h2>

          <Dropdown menu={{ items: userMenuItems }} trigger={['click']}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar
                size="small"
                icon={<UserOutlined />}
                style={{ backgroundColor: '#667eea' }}
              />
              <span>
                {user?.full_name || user?.username}
                {user?.user_type === 'DEPARTMENT' && user?.department_name && (
                  <span style={{ color: '#888', fontSize: '13px' }}> ({user.department_name})</span>
                )}
                {user?.user_type === 'DEPARTMENT' && !user?.department_name && (
                  <span style={{ color: '#888', fontSize: '13px' }}> (부서)</span>
                )}
              </span>
              <DownOutlined style={{ fontSize: 12 }} />
            </Space>
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: colorBgContainer,
            borderRadius: 8,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
