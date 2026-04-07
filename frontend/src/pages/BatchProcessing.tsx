import { useState, useEffect, useCallback } from 'react'
import {
  Steps, Card, Button, Space, Typography, Table, Tag, Input, Select,
  Statistic, Row, Col, Progress, Modal, Form, message, Popconfirm,
  Tabs, Badge, Checkbox, Alert, Spin, Divider, Tooltip,
} from 'antd'
import {
  PlayCircleOutlined, DownloadOutlined, DeleteOutlined,
  ReloadOutlined, PlusOutlined,
  FileTextOutlined, LoadingOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { batchApi, ordinanceApi } from '../services/api'
import type { BatchJob, BatchJobItem, BatchStepCounts } from '../types/api'

const { Title, Text } = Typography

const finalResultColors: Record<string, string> = {
  '개정필요': 'red',
  '개정불필요': 'green',
  '해당없음': 'default',
  '수동확인필요': 'orange',
}

function getFinalColor(result: string | null) {
  if (!result) return 'default'
  for (const [key, color] of Object.entries(finalResultColors)) {
    if (result.includes(key)) return color
  }
  if (result.includes('오류')) return 'error'
  if (result.includes('제외')) return 'default'
  return 'default'
}

// ===== Main Component =====
export default function BatchProcessing() {
  const queryClient = useQueryClient()
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createForm] = Form.useForm()

  // Job list
  const { data: jobs, isLoading: jobsLoading } = useQuery<BatchJob[]>({
    queryKey: ['batch-jobs'],
    queryFn: () => batchApi.getJobs(),
  })

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: number) => batchApi.deleteJob(jobId),
    onSuccess: () => {
      message.success('삭제되었습니다')
      setSelectedJobId(null)
      queryClient.invalidateQueries({ queryKey: ['batch-jobs'] })
    },
  })

  // Department list for filter
  const { data: departments } = useQuery({
    queryKey: ['ordinance-departments'],
    queryFn: () => ordinanceApi.getDepartments(),
  })

  const todayLabel = (() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} 일괄 개정검토`
  })()

  const createJobMutation = useMutation({
    mutationFn: ({ name, filterParams }: { name: string; filterParams: Record<string, any> }) =>
      batchApi.createJob(name, filterParams),
    onSuccess: (data: BatchJob) => {
      message.success(`배치 작업 생성 완료 — 대상 조례가 선정되었습니다`)
      setSelectedJobId(data.id)
      setCreateModalOpen(false)
      createForm.resetFields()
      queryClient.invalidateQueries({ queryKey: ['batch-jobs'] })
    },
    onError: () => {
      message.error('배치 작업 생성에 실패했습니다')
    },
  })

  if (selectedJobId) {
    return (
      <BatchJobDetail
        jobId={selectedJobId}
        onBack={() => setSelectedJobId(null)}
      />
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>일괄 개정검토</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          새 작업 생성
        </Button>
      </div>

      <Table
        loading={jobsLoading}
        dataSource={jobs || []}
        rowKey="id"
        onRow={(record) => ({
          onClick: () => setSelectedJobId(record.id),
          style: { cursor: 'pointer' },
        })}
        columns={[
          { title: '작업명', dataIndex: 'name', key: 'name' },
          {
            title: '진행 단계', dataIndex: 'current_step', key: 'step',
            render: (step: string) => {
              const labels: Record<string, string> = {
                step1_select: '1. 대상 선정',
                step2_detect: '2. 개정 판별',
                step3_collect: '3. 데이터 수집',
                step4_analyze: '4. AI 분석',
                step5_report: '5. 보고서',
              }
              return labels[step] || step
            },
          },
          {
            title: '생성일', dataIndex: 'created_at', key: 'created_at',
            render: (v: string) => v ? new Date(v).toLocaleString() : '',
          },
          {
            title: '', key: 'action', width: 60,
            render: (_: any, record: BatchJob) => (
              <Popconfirm
                title="이 작업을 삭제하시겠습니까?"
                onConfirm={(e) => {
                  e?.stopPropagation()
                  deleteJobMutation.mutate(record.id)
                }}
                okText="삭제"
                cancelText="취소"
              >
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  size="small"
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            ),
          },
        ]}
      />

      {/* 새 작업 생성 모달 */}
      <Modal
        title="일괄 개정검토 작업 생성"
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => createForm.submit()}
        confirmLoading={createJobMutation.isPending}
        width={500}
      >
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{ name: todayLabel }}
          onValuesChange={(_, allValues) => {
            const parts = [todayLabel]
            if (allValues.category) parts.push(allValues.category)
            if (allValues.department) parts.push(allValues.department)
            if (allValues.search) parts.push(`"${allValues.search}"`)
            createForm.setFieldValue('name', parts.join(' '))
          }}
          onFinish={(values) => {
            const filterParams: Record<string, any> = {}
            if (values.category) filterParams.category = values.category
            if (values.department) filterParams.department = values.department
            if (values.search) filterParams.search = values.search

            // 최종 작업명: 필터 반영
            const parts = [todayLabel]
            if (values.category) parts.push(values.category)
            if (values.department) parts.push(values.department)
            if (values.search) parts.push(`"${values.search}"`)
            const finalName = parts.join(' ')

            createJobMutation.mutate({
              name: finalName,
              filterParams,
            })
          }}
        >
          <Divider style={{ margin: '12px 0' }}>필터 조건 (선택)</Divider>
          <Form.Item name="category" label="분류">
            <Select placeholder="전체" allowClear>
              <Select.Option value="조례">조례</Select.Option>
              <Select.Option value="규칙">규칙</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="department" label="소관부서">
            <Select placeholder="전체" allowClear showSearch>
              {(departments || []).map((d: any) => {
                const name = typeof d === 'string' ? d : d.name || d.department || String(d)
                return <Select.Option key={name} value={name}>{name}</Select.Option>
              })}
            </Select>
          </Form.Item>
          <Form.Item name="search" label="조례명 검색">
            <Input placeholder="예: 건축" />
          </Form.Item>
          <Divider style={{ margin: '12px 0' }} />
          <Form.Item
            name="name"
            label="작업명 (자동 생성)"
          >
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}


// ===== Batch Job Detail (Step Wizard) =====

function BatchJobDetail({ jobId, onBack }: { jobId: number; onBack: () => void }) {
  const { data: job, isLoading: jobLoading } = useQuery<BatchJob>({
    queryKey: ['batch-job', jobId],
    queryFn: () => batchApi.getJob(jobId),
    refetchInterval: 5000,
  })

  const { data: counts } = useQuery<BatchStepCounts>({
    queryKey: ['batch-counts', jobId],
    queryFn: () => batchApi.getCounts(jobId),
    refetchInterval: 5000,
  })

  const stepIndex = (() => {
    if (!job) return 0
    const map: Record<string, number> = {
      step1_select: 0,
      step2_detect: 1,
      step3_collect: 2,
      step4_analyze: 3,
      step5_report: 4,
    }
    return map[job.current_step] ?? 0
  })()

  const [activeTab, setActiveTab] = useState('0')

  useEffect(() => {
    setActiveTab(String(stepIndex))
  }, [stepIndex])

  if (jobLoading || !job) {
    return <Spin size="large" />
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button onClick={onBack}>목록</Button>
          <Title level={4} style={{ margin: 0 }}>{job.name}</Title>
        </Space>
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => batchApi.exportExcel(jobId)}
            disabled={!job.summary}
          >
            Excel 다운로드
          </Button>
        </Space>
      </div>

      {/* Progress Overview */}
      {counts && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic title="전체" value={counts.total} suffix="건" />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Step1 대상"
                value={counts.step1.included || 0}
                suffix="건"
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Step2 개정대상"
                value={counts.step2.needs_revision || 0}
                suffix="건"
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="Step3 확보"
                value={counts.step3.collected || 0}
                suffix="건"
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="개정필요"
                value={counts.final['개정필요'] || 0}
                suffix="건"
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="개정불필요"
                value={counts.final['개정불필요'] || 0}
                suffix="건"
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Steps
        current={stepIndex}
        style={{ marginBottom: 24 }}
        onChange={(idx) => setActiveTab(String(idx))}
        items={[
          {
            title: 'Step 1',
            description: '대상 선정',
            status: job.step1_status === 'completed' ? 'finish' : 'process',
          },
          {
            title: 'Step 2',
            description: '개정 판별',
            status: job.step2_status === 'completed' ? 'finish' : job.step2_status === 'running' ? 'process' : 'wait',
          },
          {
            title: 'Step 3',
            description: '데이터 수집',
            status: job.step3_status === 'completed' ? 'finish' : job.step3_status === 'running' ? 'process' : 'wait',
          },
          {
            title: 'Step 4',
            description: 'AI 분석',
            status: job.step4_status === 'completed' ? 'finish' : job.step4_status === 'running' ? 'process' : 'wait',
          },
          {
            title: 'Step 5',
            description: '보고서',
            status: job.step5_status === 'completed' ? 'finish' : 'wait',
          },
        ]}
      />

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: '0', label: 'Step 1: 대상 선정', children: <Step1Panel jobId={jobId} job={job} counts={counts} /> },
          { key: '1', label: 'Step 2: 개정 판별', children: <Step2Panel jobId={jobId} job={job} counts={counts} /> },
          { key: '2', label: 'Step 3: 데이터 수집', children: <Step3Panel jobId={jobId} job={job} counts={counts} /> },
          { key: '3', label: 'Step 4: AI 분석', children: <Step4Panel jobId={jobId} job={job} counts={counts} /> },
          { key: '4', label: 'Step 5: 보고서', children: <Step5Panel jobId={jobId} job={job} /> },
        ]}
      />
    </div>
  )
}


// ===== Step Panels =====

function Step1Panel({ jobId, job, counts }: { jobId: number; job: BatchJob; counts?: BatchStepCounts }) {
  const [tabKey, setTabKey] = useState('included')

  return (
    <div>
      <Alert
        type="info"
        message="등록된 자치법규 중 검토 대상을 선정합니다. 상위법령이 매핑된 조례/규칙이 자동으로 포함됩니다."
        style={{ marginBottom: 16 }}
      />

      <Tabs activeKey={tabKey} onChange={setTabKey} items={[
        {
          key: 'included',
          label: <Badge count={counts?.step1.included || 0} color="green" overflowCount={9999}><span style={{ padding: '0 8px' }}>대상</span></Badge>,
          children: <StepItemsTable jobId={jobId} stepFilter="step1" resultFilter="included" showToggle />,
        },
        {
          key: 'excluded',
          label: <Badge count={counts?.step1.excluded || 0} color="default" overflowCount={9999}><span style={{ padding: '0 8px' }}>제외</span></Badge>,
          children: <StepItemsTable jobId={jobId} stepFilter="step1" resultFilter="excluded" showReason />,
        },
      ]} />
    </div>
  )
}


function StepExecutionPanel({
  jobId, job, step, stepNum, counts,
  passLabel, failLabel,
  passKey, failKey,
}: {
  jobId: number; job: BatchJob; step: string; stepNum: 2 | 3 | 4
  counts?: BatchStepCounts
  passLabel: string; failLabel: string
  passKey: string; failKey: string
}) {
  const queryClient = useQueryClient()
  const [running, setRunning] = useState(false)
  const [tabKey, setTabKey] = useState(passKey)

  const stepStatus = job[`step${stepNum}_status` as keyof BatchJob] as string
  const stepProgress = job[`step${stepNum}_progress` as keyof BatchJob] as number
  const stepTotal = job[`step${stepNum}_total` as keyof BatchJob] as number

  // DB에서 running인데 프론트에서 running이 아니면 = 이전 실행이 중단된 것
  const isStuck = stepStatus === 'running' && !running

  const stepCounts = counts ? counts[`step${stepNum}` as keyof BatchStepCounts] as Record<string, number> : {}

  const runStep = useCallback(async () => {
    setRunning(true)
    try {
      const token = localStorage.getItem('law_matcher_token')
      const resp = await fetch(`/api/v1/batch/${jobId}/step${stepNum}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && !token.startsWith('simple_') ? { Authorization: `Bearer ${token}` } : {}),
        },
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      if (reader) {
        // 주기적으로 쿼리 갱신 (5초마다)
        const refreshInterval = setInterval(() => {
          queryClient.invalidateQueries({ queryKey: ['batch-job', jobId] })
          queryClient.invalidateQueries({ queryKey: ['batch-counts', jobId] })
        }, 5000)
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            const text = decoder.decode(value, { stream: true })
            if (text.includes('"done"') || text.includes('"error"')) {
              break
            }
          }
        } finally {
          clearInterval(refreshInterval)
        }
      }

      message.success(`Step ${stepNum} 완료`)
    } catch (e: any) {
      message.error(`Step ${stepNum} 실행 중단 — 처리된 건까지는 저장되었습니다. 재실행하세요.`)
    } finally {
      setRunning(false)
      queryClient.invalidateQueries({ queryKey: ['batch-job', jobId] })
      queryClient.invalidateQueries({ queryKey: ['batch-counts', jobId] })
      queryClient.invalidateQueries({ queryKey: ['batch-items', jobId] })
    }
  }, [jobId, stepNum, queryClient])

  const retryMutation = useMutation({
    mutationFn: () => batchApi.retry(jobId, step),
    onSuccess: (data: any) => {
      message.success(`${data.count}건 초기화 완료`)
      queryClient.invalidateQueries({ queryKey: ['batch-counts', jobId] })
    },
  })

  const isRunning = running

  return (
    <div>
      {isStuck && (
        <Alert
          type="warning"
          message={`이전 실행이 중단되었습니다 (${stepProgress}/${stepTotal}). 재실행하면 나머지 건을 이어서 처리합니다.`}
          style={{ marginBottom: 12 }}
          showIcon
        />
      )}
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={isRunning ? <LoadingOutlined /> : <PlayCircleOutlined />}
          onClick={runStep}
          loading={isRunning}
          disabled={isRunning}
        >
          {isRunning ? `실행 중 (${stepProgress}/${stepTotal})` : isStuck ? `Step ${stepNum} 재실행` : `Step ${stepNum} 실행`}
        </Button>
        {(stepCounts['error'] || 0) > 0 && (
          <Button
            icon={<ReloadOutlined />}
            onClick={() => retryMutation.mutate()}
            loading={retryMutation.isPending}
          >
            오류 {stepCounts['error']}건 재시도
          </Button>
        )}
      </Space>

      {isRunning && stepTotal > 0 && (
        <Progress
          percent={Math.round((stepProgress / stepTotal) * 100)}
          status="active"
          style={{ marginBottom: 16 }}
          format={() => `${stepProgress}/${stepTotal}`}
        />
      )}

      <Tabs activeKey={tabKey} onChange={setTabKey} items={[
        {
          key: passKey,
          label: <Badge count={stepCounts[passKey] || 0} color="red" overflowCount={9999}><span style={{ padding: '0 8px' }}>{passLabel}</span></Badge>,
          children: <StepItemsTable jobId={jobId} stepFilter={step} resultFilter={passKey} showReason showToggle />,
        },
        {
          key: failKey,
          label: <Badge count={stepCounts[failKey] || 0} color="green" overflowCount={9999}><span style={{ padding: '0 8px' }}>{failLabel}</span></Badge>,
          children: <StepItemsTable jobId={jobId} stepFilter={step} resultFilter={failKey} showReason />,
        },
        {
          key: 'error',
          label: <Badge count={stepCounts.error || 0} color="orange" overflowCount={9999}><span style={{ padding: '0 8px' }}>오류</span></Badge>,
          children: <StepItemsTable jobId={jobId} stepFilter={step} resultFilter="error" showReason />,
        },
      ]} />
    </div>
  )
}

function Step2Panel({ jobId, job, counts }: { jobId: number; job: BatchJob; counts?: BatchStepCounts }) {
  return (
    <div>
      <Alert
        type="info"
        message="상위법령의 최근 개정 여부를 확인하여, 조례 개정이 필요한 대상을 판별합니다."
        style={{ marginBottom: 16 }}
      />
      <StepExecutionPanel
        jobId={jobId} job={job} step="step2" stepNum={2} counts={counts}
        passLabel="개정대상" failLabel="해당없음"
        passKey="needs_revision" failKey="no_revision"
      />
    </div>
  )
}

function Step3Panel({ jobId, job, counts }: { jobId: number; job: BatchJob; counts?: BatchStepCounts }) {
  return (
    <div>
      <Alert
        type="info"
        message="개정 대상 법령의 제·개정이유, 개정문 등 AI 분석에 필요한 데이터를 법제처에서 수집합니다."
        style={{ marginBottom: 16 }}
      />
      <StepExecutionPanel
        jobId={jobId} job={job} step="step3" stepNum={3} counts={counts}
        passLabel="데이터확보" failLabel="데이터없음"
        passKey="collected" failKey="no_data"
      />
    </div>
  )
}

function Step4Panel({ jobId, job, counts }: { jobId: number; job: BatchJob; counts?: BatchStepCounts }) {
  return (
    <div>
      <Alert
        type="info"
        message="수집된 데이터를 바탕으로 AI가 조례별 개정 필요성을 분석하고, 영향받는 조문과 검토 의견을 생성합니다."
        style={{ marginBottom: 16 }}
      />
      <StepExecutionPanel
        jobId={jobId} job={job} step="step4" stepNum={4} counts={counts}
        passLabel="개정필요" failLabel="개정불필요"
        passKey="needs_revision" failKey="no_revision"
      />
    </div>
  )
}

function Step5Panel({ jobId, job }: { jobId: number; job: BatchJob }) {
  const queryClient = useQueryClient()
  const [reportData, setReportData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const generateReport = async () => {
    setLoading(true)
    try {
      const data = await batchApi.getReport(jobId)
      setReportData(data)
      queryClient.invalidateQueries({ queryKey: ['batch-job', jobId] })
      message.success('보고서 생성 완료')
    } catch {
      message.error('보고서 생성 실패')
    } finally {
      setLoading(false)
    }
  }

  const summary = reportData?.summary || job.summary

  return (
    <div>
      <Alert
        type="info"
        message="전체 분석 결과를 종합하여 보고서를 생성하고, Excel·Word·PDF 형식으로 다운로드할 수 있습니다."
        style={{ marginBottom: 16 }}
      />
      <Space style={{ marginBottom: 16 }}>
        <Tooltip title="각 단계의 분석 결과를 집계하여 보고서 데이터를 생성합니다. 이미 생성된 경우 최신 데이터로 갱신됩니다.">
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            onClick={generateReport}
            loading={loading}
          >
            보고서 생성
          </Button>
        </Tooltip>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => batchApi.exportExcel(jobId)}
          disabled={!summary}
        >
          Excel 다운로드
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => batchApi.exportDocx(jobId)}
          disabled={!summary}
        >
          Word 다운로드
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => batchApi.exportPdf(jobId)}
          disabled={!summary}
        >
          PDF 다운로드
        </Button>
      </Space>

      {summary && (
        <>
          <Card title="파이프라인 요약" style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col span={4}><Statistic title="전체 조례" value={summary.total_ordinances} suffix="건" /></Col>
              <Col span={4}><Statistic title="Step1 대상" value={summary.pipeline?.step1_included} suffix="건" /></Col>
              <Col span={4}><Statistic title="Step2 개정대상" value={summary.pipeline?.step2_needs_revision} suffix="건" valueStyle={{ color: '#cf1322' }} /></Col>
              <Col span={4}><Statistic title="Step3 확보" value={summary.pipeline?.step3_collected} suffix="건" /></Col>
              <Col span={4}><Statistic title="개정필요" value={summary.pipeline?.step4_needs_revision} suffix="건" valueStyle={{ color: '#cf1322' }} /></Col>
              <Col span={4}><Statistic title="개정불필요" value={summary.pipeline?.step4_no_revision} suffix="건" valueStyle={{ color: '#3f8600' }} /></Col>
            </Row>
          </Card>

          <Card title="부서별 집계" style={{ marginBottom: 16 }}>
            <Table
              size="small"
              pagination={false}
              dataSource={Object.entries(summary.by_department || {}).map(([dept, stats]: [string, any]) => ({
                key: dept,
                department: dept,
                ...stats,
              }))}
              columns={[
                { title: '부서', dataIndex: 'department', key: 'department' },
                { title: '전체', dataIndex: 'total', key: 'total' },
                {
                  title: '개정필요', dataIndex: 'needs_revision', key: 'needs_revision',
                  render: (v: number) => v > 0 ? <Text type="danger">{v}</Text> : v,
                },
                { title: '개정불필요', dataIndex: 'no_revision', key: 'no_revision' },
                { title: '제외', dataIndex: 'excluded', key: 'excluded' },
                { title: '오류', dataIndex: 'error', key: 'error' },
              ]}
            />
          </Card>

          {/* 개정필요 상세 목록 */}
          {reportData?.items && (
            <Card title="개정필요 조례 목록">
              <Table
                size="small"
                dataSource={reportData.items.filter((i: any) => i.final_result === '개정필요')}
                rowKey="ordinance_id"
                columns={[
                  { title: '조례명', dataIndex: 'ordinance_name', key: 'name', ellipsis: true },
                  { title: '소관부서', dataIndex: 'department', key: 'dept', width: 120 },
                  { title: '분류', dataIndex: 'category', key: 'cat', width: 80 },
                  {
                    title: 'AI 분석 요약', dataIndex: 'ai_summary', key: 'summary',
                    ellipsis: true,
                    render: (v: string) => v ? <Text style={{ fontSize: 12 }}>{v.substring(0, 200)}...</Text> : '-',
                  },
                ]}
                expandable={{
                  expandedRowRender: (record: any) => (
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
                      {record.ai_summary || '분석 요약 없음'}
                    </div>
                  ),
                }}
              />
            </Card>
          )}
        </>
      )}
    </div>
  )
}


// ===== Detail Popup =====

function ItemDetailModal({
  open, onClose, jobId, itemId, mode,
}: {
  open: boolean; onClose: () => void
  jobId: number; itemId: number | null
  mode: 'collect' | 'analyze'
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['batch-item-detail', jobId, itemId],
    queryFn: () => batchApi.getItemDetail(jobId, itemId!),
    enabled: open && !!itemId,
  })

  return (
    <Modal
      title={mode === 'collect' ? '수집내용 (제개정이유 / 개정문)' : 'AI 분석결과'}
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
      destroyOnClose
    >
      {isLoading ? <Spin /> : (
        <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
          {data?.item && (
            <div style={{ marginBottom: 12, color: '#666', fontSize: 13 }}>
              <strong>{data.item.ordinance_name}</strong>
              <span style={{ marginLeft: 8 }}>{data.item.ordinance_department}</span>
            </div>
          )}

          {mode === 'collect' && (
            <>
              {(data?.revision_reasons || []).length === 0 && (
                <div style={{ color: '#999', textAlign: 'center', padding: 24 }}>수집된 데이터가 없습니다.</div>
              )}
              {(data?.revision_reasons || []).map((rr: any, idx: number) => (
                <Card key={idx} size="small" title={rr.law_name} style={{ marginBottom: 12 }}>
                  {rr.revision_reason && (
                    <>
                      <Text strong>제개정이유</Text>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, marginBottom: 12, marginTop: 4, background: '#fafafa', padding: 8, borderRadius: 4 }}>
                        {rr.revision_reason}
                      </div>
                    </>
                  )}
                  {rr.amendment_content && (
                    <>
                      <Text strong>개정문</Text>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, marginTop: 4, background: '#fafafa', padding: 8, borderRadius: 4 }}>
                        {rr.amendment_content}
                      </div>
                    </>
                  )}
                  {rr.extracted_articles?.articles && (
                    <div style={{ marginTop: 8 }}>
                      <Text strong>추출 조문: </Text>
                      {rr.extracted_articles.articles.map((a: string, i: number) => (
                        <Tag key={i} style={{ marginTop: 4 }}>{a}</Tag>
                      ))}
                    </div>
                  )}
                  {rr.fetched_at && (
                    <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                      수집일: {new Date(rr.fetched_at).toLocaleString()}
                    </div>
                  )}
                </Card>
              ))}
            </>
          )}

          {mode === 'analyze' && (
            <>
              {(data?.ai_results || []).length === 0 && (
                <div style={{ color: '#999', textAlign: 'center', padding: 24 }}>AI 분석 결과가 없습니다.</div>
              )}
              {(data?.ai_results || []).map((ai: any, idx: number) => (
                <Card
                  key={idx} size="small"
                  title={
                    <Space>
                      <span>{ai.law_name}</span>
                      {ai.review_draft_result && (
                        <Tag color={ai.review_draft_result === '개정필요' ? 'red' : 'green'}>
                          {ai.review_draft_result}
                        </Tag>
                      )}
                      <Tag color="purple">{ai.provider_name} ({ai.model_name})</Tag>
                    </Space>
                  }
                  style={{ marginBottom: 12 }}
                >
                  {ai.summary_text && (
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, marginBottom: 12 }}>
                      {ai.summary_text}
                    </div>
                  )}
                  {ai.affected_articles_json && ai.affected_articles_json.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <Text strong>영향받는 조례 조문</Text>
                      {ai.affected_articles_json.map((art: any, i: number) => (
                        <Card key={i} size="small" style={{ marginTop: 4, background: '#fafafa' }}>
                          <div><strong>{art.article_no}</strong> {art.article_title || ''}</div>
                          {art.current_content_summary && <div style={{ fontSize: 12, color: '#666' }}>현행: {art.current_content_summary}</div>}
                          {art.issue && <div style={{ fontSize: 12, color: '#cf1322' }}>문제: {art.issue}</div>}
                          {art.recommendation && <div style={{ fontSize: 12, color: '#1677ff' }}>권고: {art.recommendation}</div>}
                        </Card>
                      ))}
                    </div>
                  )}
                  {ai.review_draft_text && (
                    <>
                      <Text strong>검토의견 초안</Text>
                      <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, marginTop: 4, background: '#f6ffed', padding: 8, borderRadius: 4 }}>
                        {ai.review_draft_text}
                      </div>
                    </>
                  )}
                  {ai.created_at && (
                    <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                      생성일: {new Date(ai.created_at).toLocaleString()}
                    </div>
                  )}
                </Card>
              ))}
            </>
          )}
        </div>
      )}
    </Modal>
  )
}


// ===== Reusable Items Table =====

function StepItemsTable({
  jobId, stepFilter, resultFilter, showReason, showToggle,
}: {
  jobId: number
  stepFilter?: string
  resultFilter?: string
  showReason?: boolean
  showToggle?: boolean
}) {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [detailModal, setDetailModal] = useState<{
    open: boolean; itemId: number | null; mode: 'collect' | 'analyze'
  }>({ open: false, itemId: null, mode: 'collect' })

  const { data, isLoading } = useQuery({
    queryKey: ['batch-items', jobId, stepFilter, resultFilter, page],
    queryFn: () => batchApi.getItems(jobId, {
      step_filter: stepFilter,
      result_filter: resultFilter,
      page,
      size: 50,
    }),
  })

  const toggleMutation = useMutation({
    mutationFn: (itemId: number) => batchApi.toggleExclude(jobId, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch-items', jobId] })
      queryClient.invalidateQueries({ queryKey: ['batch-counts', jobId] })
    },
  })

  const columns: any[] = [
    {
      title: '조례명', dataIndex: 'ordinance_name', key: 'name',
      ellipsis: true, width: 250,
    },
    { title: '소관부서', dataIndex: 'ordinance_department', key: 'dept', width: 110, ellipsis: true },
    { title: '분류', dataIndex: 'ordinance_category', key: 'cat', width: 60 },
  ]

  if (showReason) {
    const reasonField = stepFilter ? `${stepFilter}_reason` : 'step1_reason'
    columns.push({
      title: '사유', dataIndex: reasonField, key: 'reason',
      ellipsis: true,
      render: (v: string | null) => v || '-',
    })
  }

  // 수집내용 버튼 (step3)
  if (stepFilter === 'step3') {
    columns.push({
      title: '수집내용', key: 'collect_detail', width: 80,
      render: (_: any, record: BatchJobItem) => (
        <Button
          type="link"
          size="small"
          onClick={() => setDetailModal({ open: true, itemId: record.id, mode: 'collect' })}
        >
          보기
        </Button>
      ),
    })
  }

  // AI 분석결과 버튼 (step4)
  if (stepFilter === 'step4') {
    columns.push({
      title: 'AI 판정', dataIndex: 'step4_ai_result', key: 'ai_result', width: 90,
      render: (v: string | null) => v ? <Tag color={v === '개정필요' ? 'red' : 'green'}>{v}</Tag> : '-',
    })
    columns.push({
      title: '분석내용', key: 'analyze_detail', width: 80,
      render: (_: any, record: BatchJobItem) => (
        <Button
          type="link"
          size="small"
          onClick={() => setDetailModal({ open: true, itemId: record.id, mode: 'analyze' })}
        >
          보기
        </Button>
      ),
    })
  }

  columns.push({
    title: '최종결과', dataIndex: 'final_result', key: 'final', width: 100,
    render: (v: string | null) => v ? <Tag color={getFinalColor(v)}>{v}</Tag> : '-',
  })

  if (showToggle) {
    columns.push({
      title: '제외', key: 'exclude', width: 50,
      render: (_: any, record: BatchJobItem) => (
        <Checkbox
          checked={record.manually_excluded}
          onChange={() => toggleMutation.mutate(record.id)}
        />
      ),
    })
  }

  return (
    <>
      <Table
        loading={isLoading}
        dataSource={data?.items || []}
        rowKey="id"
        size="small"
        columns={columns}
        pagination={{
          current: page,
          pageSize: 50,
          total: data?.total || 0,
          onChange: setPage,
          showTotal: (total: number) => `총 ${total}건`,
          showSizeChanger: false,
        }}
        rowClassName={(record: BatchJobItem) =>
          record.manually_excluded ? 'ant-table-row-disabled' : ''
        }
      />
      <ItemDetailModal
        open={detailModal.open}
        onClose={() => setDetailModal({ open: false, itemId: null, mode: 'collect' })}
        jobId={jobId}
        itemId={detailModal.itemId}
        mode={detailModal.mode}
      />
    </>
  )
}
