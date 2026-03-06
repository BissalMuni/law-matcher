import { Card, Row, Col, Statistic, Table, DatePicker, Space, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../services/api'
import type { AiAnalyticsData } from '../types/api'
import dayjs from 'dayjs'
import { useState } from 'react'

const { RangePicker } = DatePicker
const { Title } = Typography

export default function AiAnalytics() {
  const [dateRange, setDateRange] = useState<[string | undefined, string | undefined]>([undefined, undefined])

  const { data, isLoading } = useQuery<AiAnalyticsData>({
    queryKey: ['ai-analytics', dateRange],
    queryFn: () =>
      adminApi.getAiAnalytics({
        start_date: dateRange[0],
        end_date: dateRange[1],
      }),
  })

  const providerData = data?.by_provider
    ? Object.entries(data.by_provider).map(([name, stats]) => ({
        key: name,
        provider: name,
        count: stats.count,
        model: stats.model,
      }))
    : []

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>AI 분석 이력</Title>
        <RangePicker
          onChange={(dates) => {
            if (dates) {
              setDateRange([
                dates[0]?.format('YYYY-MM-DD'),
                dates[1]?.format('YYYY-MM-DD'),
              ])
            } else {
              setDateRange([undefined, undefined])
            }
          }}
        />
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card loading={isLoading}>
            <Statistic title="총 분석 건수" value={data?.total_analyses ?? 0} suffix="건" />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={isLoading}>
            <Statistic
              title="성공률"
              value={data?.total_analyses ? Math.round((data.success_count / data.total_analyses) * 100) : 0}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={isLoading}>
            <Statistic
              title="AI 초안 채택률"
              value={Math.round((data?.draft_adoption_rate ?? 0) * 100)}
              suffix="%"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={isLoading}>
            <Statistic
              title="AI 초안 수정률"
              value={Math.round((data?.draft_modified_rate ?? 0) * 100)}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="프로바이더별 사용량" loading={isLoading}>
            <Table
              dataSource={providerData}
              columns={[
                { title: '프로바이더', dataIndex: 'provider', key: 'provider' },
                { title: '모델', dataIndex: 'model', key: 'model' },
                { title: '분석 수', dataIndex: 'count', key: 'count' },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="평균 토큰 사용량" loading={isLoading}>
            {data?.average_token_usage ? (
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="입력 토큰" value={data.average_token_usage.input_tokens} />
                </Col>
                <Col span={12}>
                  <Statistic title="출력 토큰" value={data.average_token_usage.output_tokens} />
                </Col>
              </Row>
            ) : (
              <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
                데이터 없음
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
