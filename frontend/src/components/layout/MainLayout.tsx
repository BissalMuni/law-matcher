import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, theme } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  AlertOutlined,
  CheckSquareOutlined,
  SyncOutlined,
  TeamOutlined,
  BarChartOutlined,
  BookOutlined,
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '대시보드',
  },
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
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer },
  } = theme.useToken()

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
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
          <SyncOutlined style={{ fontSize: 20, cursor: 'pointer' }} />
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
