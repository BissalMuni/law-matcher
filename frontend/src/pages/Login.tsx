import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message, Layout } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'

const { Title, Text } = Typography
const { Content } = Layout

const Login = () => {
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('로그인 성공!')
      navigate('/ordinances')
    } catch (error: any) {
      console.error('Login error:', error)
      const errorMessage = error.response?.data?.detail || '로그인에 실패했습니다.'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px' }}>
        <Card
          style={{
            width: '100%',
            maxWidth: '450px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            borderRadius: '12px',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <LoginOutlined style={{ fontSize: '48px', color: '#667eea', marginBottom: '16px' }} />
            <Title level={2} style={{ marginBottom: '8px' }}>
              로그인
            </Title>
            <Text type="secondary">자치법규 정비 시스템</Text>
          </div>

          <Form name="login" onFinish={onFinish} layout="vertical" size="large">
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '사용자명을 입력하세요' },
                { min: 3, message: '사용자명은 최소 3자 이상이어야 합니다' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="사용자명"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="비밀번호"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                로그인
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <Text type="secondary">
              계정이 없으신가요?{' '}
              <Link to="/register" style={{ color: '#667eea', fontWeight: 500 }}>
                회원가입
              </Link>
            </Text>
          </div>

          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <Link to="/landing" style={{ color: '#8c8c8c' }}>
              <ArrowLeftOutlined /> 홈으로 돌아가기
            </Link>
          </div>
        </Card>
      </Content>
    </Layout>
  )
}

export default Login
