import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message, Layout, Result } from 'antd'
import { MailOutlined, ArrowLeftOutlined, KeyOutlined } from '@ant-design/icons'
import { authApi } from '../services/api'

const { Title, Text } = Typography
const { Content } = Layout

const ForgotPassword = () => {
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const onFinish = async (values: { email: string }) => {
    setLoading(true)
    try {
      await authApi.forgotPassword(values.email)
      setSubmitted(true)
    } catch (error: any) {
      console.error('Forgot password error:', error)
      message.error('요청 처리 중 오류가 발생했습니다.')
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
          {submitted ? (
            <Result
              icon={<MailOutlined style={{ color: '#667eea' }} />}
              title="이메일을 확인해주세요"
              subTitle="비밀번호 재설정 링크가 이메일로 전송되었습니다. 이메일을 확인하여 비밀번호를 재설정하세요."
              extra={
                <Link to="/login">
                  <Button type="primary">로그인으로 돌아가기</Button>
                </Link>
              }
            />
          ) : (
            <>
              <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                <KeyOutlined style={{ fontSize: '48px', color: '#667eea', marginBottom: '16px' }} />
                <Title level={2} style={{ marginBottom: '8px' }}>
                  비밀번호 찾기
                </Title>
                <Text type="secondary">
                  가입 시 사용한 이메일을 입력하시면<br />
                  비밀번호 재설정 링크를 보내드립니다.
                </Text>
              </div>

              <Form name="forgot-password" onFinish={onFinish} layout="vertical" size="large">
                <Form.Item
                  name="email"
                  rules={[
                    { required: true, message: '이메일을 입력하세요' },
                    { type: 'email', message: '올바른 이메일 형식이 아닙니다' },
                  ]}
                >
                  <Input
                    prefix={<MailOutlined />}
                    placeholder="이메일"
                    autoComplete="email"
                  />
                </Form.Item>

                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    재설정 링크 보내기
                  </Button>
                </Form.Item>
              </Form>

              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <Link to="/login" style={{ color: '#8c8c8c' }}>
                  <ArrowLeftOutlined /> 로그인으로 돌아가기
                </Link>
              </div>
            </>
          )}
        </Card>
      </Content>
    </Layout>
  )
}

export default ForgotPassword
