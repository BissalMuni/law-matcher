import { useNavigate } from 'react-router-dom'
import { Button, Typography, Layout, Row, Col } from 'antd'
import { LoginOutlined, UserAddOutlined, FileTextOutlined } from '@ant-design/icons'

const { Title, Paragraph } = Typography
const { Content } = Layout

const Landing = () => {
  const navigate = useNavigate()

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px' }}>
        <div style={{ textAlign: 'center', maxWidth: '800px' }}>
          <FileTextOutlined style={{ fontSize: '80px', color: '#fff', marginBottom: '20px' }} />

          <Title level={1} style={{ color: '#fff', fontSize: '48px', marginBottom: '20px' }}>
            자치법규 정비 시스템
          </Title>

          <Paragraph style={{ color: '#f0f0f0', fontSize: '20px', marginBottom: '40px' }}>
            상위법령 변경 추적 및 자치법규 검토 관리 시스템
          </Paragraph>

          <Row gutter={16} justify="center">
            <Col>
              <Button
                type="primary"
                size="large"
                icon={<LoginOutlined />}
                onClick={() => navigate('/login')}
                style={{
                  height: '50px',
                  fontSize: '18px',
                  padding: '0 40px',
                  background: '#fff',
                  color: '#667eea',
                  border: 'none',
                }}
              >
                로그인
              </Button>
            </Col>
            <Col>
              <Button
                size="large"
                icon={<UserAddOutlined />}
                onClick={() => navigate('/register')}
                style={{
                  height: '50px',
                  fontSize: '18px',
                  padding: '0 40px',
                  background: 'transparent',
                  color: '#fff',
                  borderColor: '#fff',
                  borderWidth: '2px',
                }}
              >
                회원가입
              </Button>
            </Col>
          </Row>

          <div style={{ marginTop: '60px', color: '#f0f0f0' }}>
            <Title level={4} style={{ color: '#fff' }}>
              주요 기능
            </Title>
            <Row gutter={24} style={{ marginTop: '20px' }}>
              <Col span={8}>
                <div style={{ padding: '20px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                  <Title level={5} style={{ color: '#fff' }}>
                    상위법령 추적
                  </Title>
                  <Paragraph style={{ color: '#f0f0f0' }}>
                    법령 변경사항 자동 감지 및 알림
                  </Paragraph>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ padding: '20px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                  <Title level={5} style={{ color: '#fff' }}>
                    검토 의견 관리
                  </Title>
                  <Paragraph style={{ color: '#f0f0f0' }}>
                    부서별 검토 의견 작성 및 추적
                  </Paragraph>
                </div>
              </Col>
              <Col span={8}>
                <div style={{ padding: '20px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                  <Title level={5} style={{ color: '#fff' }}>
                    통계 대시보드
                  </Title>
                  <Paragraph style={{ color: '#f0f0f0' }}>
                    정비 현황 실시간 모니터링
                  </Paragraph>
                </div>
              </Col>
            </Row>
          </div>
        </div>
      </Content>
    </Layout>
  )
}

export default Landing
