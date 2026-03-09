import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table,
  Select,
  Space,
  Typography,
  Tag,
  Card,
  Statistic,
  Row,
  Col,
  Button,
} from 'antd'
import {
  WarningOutlined,
  FileTextOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { ordinanceApi } from '../services/api'
import type { ColumnsType } from 'antd/es/table'

const { Title } = Typography

interface OrdinanceItem {
  id: number
  name: string
  code: string
  category: string
  department: string
  revision_status: string | null
  latest_review_result: string | null
}

const revisionStatusColor: Record<string, string> = {
  '검토대기': 'warning',
  '검토중': 'processing',
  '개정확정': 'error',
}

const reviewResultColor: Record<string, string> = {
  '개정필요': 'red',
  '개정불필요': 'green',
}

export default function RevisionNeededList() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [department, setDepartment] = useState<string | undefined>(undefined)
  const [revisionStatus, setRevisionStatus] = useState<string | undefined>(undefined)

  // 부서 목록 (조례 실데이터 기준)
  const { data: departmentsData } = useQuery({
    queryKey: ['ordinance-departments'],
    queryFn: () => ordinanceApi.getDepartments(),
  })

  // 변경 감지된 조례 목록 (needs_revision_filter)
  const { data, isLoading } = useQuery({
    queryKey: ['revision-needed', page, department, revisionStatus],
    queryFn: () =>
      ordinanceApi.getList({
        page,
        size: 20,
        revision_status_filter: revisionStatus || 'any',
        department,
      }),
  })

  const items: OrdinanceItem[] = data?.items || []

  const columns: ColumnsType<OrdinanceItem> = [
    {
      title: '조례명',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/ordinances/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '담당부서',
      dataIndex: 'department',
      key: 'department',
      width: 150,
    },
    {
      title: '분류',
      dataIndex: 'category',
      key: 'category',
      width: 120,
    },
    {
      title: '검토 상태',
      dataIndex: 'revision_status',
      key: 'revision_status',
      width: 120,
      render: (status: string | null) =>
        status ? (
          <Tag color={revisionStatusColor[status] || 'default'}>{status}</Tag>
        ) : (
          <Tag color="default">미시작</Tag>
        ),
    },
    {
      title: '최신 검토결과',
      dataIndex: 'latest_review_result',
      key: 'latest_review_result',
      width: 130,
      render: (result: string | null) =>
        result ? (
          <Tag color={reviewResultColor[result] || 'default'}>{result}</Tag>
        ) : (
          <Tag color="default">미작성</Tag>
        ),
    },
    {
      title: '조치',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          size="small"
          icon={<SearchOutlined />}
          onClick={() => navigate(`/ordinances/${record.id}`)}
        >
          상세보기
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={3}>
            <WarningOutlined style={{ color: '#ff4d4f' }} /> 개정 검토 필요 조례
          </Title>
        </div>

        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic
                title="검토 필요 조례"
                value={data?.total || 0}
                suffix="건"
                valueStyle={{ color: '#ff4d4f' }}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Space wrap>
          <Select
            placeholder="담당부서"
            value={department}
            onChange={(value) => { setDepartment(value); setPage(1) }}
            style={{ width: 200 }}
            allowClear
            showSearch
            filterOption={(input, option) =>
              String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            options={departmentsData?.map((dept: any) => ({
              value: dept.name,
              label: `${dept.name} (${dept.count})`,
            }))}
          />
          <Select
            placeholder="검토 상태"
            value={revisionStatus}
            onChange={(value) => { setRevisionStatus(value); setPage(1) }}
            style={{ width: 150 }}
            allowClear
            options={[
              { value: '검토대기', label: '검토대기' },
              { value: '검토중', label: '검토중' },
              { value: '개정확정', label: '개정확정' },
            ]}
          />
        </Space>

        <Table
          columns={columns}
          dataSource={items}
          loading={isLoading}
          rowKey="id"
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total || 0,
            onChange: (newPage) => setPage(newPage),
            showSizeChanger: false,
            showTotal: (total) => `총 ${total}건`,
          }}
        />
      </Space>
    </div>
  )
}
