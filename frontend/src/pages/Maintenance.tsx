import { Layout, Typography, Button } from 'antd'
import { ToolOutlined, ReloadOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography
const { Content } = Layout

interface MaintenanceProps {
  message?: string
}

const Maintenance = ({ message }: MaintenanceProps) => {
  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '50px',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: '600px' }}>
          <ToolOutlined
            style={{
              fontSize: '80px',
              color: '#faad14',
              marginBottom: '24px',
            }}
          />
          <Title level={2} style={{ color: '#333' }}>
            시스템 정비 중
          </Title>
          <Paragraph
            style={{
              fontSize: '16px',
              color: '#666',
              marginBottom: '32px',
            }}
          >
            {message || '시스템 정비 중입니다. 잠시 후 다시 접속해 주세요.'}
          </Paragraph>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            size="large"
            onClick={() => window.location.reload()}
          >
            새로고침
          </Button>
        </div>
      </Content>
    </Layout>
  )
}

export default Maintenance
