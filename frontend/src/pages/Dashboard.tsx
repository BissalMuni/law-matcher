import { Row, Col, Card, Statistic, Table, Tag, Typography, Progress, Empty, Space } from 'antd'
import {
  FileTextOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  BookOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState, type Key } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Pie, Column, Bar } from '@ant-design/charts'
import {
  dashboardApi,
  departmentApi,
  lawChangesApi,
  batchApi,
  adminApi,
} from '../services/api'
import {
  RevisionNeededItem,
  OrdinanceRevisionTree,
  LatestSyncStats,
  DepartmentInputStatsResponse,
  LawChangeStatsResponse,
  DashboardSummary,
  BatchJob,
  AiAnalyticsData,
} from '../types/api'
import { useAuth } from '../contexts/AuthContext'

const { Title, Text } = Typography

const revisionStatusMeta: Record<string, { color: string; label: string }> = {
  NEEDS_REVISION: { color: 'red', label: '개정 필요' },
  COMPLETED: { color: 'green', label: '개정 완료' },
  UNDER_REVIEW: { color: 'gold', label: '검토중' },
  RE_REVIEW: { color: 'volcano', label: '재검토중' },
}

const stepLabels: Record<string, string> = {
  step1_select: '1. 대상 선정',
  step2_detect: '2. 개정 판별',
  step3_collect: '3. 정보 수집',
  step4_analyze: '4. AI 분석',
  step5_report: '5. 보고서',
}

const stepStatusColor: Record<string, string> = {
  idle: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
}

function toDateValue(value: string | null | undefined) {
  if (!value) return 0
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? 0 : d.getTime()
}

function formatDate(value: string | null | undefined) {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value ?? '-' : d.toLocaleDateString()
}

function daysDiffColor(days: number) {
  const abs = Math.abs(days)
  if (abs >= 90) return '#cf1322'
  if (abs >= 30) return '#fa8c16'
  return '#52c41a'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.user_type === 'ADMIN'
  const [urgentPageSize, setUrgentPageSize] = useState(10)

  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.getSummary,
  })

  const { data: latestSyncStats } = useQuery<LatestSyncStats>({
    queryKey: ['dashboard', 'latest-sync-stats'],
    queryFn: dashboardApi.getLatestSyncStats,
  })

  const { data: revisionTree } = useQuery<OrdinanceRevisionTree>({
    queryKey: ['dashboard', 'ordinance-revision-tree'],
    queryFn: dashboardApi.getOrdinanceRevisionTree,
  })

  const { data: revisionNeeded, isLoading: revisionLoading } = useQuery({
    queryKey: ['dashboard', 'revision-needed', urgentPageSize],
    queryFn: () => dashboardApi.getRevisionNeeded({ limit: urgentPageSize }),
  })

  const { data: deptStats } = useQuery<DepartmentInputStatsResponse>({
    queryKey: ['dashboard', 'dept-stats'],
    queryFn: departmentApi.getInputStatistics,
  })

  const { data: lawChangeStats } = useQuery<LawChangeStatsResponse>({
    queryKey: ['dashboard', 'law-change-stats'],
    queryFn: () => lawChangesApi.getStats(),
  })

  const { data: batchJobs } = useQuery<BatchJob[]>({
    queryKey: ['dashboard', 'batch-jobs'],
    queryFn: batchApi.getJobs,
  })

  const { data: aiAnalytics } = useQuery<AiAnalyticsData>({
    queryKey: ['dashboard', 'ai-analytics'],
    queryFn: () => adminApi.getAiAnalytics(),
    enabled: isAdmin,
  })

  // ==== Funnel data ====
  const funnelData = useMemo(() => {
    const total = revisionTree?.total_count ?? 0
    const target = (revisionTree?.total_count ?? 0) - (revisionTree?.no_revision_count ?? 0)
    const needs = revisionTree?.needs_revision_count ?? 0
    const underReview = revisionNeeded?.items?.filter((i) => i.revision_status === '검토중').length ?? 0
    const completed = revisionNeeded?.completed_count ?? 0
    return [
      { stage: '전체 조례', value: total },
      { stage: '검토 대상', value: target },
      { stage: '개정 필요', value: needs },
      { stage: '검토중', value: underReview },
      { stage: '개정 완료', value: completed },
    ]
  }, [revisionTree, revisionNeeded])

  // ==== Donut data: revision type distribution ====
  const revisionTypeData = useMemo(() => {
    if (!revisionTree?.by_revision_type) return []
    return revisionTree.by_revision_type.map((t) => ({
      type: t.revision_type,
      value: t.count,
    }))
  }, [revisionTree])

  // ==== Department stacked bar ====
  const deptBarData = useMemo(() => {
    if (!deptStats?.departments) return []
    const top = [...deptStats.departments]
      .sort((a, b) => b.ordinances_without_laws - a.ordinances_without_laws || b.total_ordinances - a.total_ordinances)
      .slice(0, 10)
    const rows: Array<{ department: string; category: string; count: number }> = []
    top.forEach((d) => {
      rows.push({ department: d.name, category: '상위법령 미매핑', count: d.ordinances_without_laws })
      rows.push({ department: d.name, category: '매핑 완료', count: d.ordinances_with_laws })
    })
    return rows
  }, [deptStats])

  // ==== Law change trend (by api_status) ====
  const apiStatusData = useMemo(() => {
    if (!lawChangeStats?.by_api_status) return []
    const labels: Record<string, string> = {
      success: '변경 감지',
      no_change: '변경 없음',
      no_response: '응답 없음',
      not_found: '미발견',
      error: '오류',
    }
    return Object.entries(lawChangeStats.by_api_status).map(([k, v]) => ({
      status: labels[k] ?? k,
      count: v as number,
    }))
  }, [lawChangeStats])

  // ==== Urgent table ====
  const departmentFilters = useMemo(() => {
    const set = new Set<string>()
    revisionNeeded?.items?.forEach((i) => i.department && set.add(i.department))
    return Array.from(set).map((d) => ({ text: d, value: d }))
  }, [revisionNeeded?.items])

  const urgentColumns = [
    {
      title: '상태',
      dataIndex: 'revision_status',
      key: 'revision_status',
      width: 110,
      filters: [
        { text: '개정 필요', value: 'NEEDS_REVISION' },
        { text: '개정 완료', value: 'COMPLETED' },
        { text: '검토중', value: 'UNDER_REVIEW' },
        { text: '재검토중', value: 'RE_REVIEW' },
      ],
      onFilter: (value: Key | boolean, record: RevisionNeededItem) =>
        (record.revision_status as unknown as string) === String(value),
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
      title: '상위법령',
      dataIndex: 'law_name',
      key: 'law_name',
      ellipsis: true,
    },
    {
      title: '조례개정일',
      dataIndex: 'ordinance_revision_date',
      key: 'ordinance_revision_date',
      width: 120,
      render: (v: string | null) => formatDate(v),
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        toDateValue(a.ordinance_revision_date) - toDateValue(b.ordinance_revision_date),
    },
    {
      title: '법령공포일',
      dataIndex: 'law_proclaimed_date',
      key: 'law_proclaimed_date',
      width: 120,
      render: (v: string | null) => formatDate(v),
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        toDateValue(a.law_proclaimed_date) - toDateValue(b.law_proclaimed_date),
    },
    {
      title: '날짜차이',
      dataIndex: 'days_diff',
      key: 'days_diff',
      width: 110,
      sorter: (a: RevisionNeededItem, b: RevisionNeededItem) =>
        Math.abs(a.days_diff) - Math.abs(b.days_diff),
      defaultSortOrder: 'descend' as const,
      render: (v: number) => (
        <Tag color={daysDiffColor(v)} style={{ borderColor: 'transparent', color: '#fff' }}>
          {Math.abs(v)}일
        </Tag>
      ),
    },
    {
      title: '소관부서',
      dataIndex: 'department',
      key: 'department',
      width: 140,
      filters: departmentFilters,
      onFilter: (value: Key | boolean, record: RevisionNeededItem) =>
        record.department === String(value),
      render: (v: string | null) => v || '-',
    },
  ]

  // ==== Active batch jobs ====
  const activeBatches = useMemo(() => {
    if (!batchJobs) return []
    return batchJobs
      .filter((j) => j.current_step !== 'step5_report' || j.step5_status !== 'completed')
      .slice(0, 5)
  }, [batchJobs])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>현황</Title>
        {latestSyncStats?.sync_date && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            <SyncOutlined /> 마지막 동기화: {formatDate(latestSyncStats.sync_date)}
          </Text>
        )}
      </div>

      {/* ===== 1. KPI 밴드 ===== */}
      <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
        <Col xs={12} sm={8} lg={4}>
          <Card hoverable size="small" onClick={() => navigate('/ordinances')}>
            <Statistic
              title="자치법규"
              value={summary?.total_ordinances || 0}
              prefix={<FileTextOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card hoverable size="small" onClick={() => navigate('/laws')}>
            <Statistic
              title="상위법령"
              value={summary?.total_parent_laws || 0}
              prefix={<BookOutlined />}
              loading={summaryLoading}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card hoverable size="small" onClick={() => navigate('/amendments')}>
            <Statistic
              title="최근 감지 법령"
              value={latestSyncStats?.total_laws || 0}
              suffix="건"
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card
            hoverable
            size="small"
            onClick={() => navigate('/ordinances?needs_revision_filter=needs_revision')}
          >
            <Statistic
              title="개정 필요"
              value={revisionTree?.needs_revision_count || 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card hoverable size="small" onClick={() => navigate('/reviews')}>
            <Statistic
              title="승인 대기"
              value={summary?.pending_reviews || 0}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <Card hoverable size="small" onClick={() => navigate('/reviews')}>
            <Statistic
              title="개정 완료"
              value={summary?.revision_completed_count || 0}
              valueStyle={{ color: '#389e0d' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* ===== 2. 중단 2x2 그리드 ===== */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="개정검토 파이프라인" size="small">
            {funnelData.some((d) => d.value > 0) ? (
              <Column
                data={funnelData}
                xField="stage"
                yField="value"
                height={240}
                label={{ position: 'top' }}
                color={({ stage }: { stage: string }) => {
                  const map: Record<string, string> = {
                    '전체 조례': '#1677ff',
                    '검토 대상': '#69b1ff',
                    '개정 필요': '#cf1322',
                    '검토중': '#faad14',
                    '개정 완료': '#389e0d',
                  }
                  return map[stage] || '#1677ff'
                }}
                xAxis={{ label: { autoRotate: false } }}
                meta={{ value: { alias: '건수' } }}
              />
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title="상위법령 개정 유형 분포"
            size="small"
            extra={<Text type="secondary" style={{ fontSize: 12 }}>개정대상 {revisionTree?.needs_revision_count ?? 0}건</Text>}
          >
            {revisionTypeData.length ? (
              <Pie
                data={revisionTypeData}
                angleField="value"
                colorField="type"
                radius={0.85}
                innerRadius={0.55}
                height={240}
                legend={{ position: 'right' }}
                label={{
                  type: 'inner',
                  offset: '-35%',
                  content: ({ value }: { value: number }) => (value > 0 ? `${value}` : ''),
                  style: { fontSize: 12, fill: '#fff' },
                }}
                statistic={{
                  title: { content: '합계', style: { fontSize: '12px' } },
                  content: {
                    content: `${revisionTypeData.reduce((s, d) => s + d.value, 0)}건`,
                    style: { fontSize: '16px' },
                  },
                }}
              />
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title="부서별 상위법령 매핑 현황 (Top 10)"
            size="small"
            extra={
              deptStats ? (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  전체 매핑율 {deptStats.overall_progress_rate.toFixed(1)}%
                </Text>
              ) : null
            }
          >
            {deptBarData.length ? (
              <Bar
                data={deptBarData}
                xField="count"
                yField="department"
                seriesField="category"
                isStack
                height={260}
                color={['#ff7875', '#52c41a']}
                legend={{ position: 'top' }}
                label={{ position: 'middle', style: { fill: '#fff', fontSize: 11 } }}
              />
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title="법령 감지 상태 분포"
            size="small"
            extra={
              <Text type="secondary" style={{ fontSize: 12 }}>
                누적 {lawChangeStats?.total ?? 0}건
              </Text>
            }
          >
            {apiStatusData.length ? (
              <Column
                data={apiStatusData}
                xField="status"
                yField="count"
                height={260}
                label={{ position: 'top' }}
                color={({ status }: { status: string }) => {
                  const map: Record<string, string> = {
                    '변경 감지': '#1677ff',
                    '변경 없음': '#8c8c8c',
                    '응답 없음': '#fa8c16',
                    '미발견': '#d9d9d9',
                    '오류': '#cf1322',
                  }
                  return map[status] || '#1677ff'
                }}
              />
            ) : (
              <Empty description="데이터 없음" />
            )}
          </Card>
        </Col>
      </Row>

      {/* ===== 3. 하단: 긴급 대상 + 배치 작업 ===== */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={14}>
          <Card
            size="small"
            title={
              <Space>
                <ExclamationCircleOutlined style={{ color: '#cf1322' }} />
                긴급 개정 대상 (날짜차이 큰 순)
              </Space>
            }
            extra={
              <Space>
                <Tag color="red">개정 필요 {revisionNeeded?.needs_revision_count || 0}</Tag>
                <Tag color="green">완료 {revisionNeeded?.completed_count || 0}</Tag>
              </Space>
            }
          >
            <Table<RevisionNeededItem>
              rowKey={(r) => `${r.ordinance_id}-${r.law_id}`}
              columns={urgentColumns}
              dataSource={revisionNeeded?.items || []}
              loading={revisionLoading}
              size="small"
              pagination={{
                pageSize: urgentPageSize,
                showSizeChanger: true,
                pageSizeOptions: ['10', '20', '50'],
                onChange: (_p, ps) => ps && ps !== urgentPageSize && setUrgentPageSize(ps),
              }}
              locale={{ emptyText: '데이터 없음' }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={
              <Space>
                <ThunderboltOutlined />
                진행 중 일괄 검토 작업
              </Space>
            }
            extra={
              <Link to="/admin/batch">
                <Text style={{ fontSize: 12 }}>전체 보기 →</Text>
              </Link>
            }
          >
            {activeBatches.length ? (
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {activeBatches.map((job) => {
                  const stepKeys = ['step1_select', 'step2_detect', 'step3_collect', 'step4_analyze', 'step5_report']
                  const statuses = [job.step1_status, job.step2_status, job.step3_status, job.step4_status, job.step5_status]
                  const currentIdx = stepKeys.indexOf(job.current_step)
                  const step = job.current_step
                  let percent = 0
                  if (step === 'step2_detect' && job.step2_total) {
                    percent = Math.round((job.step2_progress / job.step2_total) * 100)
                  } else if (step === 'step3_collect' && job.step3_total) {
                    percent = Math.round((job.step3_progress / job.step3_total) * 100)
                  } else if (step === 'step4_analyze' && job.step4_total) {
                    percent = Math.round((job.step4_progress / job.step4_total) * 100)
                  } else if (job.step5_status === 'completed') {
                    percent = 100
                  }
                  return (
                    <div
                      key={job.id}
                      style={{ cursor: 'pointer', padding: 8, border: '1px solid #f0f0f0', borderRadius: 6 }}
                      onClick={() => navigate(`/admin/batch/${job.id}`)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <Text strong style={{ fontSize: 13 }}>{job.name}</Text>
                        <Tag color={stepStatusColor[statuses[currentIdx >= 0 ? currentIdx : 0]] || 'default'}>
                          {stepLabels[job.current_step] || job.current_step}
                        </Tag>
                      </div>
                      <Progress percent={percent} size="small" status={statuses[currentIdx] === 'failed' ? 'exception' : undefined} />
                      <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                        {stepKeys.map((k, idx) => {
                          const s = statuses[idx]
                          const bg = s === 'completed' ? '#52c41a' : s === 'running' ? '#1677ff' : s === 'failed' ? '#cf1322' : '#f0f0f0'
                          return (
                            <div
                              key={k}
                              title={stepLabels[k]}
                              style={{ flex: 1, height: 4, borderRadius: 2, background: bg }}
                            />
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </Space>
            ) : (
              <Empty description="진행 중 작업 없음" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {isAdmin && aiAnalytics && aiAnalytics.total_analyses > 0 && (
            <Card
              size="small"
              style={{ marginTop: 16 }}
              title={
                <Space>
                  <ExperimentOutlined />
                  AI 분석 품질
                </Space>
              }
              extra={
                <Link to="/admin/ai-analytics">
                  <Text style={{ fontSize: 12 }}>상세 →</Text>
                </Link>
              }
            >
              <Row gutter={8}>
                <Col span={8}>
                  <Statistic
                    title="총 분석"
                    value={aiAnalytics.total_analyses}
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="초안 채택률"
                    value={(aiAnalytics.draft_adoption_rate * 100).toFixed(1)}
                    suffix="%"
                    valueStyle={{ fontSize: 18, color: '#389e0d' }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="성공률"
                    value={
                      aiAnalytics.total_analyses
                        ? ((aiAnalytics.success_count / aiAnalytics.total_analyses) * 100).toFixed(1)
                        : '0'
                    }
                    suffix="%"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
              </Row>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}
