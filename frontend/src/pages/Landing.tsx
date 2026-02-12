import { useNavigate } from 'react-router-dom'
import { Button, Typography, Layout, Row, Col } from 'antd'
import { CrownOutlined, TeamOutlined } from '@ant-design/icons'
import mainLogo from '../assets/img_main_logo_new.png'
import logo from '../assets/logo.svg'

const { Title, Paragraph } = Typography
const { Content } = Layout

const Landing = () => {
  const navigate = useNavigate()

  return (
    <Layout style={{ minHeight: '100vh', background: '#fff', position: 'relative' }}>
      <div style={{ position: 'absolute', top: '50px', left: '100px' }}>
        <img
          src={mainLogo}
          alt="Main Logo"
          style={{
            height: '60px'
          }}
        />
      </div>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px' }}>
        <div style={{ textAlign: 'center', maxWidth: '1200px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            {/* <img
              src={logo}
              alt="OLM Logo"
              style={{
                width: '100px',
                marginBottom: '10px',
                filter: 'drop-shadow(0 0 20px rgba(24, 144, 255, 0.3))'
              }}
            /> */}
            <Title level={1} style={{ fontSize: '72px', marginBottom: '20px', textAlign: 'center', width: '100%' }}>
              <span style={{ color: '#063B94' }}>강남구</span>
              <span style={{ color: '#000' }}> 자치법규 스마트 정비시스템</span>
            </Title>
          </div>

          <Paragraph style={{ color: '#666', fontSize: '20px', marginBottom: '40px' }}>

          </Paragraph>

          <Row gutter={16} justify="center">
            <Col>
              <Button
                type="primary"
                size="large"
                icon={<TeamOutlined />}
                onClick={() => navigate('/login?type=user')}
                style={{
                  height: '50px',
                  fontSize: '18px',
                  padding: '0 40px',
                  background: '#1890ff',
                  color: '#fff',
                  border: 'none',
                }}
              >
                부서 로그인
              </Button>
            </Col>
            <Col>
              <Button
                size="large"
                icon={<CrownOutlined />}
                onClick={() => navigate('/login?type=admin')}
                style={{
                  height: '50px',
                  fontSize: '18px',
                  padding: '0 40px',
                  background: '#722ed1',
                  color: '#fff',
                  border: 'none',
                }}
              >
                관리자 로그인
              </Button>
            </Col>
          </Row>

          <div style={{ marginTop: '60px', color: '#333' }}>
            <Row style={{ marginTop: '20px', fontWeight: 'bold' }}>
              주요 기능
            </Row>

            <Row style={{ marginTop: '20px' }}>
              <Col span={24}>
                <div style={{ padding: '20px', background: '#f5f5f5', borderRadius: '8px', border: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, whiteSpace: 'nowrap' }}>
                    상위법령 추적
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0 }}>
                    법령 변경사항 자동 감지 및 알림
                  </Paragraph>
                </div>
              </Col>
            </Row>
            <Row style={{ marginTop: '12px' }}>
              <Col span={24}>
                <div style={{ padding: '20px', background: '#f5f5f5', borderRadius: '8px', border: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, whiteSpace: 'nowrap' }}>
                    검토 의견 관리
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0 }}>
                    부서별 검토 의견 작성 및 추적
                  </Paragraph>
                </div>
              </Col>
            </Row>
            <Row style={{ marginTop: '12px' }}>
              <Col span={24}>
                <div style={{ padding: '20px', background: '#f5f5f5', borderRadius: '8px', border: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, whiteSpace: 'nowrap' }}>
                    통계 대시보드
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0 }}>
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
