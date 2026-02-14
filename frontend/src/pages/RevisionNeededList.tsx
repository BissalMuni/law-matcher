import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table,
  Select,
  Space,
  Typography,
  Tag,
  DatePicker,
  Card,
  Statistic,
  Row,
  Col,
  Alert,
} from 'antd'
import {
  WarningOutlined,
  FileTextOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { articleApi, departmentApi } from '../services/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Title } = Typography
const { Option } = Select

interface RevisionNeededItem {
  ordinance_id: number
  ordinance_name: string
  ordinance_category: string
  department: string
  article_id: number
  article_no: string
  article_title: string
  law_name: string
  change_date: string
  detected_at: string
  change_type: string
  diff_html?: string
}

interface RevisionNeededListResponse {
  items: RevisionNeededItem[]
  total: number
  page: number
  size: number
}

export default function RevisionNeededList() {
  const navigate = useNavigate()

  // State
  const [page, setPage] = useState(1)
  const [days, setDays] = useState(30)
  const [department, setDepartment] = useState<string | undefined>(undefined)

  // 부서 목록 조회
  const { data: departmentsData } = useQuery({
    queryKey: ['departments-all'],
    queryFn: () => departmentApi.getAll(),
  })

  // 개정 검토 필요 조례 목록 조회
  const { data, isLoading } = useQuery<RevisionNeededListResponse>({
    queryKey: ['revision-needed', page, days, department],
    queryFn: () =>
      articleApi.getRevisionNeededOrdinances({
        page,
        size: 20,
        days,
        department,
      }),
  })

  // 테이블 컬럼 정의
  const columns: ColumnsType<RevisionNeededItem> = [
    {
      title: '조례명',
      dataIndex: 'ordinance_name',
      key: 'ordinance_name',
      width: 300,
      render: (text, record) => (
        <div>
          <a onClick={() => navigate(`/ordinances/${record.ordinance_id}`)}>
            {text}
          </a>
          <div style={{ fontSize: 12, color: '#888' }}>
            {record.ordinance_category}
          </div>
        </div>
      ),
    },
    {
      title: '담당부서',
      dataIndex: 'department',
      key: 'department',
      width: 150,
    },
    {
      title: '변경된 법령 조문',
      key: 'article',
      width: 300,
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.law_name}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            제{record.article_no}조 {record.article_title}
          </div>
        </div>
      ),
    },
    {
      title: '감지일',
      dataIndex: 'detected_at',
      key: 'detected_at',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '변경 유형',
      dataIndex: 'change_type',
      key: 'change_type',
      width: 100,
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          created: 'green',
          updated: 'orange',
          deleted: 'red',
        }
        const labelMap: Record<string, string> = {
          created: '신규',
          updated: '수정',
          deleted: '삭제',
        }
        return <Tag color={colorMap[type]}>{labelMap[type] || type}</Tag>
      },
    },
    {
      title: '조치',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => navigate(`/articles/${record.article_id}`)}>
            조문 보기
          </a>
          <a onClick={() => navigate(`/ordinances/${record.ordinance_id}`)}>
            조례 보기
          </a>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={3}>
            <WarningOutlined style={{ color: '#ff4d4f' }} /> 개정 검토 필요 조례
          </Title>
        </div>

        {/* Alert */}
        <Alert
          message="법령 조문 변경 감지"
          description="최근 감지된 법령 조문 변경과 매핑된 조례들입니다. 해당 조례의 개정 검토가 필요할 수 있습니다."
          type="warning"
          showIcon
          icon={<WarningOutlined />}
        />

        {/* 통계 카드 */}
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
          <Col span={8}>
            <Card>
              <Statistic
                title="조회 기간"
                value={days}
                suffix="일"
                prefix={<CalendarOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="현재 페이지"
                value={`${page} / ${Math.ceil((data?.total || 0) / 20)}`}
              />
            </Card>
          </Col>
        </Row>

        {/* Filters */}
        <Space wrap>
          <Select
            placeholder="조회 기간"
            value={days}
            onChange={(value) => {
              setDays(value)
              setPage(1)
            }}
            style={{ width: 150 }}
          >
            <Option value={7}>최근 7일</Option>
            <Option value={30}>최근 30일</Option>
            <Option value={90}>최근 90일</Option>
            <Option value={180}>최근 180일</Option>
            <Option value={365}>최근 1년</Option>
          </Select>

          <Select
            placeholder="담당부서"
            value={department}
            onChange={(value) => {
              setDepartment(value)
              setPage(1)
            }}
            style={{ width: 200 }}
            allowClear
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            options={departmentsData?.map((dept: any) => ({
              value: dept.name,
              label: dept.name,
            }))}
          />
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={data?.items}
          loading={isLoading}
          rowKey={(record) => `${record.ordinance_id}-${record.article_id}-${record.detected_at}`}
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
