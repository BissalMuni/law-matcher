import { Row, Col, Card, Statistic, Table, Tag, List, Typography } from 'antd'
import {
  FileTextOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../services/api'

const { Title } = Typography

export default function Dashboard() {
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

  const urgencyColor: Record<string, string> = {
    HIGH: 'red',
    MEDIUM: 'orange',
    LOW: 'blue',
  }

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
              title="검토 필요"
              value={summary?.need_revision_count || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ClockCircleOutlined />}
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
    </div>
  )
}
