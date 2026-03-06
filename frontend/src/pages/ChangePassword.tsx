import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { authApi } from '../services/api'

const { Title } = Typography

export default function ChangePassword() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: { current_password: string; new_password: string }) => {
    setLoading(true)
    try {
      await authApi.changePassword(values.current_password, values.new_password)
      message.success('비밀번호가 변경되었습니다.')
      navigate(-1)
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      if (error?.response?.status === 400) {
        message.error(detail || '현재 비밀번호가 일치하지 않습니다.')
      } else {
        message.error('비밀번호 변경 중 오류가 발생했습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 480, margin: '40px auto' }}>
      <Card>
        <Title level={4} style={{ marginBottom: 24 }}>비밀번호 변경</Title>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="current_password"
            label="현재 비밀번호"
            rules={[{ required: true, message: '현재 비밀번호를 입력하세요' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="현재 비밀번호" />
          </Form.Item>

          <Form.Item
            name="new_password"
            label="새 비밀번호"
            rules={[
              { required: true, message: '새 비밀번호를 입력하세요' },
              { min: 8, message: '비밀번호는 8자 이상이어야 합니다' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="새 비밀번호 (8자 이상)" />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="새 비밀번호 확인"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '새 비밀번호를 다시 입력하세요' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('비밀번호가 일치하지 않습니다'))
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="새 비밀번호 확인" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              비밀번호 변경
            </Button>
          </Form.Item>
          <Button type="text" block onClick={() => navigate(-1)}>
            취소
          </Button>
        </Form>
      </Card>
    </div>
  )
}
