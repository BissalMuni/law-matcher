import { Row, Col, Card, Statistic, Table, Tag, List, Typography } from 'antd'
import {
  FileTextOutlined,
  AlertOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../services/api'
import { RevisionNeededItem } from '../types/api'

const { Title } = Typography

export default function Dashboard() {
  const [revisionPageSize, setRevisionPageSize] = useState(10)

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.getSummary,
  })

  const { data: recentAmendments } = useQuery({
    queryKey: ['dashboard', 'recent-amendments'],
    queryFn: () => dashboardApi.getRecentAmendments(5),
  })

  const { data: pendingReviews } = useQuery({
    queryKey: ['dashboard', 'pending-reviews'],
    queryFn: () => dashboardApi.getPendingReviews(5),
  })

  const { data: revisionNeeded, isLoading: revisionLoading } = useQuery({
    queryKey: ['dashboard', 'revision-needed', revisionPageSize],
    queryFn: () => dashboardApi.getRevisionNeeded({ limit: revisionPageSize }),
  })

  const urgencyColor: Record<string, string> = {
    HIGH: 'red',
    MEDIUM: 'orange',
    LOW: 'blue',
  }

  const revisionStatusMeta: Record<string, { color: string; label: string }> = {
    NEEDS_REVISION: { color: 'red', label: '개정 필요' },
    COMPLETED: { color: 'green', label: '개정 완료' },
    UNDER_REVIEW: { color: 'gold', label: '검토중' },
  }

  const toDateValue = (value: string | null | undefined) => {
    if (!value) return 0
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? 0 : date.getTime()
  }

  const formatDate = (value: string | null | undefined) => {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleDateString()
  }

  const departmentFilters = useMemo(() => {
    const departments = new Set<string>()
    revisionNeeded?.items?.forEach((item) => {
      if (item.department) departments.add(item.department)
    })
    return Array.from(departments).map((department) => ({
      text: department,
      value: department,
    }))
  }, [revisionNeeded?.items])

  const columns = [
    {
      title: '상태',
      dataIndex: 'revision_status',
      key: 'revision_status',
      filters: [
        { text: '개정 필요', value: 'NEEDS_REVISION' },
        { text: '개정 완료', value: 'COMPLETED' },
        { text: '검토중', value: 'UNDER_REVIEW' },
      ],
      onFilter: (value: string | number | boolean, record: RevisionNeededItem) =>
        record.revision_status === value,
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        a.revision_status.localeCompare(b.revision_status),
      render: (status: string) => {
        const meta = revisionStatusMeta[status] || { color: 'default', label: status }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '조례명',
      dataIndex: 'ordinance_name',
      key: 'ordinance_name',
      render: (_: string, record: RevisionNeededItem) => (
        <Link to={`/ordinances/${record.ordinance_id}`}>{record.ordinance_name}</Link>
      ),
    },
    {
      title: '조례개정일',
      dataIndex: 'ordinance_revision_date',
      key: 'ordinance_revision_date',
      render: (value: string | null) => formatDate(value),
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        toDateValue(a.ordinance_revision_date) - toDateValue(b.ordinance_revision_date),
    },
    {
      title: '상위법령',
      dataIndex: 'law_name',
      key: 'law_name',
    },
    {
      title: '법령공포일',
      dataIndex: 'law_proclaimed_date',
      key: 'law_proclaimed_date',
      render: (value: string | null) => formatDate(value),
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        toDateValue(a.law_proclaimed_date) - toDateValue(b.law_proclaimed_date),
    },
    {
      title: '날짜차이',
      dataIndex: 'days_diff',
      key: 'days_diff',
      render: (value: number) => `${Math.abs(value)}일`,
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) => a.days_diff - b.days_diff,
    },
    {
      title: '소관부서',
      dataIndex: 'department',
      key: 'department',
      render: (value: string | null) => value || '-',
      filters: departmentFilters,
      onFilter: (value: string | number | boolean, record: RevisionNeededItem) =>
        record.department === value,
    },
  ]

  return (
    <div>
      <Title level={4}>대시보드</Title>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="자치법규"
              value={summary?.total_ordinances || 0}
              prefix={<FileTextOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="상위법령"
              value={summary?.total_parent_laws || 0}
              prefix={<FileTextOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="최근 개정"
              value={summary?.recent_amendments || 0}
              prefix={<AlertOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="개정 필요"
              value={summary?.revision_needs_action_count || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="최근 법령 개정" size="small">
            <List
              dataSource={recentAmendments?.items || []}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={item.law_name}
                    description={`${item.change_type} | 영향 조례: ${item.affected_ordinances}건`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="검토 대기" size="small">
            <List
              dataSource={pendingReviews?.items || []}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={item.ordinance_name}
                    description={item.law_name}
                  />
                  <Tag color={urgencyColor[item.urgency]}>{item.urgency}</Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24}>
          <Card
            title="조례 개정 상태 (상위법령 개정 추적)"
            size="small"
            extra={(
              <div>
                <Tag color="red">개정 필요 {revisionNeeded?.needs_revision_count || 0}</Tag>
                <Tag color="green">개정 완료 {revisionNeeded?.completed_count || 0}</Tag>
              </div>
            )}
          >
            <Table<RevisionNeededItem>
              rowKey={(record) => `${record.ordinance_id}-${record.law_id}`}
              columns={columns}
              dataSource={revisionNeeded?.items || []}
              loading={revisionLoading}
              rowClassName={(record) => {
                const meta = revisionStatusMeta[record.revision_status]
                return meta ? `revision-row-${record.revision_status.toLowerCase()}` : ''
              }}
              pagination={{
                pageSize: revisionPageSize,
                showSizeChanger: true,
                pageSizeOptions: ['10', '20', '50'],
                onChange: (_page, pageSize) => {
                  if (pageSize && pageSize !== revisionPageSize) {
                    setRevisionPageSize(pageSize)
                  }
                },
              }}
              size="small"
              locale={{ emptyText: '표시할 데이터가 없습니다.' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
