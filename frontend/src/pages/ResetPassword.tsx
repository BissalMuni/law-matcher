import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message, Layout, Result } from 'antd'
import { LockOutlined, KeyOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { authApi } from '../services/api'

const { Title, Text } = Typography
const { Content } = Layout

const ResetPassword = () => {
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const onFinish = async (values: { password: string }) => {
    if (!token) {
      message.error('유효하지 않은 링크입니다.')
      return
    }

    setLoading(true)
    try {
      await authApi.resetPassword(token, values.password)
      setSuccess(true)
    } catch (error: any) {
      console.error('Reset password error:', error)
      const errorMessage = error.response?.data?.detail || '비밀번호 재설정에 실패했습니다.'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
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
            <Result
              status="error"
              title="유효하지 않은 링크"
              subTitle="비밀번호 재설정 링크가 유효하지 않습니다. 다시 시도해주세요."
              extra={
                <Link to="/forgot-password">
                  <Button type="primary">비밀번호 찾기로 이동</Button>
                </Link>
              }
            />
          </Card>
        </Content>
      </Layout>
    )
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
          {success ? (
            <Result
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title="비밀번호가 변경되었습니다"
              subTitle="새 비밀번호로 로그인하세요."
              extra={
                <Button type="primary" onClick={() => navigate('/login')}>
                  로그인하기
                </Button>
              }
            />
          ) : (
            <>
              <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                <KeyOutlined style={{ fontSize: '48px', color: '#667eea', marginBottom: '16px' }} />
                <Title level={2} style={{ marginBottom: '8px' }}>
                  비밀번호 재설정
                </Title>
                <Text type="secondary">새로운 비밀번호를 입력하세요.</Text>
              </div>

              <Form name="reset-password" onFinish={onFinish} layout="vertical" size="large">
                <Form.Item
                  name="password"
                  rules={[
                    { required: true, message: '비밀번호를 입력하세요' },
                    { min: 8, message: '비밀번호는 최소 8자 이상이어야 합니다' },
                  ]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="새 비밀번호 (최소 8자)"
                    autoComplete="new-password"
                  />
                </Form.Item>

                <Form.Item
                  name="confirm_password"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: '비밀번호를 다시 입력하세요' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve()
                        }
                        return Promise.reject(new Error('비밀번호가 일치하지 않습니다'))
                      },
                    }),
                  ]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="비밀번호 확인"
                    autoComplete="new-password"
                  />
                </Form.Item>

                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    비밀번호 변경
                  </Button>
                </Form.Item>
              </Form>
            </>
          )}
        </Card>
      </Content>
    </Layout>
  )
}

export default ResetPassword
