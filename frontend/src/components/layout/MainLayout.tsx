import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme, Dropdown, Space, Avatar } from 'antd'
import type { MenuProps } from 'antd'
import {
  FileTextOutlined,
  TeamOutlined,
  BarChartOutlined,
  BookOutlined,
  UserOutlined,
  LogoutOutlined,
  DownOutlined,
  SyncOutlined,
  SettingOutlined,
  ExperimentOutlined,
  DiffOutlined,
  LockOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import { useAuth } from '../../contexts/AuthContext'

const { Header, Sider, Content } = Layout

// Menu items for admin users (6 tabs)
const adminMenuItems = [
  {
    key: '/ordinances',
    icon: <FileTextOutlined />,
    label: '자치법규관리',
  },
  {
    key: '/amendments',
    icon: <SyncOutlined />,
    label: '변경감지',
  },
  {
    key: '/reviews',
    icon: <CheckCircleOutlined />,
    label: '승인관리',
  },
  {
    key: '/admin/batch',
    icon: <ThunderboltOutlined />,
    label: '일괄 검토',
  },
  {
    key: '/laws',
    icon: <BookOutlined />,
    label: '법령관리',
  },
 
  {
    key: '/departments',
    icon: <TeamOutlined />,
    label: '부서관리',
  },
  {
    key: '/dashboard',
    icon: <BarChartOutlined />,
    label: '현황',
  },
  {
    key: '/admin/settings',
    icon: <SettingOutlined />,
    label: 'LLM 설정',
  },
  {
    key: '/admin/ai-analytics',
    icon: <ExperimentOutlined />,
    label: 'AI 이력',
  },
  {
    key: '/admin/detection-compare',
    icon: <DiffOutlined />,
    label: '탭 비교',
  },
]

// Menu items for regular users (3 tabs)
const regularUserMenuItems = [
  {
    key: '/ordinances',
    icon: <FileTextOutlined />,
    label: '자치법규관리',
  },
  {
    key: '/dashboard',
    icon: <BarChartOutlined />,
    label: '현황',
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

  const userDropdownItems: MenuProps['items'] = [
    {
      key: 'change-password',
      icon: <LockOutlined />,
      label: '비밀번호 변경',
      onClick: () => navigate('/change-password'),
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

  // Select menu items based on user type
  const sidebarMenuItems = user?.user_type === 'ADMIN' ? adminMenuItems : regularUserMenuItems

  // Match selectedKeys by pathname prefix for sub-routes
  const getSelectedKey = () => {
    const menuKeys = sidebarMenuItems.map((item) => item.key)
    const matched = menuKeys.find((key) => location.pathname === key || location.pathname.startsWith(key + '/'))
    return matched ? [matched] : []
  }

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
          selectedKeys={getSelectedKey()}
          items={sidebarMenuItems}
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

          <Dropdown menu={{ items: userDropdownItems }} trigger={['click']}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar
                size="small"
                icon={<UserOutlined />}
                style={{ backgroundColor: '#667eea' }}
              />
              <span>
                {user?.username}
                {user?.user_type === 'ADMIN' && (
                  <span style={{ color: '#667eea', fontSize: '13px', fontWeight: 500 }}> (관리자)</span>
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
