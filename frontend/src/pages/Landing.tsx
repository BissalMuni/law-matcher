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
            <div style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '22px', marginBottom: '30px' }}>
              주요기능
            </div>

            <Row gutter={24} justify="center">
              <Col span={8}>
                <div className="feature-box" style={{ padding: '30px 20px', background: '#f5f5f5', borderRadius: '20px', border: '1px solid #e8e8e8', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, marginBottom: '10px' }}>
                    상위법령 추적
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0, fontSize: '18px' }}>
                    법령 변경사항 자동감지 및 알림
                  </Paragraph>
                </div>
              </Col>
              <Col span={8}>
                <div className="feature-box" style={{ padding: '30px 20px', background: '#f5f5f5', borderRadius: '20px', border: '1px solid #e8e8e8', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, marginBottom: '10px' }}>
                    검토의견 관리
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0, fontSize: '18px' }}>
                    부서별 검토의견 작성 및 추적
                  </Paragraph>
                </div>
              </Col>
              <Col span={8}>
                <div className="feature-box" style={{ padding: '30px 20px', background: '#f5f5f5', borderRadius: '20px', border: '1px solid #e8e8e8', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
                  <Title level={5} style={{ color: '#000', margin: 0, marginBottom: '10px' }}>
                    통계 대시보드
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0, fontSize: '18px' }}>
                    정비현황 실시간 모니터링
                  </Paragraph>
                </div>
              </Col>
            </Row>
          </div>
        </div>
      </Content>

      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }

        .feature-box::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(
            120deg,
            transparent 30%,
            rgba(255, 255, 255, 0.6) 50%,
            transparent 70%
          );
          
          animation: shimmer 5s ease-in-out infinite;
        }
      `}</style>
    </Layout>
  )
}

export default Landing
