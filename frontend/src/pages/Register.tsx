import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message, Layout, Select } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, UserAddOutlined, ArrowLeftOutlined, IdcardOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { departmentApi } from '../services/api'

const { Title, Text } = Typography
const { Content } = Layout
const { Option } = Select

interface Department {
  id: number
  code: string
  name: string
}

const Register = () => {
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState<Department[]>([])
  const [userType, setUserType] = useState<'GENERAL' | 'DEPARTMENT'>('GENERAL')
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()

  useEffect(() => {
    loadDepartments()
  }, [])

  const loadDepartments = async () => {
    try {
      const response = await departmentApi.getAll()
      setDepartments(response)
    } catch (error) {
      console.error('Failed to load departments:', error)
    }
  }

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const registerData = {
        email: values.email,
        username: values.username,
        password: values.password,
        full_name: values.full_name,
        user_type: values.user_type,
        department_id: values.user_type === 'DEPARTMENT' ? values.department_id : undefined,
      }

      await register(registerData)
      message.success('회원가입 성공!')
      navigate('/ordinances')
    } catch (error: any) {
      console.error('Register error:', error)
      const errorMessage = error.response?.data?.detail || '회원가입에 실패했습니다.'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleUserTypeChange = (value: 'GENERAL' | 'DEPARTMENT') => {
    setUserType(value)
    if (value === 'GENERAL') {
      form.setFieldValue('department_id', undefined)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px' }}>
        <Card
          style={{
            width: '100%',
            maxWidth: '500px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            borderRadius: '12px',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <UserAddOutlined style={{ fontSize: '48px', color: '#667eea', marginBottom: '16px' }} />
            <Title level={2} style={{ marginBottom: '8px' }}>
              회원가입
            </Title>
            <Text type="secondary">자치법규 정비 시스템</Text>
          </div>

          <Form form={form} name="register" onFinish={onFinish} layout="vertical" size="large" initialValues={{ user_type: 'GENERAL' }}>
            <Form.Item
              name="email"
              rules={[
                { required: true, message: '이메일을 입력하세요' },
                { type: 'email', message: '올바른 이메일 형식이 아닙니다' },
              ]}
            >
              <Input prefix={<MailOutlined />} placeholder="이메일" autoComplete="email" />
            </Form.Item>

            <Form.Item
              name="username"
              rules={[
                { required: true, message: '사용자명을 입력하세요' },
                { min: 3, message: '사용자명은 최소 3자 이상이어야 합니다' },
                { max: 100, message: '사용자명은 최대 100자까지 가능합니다' },
              ]}
            >
              <Input prefix={<UserOutlined />} placeholder="사용자명 (3-100자)" autoComplete="username" />
            </Form.Item>

            <Form.Item
              name="full_name"
              rules={[
                { max: 100, message: '이름은 최대 100자까지 가능합니다' },
              ]}
            >
              <Input prefix={<IdcardOutlined />} placeholder="이름 (선택)" autoComplete="name" />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '비밀번호를 입력하세요' },
                { min: 8, message: '비밀번호는 최소 8자 이상이어야 합니다' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="비밀번호 (최소 8자)"
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

            <Form.Item
              name="user_type"
              label="사용자 유형"
              rules={[{ required: true, message: '사용자 유형을 선택하세요' }]}
            >
              <Select placeholder="사용자 유형 선택" onChange={handleUserTypeChange}>
                <Option value="GENERAL">일반 사용자</Option>
                <Option value="DEPARTMENT">부서 담당자</Option>
              </Select>
            </Form.Item>

            {userType === 'DEPARTMENT' && (
              <Form.Item
                name="department_id"
                label="소속 부서"
                rules={[{ required: true, message: '소속 부서를 선택하세요' }]}
              >
                <Select
                  placeholder="부서 선택"
                  showSearch
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.children as unknown as string).toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {departments.map((dept) => (
                    <Option key={dept.id} value={dept.id}>
                      {dept.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            )}

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                회원가입
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <Text type="secondary">
              이미 계정이 있으신가요?{' '}
              <Link to="/login" style={{ color: '#667eea', fontWeight: 500 }}>
                로그인
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

export default Register
