import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message, Layout, Select } from 'antd'
import { LockOutlined, ArrowLeftOutlined, CrownOutlined, TeamOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { departmentApi, authApi } from '../services/api'

const { Title, Text } = Typography
const { Content } = Layout

interface Department {
  id: number
  name: string
  parent_name?: string | null
  sort_order: number
}

const Login = () => {
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState<Department[]>([])
  const [searchParams] = useSearchParams()
  const loginType = searchParams.get('type') === 'admin' ? 'admin' : 'user'
  const { login, loginSimple } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (loginType === 'user') {
      loadDepartments()
    }
  }, [loginType])

  const loadDepartments = async () => {
    try {
      const data = await departmentApi.getAll()
      setDepartments(data)
    } catch (error) {
      console.error('Failed to load departments:', error)
      message.error('부서 목록을 불러오는데 실패했습니다.')
    }
  }

  const onFinishAdmin = async (values: { password: string }) => {
    setLoading(true)
    try {
      await login('admin', values.password)
      message.success('관리자 로그인 성공!')
      navigate('/ordinances')
    } catch {
      message.error('비밀번호가 올바르지 않습니다.')
    } finally {
      setLoading(false)
    }
  }

  const onFinishUser = async (values: { department: number; password: string }) => {
    setLoading(true)
    try {
      const dept = departments.find(d => d.id === values.department)
      const deptName = dept?.parent_name
        ? `${dept.parent_name} - ${dept.name}`
        : dept?.name || '부서'
      await login('user', values.password, deptName)
      message.success('로그인 성공!')
      navigate('/ordinances')
    } catch {
      message.error('비밀번호가 올바르지 않습니다.')
    } finally {
      setLoading(false)
    }
  }

  const isAdmin = loginType === 'admin'

  return (
    <Layout style={{ minHeight: '100vh', background: '#000' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px' }}>
        <Card
          style={{
            width: '100%',
            maxWidth: '450px',
            boxShadow: '0 4px 20px rgba(255,255,255,0.1)',
            borderRadius: '12px',
            background: '#1a1a1a',
            border: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            {isAdmin ? (
              <CrownOutlined style={{ fontSize: '48px', color: '#722ed1', marginBottom: '16px' }} />
            ) : (
              <TeamOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
            )}
            <Title level={2} style={{ marginBottom: '8px', color: '#fff' }}>
              {isAdmin ? '관리자 로그인' : '부서 로그인'}
            </Title>
            <Text style={{ color: '#bfbfbf' }}>자치법규 정비 시스템</Text>
          </div>

          {isAdmin ? (
            <Form name="adminLogin" onFinish={onFinishAdmin} layout="vertical" size="large">
              <Form.Item
                name="password"
                rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="관리자 비밀번호"
                  autoComplete="current-password"
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  style={{ background: '#722ed1', borderColor: '#722ed1' }}
                >
                  관리자 로그인
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Form name="userLogin" onFinish={onFinishUser} layout="vertical" size="large">
              <Form.Item
                name="department"
                rules={[{ required: true, message: '부서를 선택하세요' }]}
              >
                <Select
                  placeholder="부서 선택"
                  showSearch
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                >
                  {departments.map(dept => (
                    <Select.Option key={dept.id} value={dept.id}>
                      {dept.parent_name ? `${dept.parent_name} - ${dept.name}` : dept.name}
                    </Select.Option>
                  ))}
                </Select>
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
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                >
                  로그인
                </Button>
              </Form.Item>
            </Form>
          )}

          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <Link to="/landing" style={{ color: '#1890ff' }}>
              <ArrowLeftOutlined /> 홈으로 돌아가기
            </Link>
          </div>
        </Card>
      </Content>

      <style>{`
        .ant-input::placeholder,
        .ant-input-password input::placeholder {
          color: rgba(255, 255, 255, 0.65) !important;
        }
        .ant-select-selector {
          background: transparent !important;
        }
        .ant-select-selection-placeholder {
          color: rgba(255, 255, 255, 0.65) !important;
        }
      `}</style>
    </Layout>
  )
}

export default Login
