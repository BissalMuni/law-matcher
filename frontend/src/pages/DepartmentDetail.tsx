import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Table,
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Descriptions,
  Tag,
  Space,
} from 'antd'
import { ArrowLeftOutlined, FileTextOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { departmentApi } from '../services/api'

const { Title } = Typography

export default function DepartmentDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const departmentId = parseInt(id || '0', 10)

  const { data: department, isLoading: isDeptLoading } = useQuery({
    queryKey: ['department', departmentId],
    queryFn: () => departmentApi.getById(departmentId),
    enabled: !!departmentId,
  })

  const { data: ordinances, isLoading: isOrdinancesLoading } = useQuery({
    queryKey: ['department-ordinances', departmentId, page],
    queryFn: () => departmentApi.getOrdinances(departmentId, { page, size: 20 }),
    enabled: !!departmentId,
  })

  const columns = [
    {
      title: '자치법규명',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <a onClick={() => navigate(`/ordinances/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '분류',
      dataIndex: 'category',
      key: 'category',
      width: 100,
    },
    {
      title: '시행일',
      dataIndex: 'enforced_date',
      key: 'enforced_date',
      width: 120,
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'ACTIVE' ? 'green' : 'default'}>{status}</Tag>
      ),
    },
  ]

  if (isDeptLoading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/departments')}
        >
          목록으로
        </Button>
      </Space>

      <Title level={4}>{department?.name}</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Descriptions column={3}>
              <Descriptions.Item label="부서코드">
                {department?.code}
              </Descriptions.Item>
              <Descriptions.Item label="부서명">
                {department?.name}
              </Descriptions.Item>
              <Descriptions.Item label="연락처">
                {department?.phone || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="상위부서코드">
                {department?.parent_code || '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="소관 자치법규"
              value={ordinances?.total || 0}
              prefix={<FileTextOutlined />}
              suffix="건"
            />
          </Card>
        </Col>
      </Row>

      <Card title="소관 자치법규 목록">
        <Table
          columns={columns}
          dataSource={ordinances?.items || []}
          rowKey="id"
          loading={isOrdinancesLoading}
          pagination={{
            current: page,
            total: ordinances?.total || 0,
            pageSize: 20,
            onChange: setPage,
            showTotal: (total) => `총 ${total}건`,
          }}
        />
      </Card>
    </div>
  )
}
