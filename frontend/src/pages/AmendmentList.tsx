import { useState, useEffect, useRef } from 'react'
import {
  Table,
  Tag,
  Typography,
  Space,
  Select,
  Button,
  Modal,
  Progress,
  Card,
  Descriptions,
  Alert,
  Row,
  Col,
  Statistic,
} from 'antd'
import { SyncOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { amendmentApi, lawSearchApi, lawChangesApi } from '../services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography

interface SyncDate {
  sync_date: string
  total: number
  success: number
  pending: number
}

interface SyncProgress {
  type: string
  current?: number
  total?: number
  law_name?: string
  status?: string
  result?: string
  message?: string
  law?: any
  error?: string
  changed_count?: number
  updated?: number
  failed?: number
}

interface ChangedLaw {
  id: number
  law_id: number
  law_name: string
  law_type: string
  proclaimed_date: string | null
  enforced_date: string | null
  revision_type: string | null
  dept_name: string | null
  changes: Record<string, { old: string | null; new: string | null }>
  api_status?: 'success' | 'no_response' | 'not_found'
  api_message?: string
}

interface SyncResult {
  total: number
  updated: number
  failed: number
  changedCount: number
  changedLaws: ChangedLaw[]
}

export default function AmendmentList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [selectedSyncDate, setSelectedSyncDate] = useState<string>()
  const [apiStatusFilter, setApiStatusFilter] = useState<string>()

  // 동기화 모달 상태
  const [syncModalOpen, setSyncModalOpen] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)

  // content 영역에 표시할 변경된 법령 (모달 바깥)
  const [changedLaws, setChangedLaws] = useState<ChangedLaw[]>([])
  const [resultFilter, setResultFilter] = useState<string>('all')

  const eventSourceRef = useRef<EventSource | null>(null)

  // 동기화 날짜 목록 조회
  const { data: syncDates } = useQuery({
    queryKey: ['law-changes-sync-dates'],
    queryFn: () => lawChangesApi.getSyncDates(),
  })

  // 최초 로드 시 가장 최근 날짜 선택
  useEffect(() => {
    if (syncDates && syncDates.length > 0 && !selectedSyncDate) {
      setSelectedSyncDate(syncDates[0].sync_date)
    }
  }, [syncDates, selectedSyncDate])

  // 선택된 날짜의 데이터 조회
  const { data, isLoading } = useQuery({
    queryKey: ['law-changes', page, selectedSyncDate, apiStatusFilter],
    queryFn: () =>
      lawChangesApi.getList({
        page,
        size: 20,
        sync_date: selectedSyncDate,
        api_status: apiStatusFilter,
      }),
    enabled: !!selectedSyncDate,
  })

  // 통계 조회
  const { data: stats } = useQuery({
    queryKey: ['law-changes-stats'],
    queryFn: () => lawChangesApi.getStats(),
  })

  // 기존 amendments 데이터 (조례 연계용)
  const { data: amendmentsData } = useQuery({
    queryKey: ['amendments'],
    queryFn: () => amendmentApi.getList({ page: 1, size: 100 }),
  })

  const analyzeMutation = useMutation({
    mutationFn: (id: number) => amendmentApi.analyze(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amendments'] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })

  const apiStatusConfig: Record<string, { color: string; text: string }> = {
    success: { color: 'green', text: '성공' },
    no_response: { color: 'red', text: '응답없음' },
    not_found: { color: 'orange', text: '미발견' },
  }

  const fieldNames: Record<string, string> = {
    proclaimed_date: '공포일',
    enforced_date: '시행일',
    revision_type: '제개정구분',
    law_id: '법령ID',
    dept_name: '소관부처',
  }

  // 동기화 시작
  const handleStartSync = () => {
    setSyncModalOpen(true)
    setSyncing(true)
    setProgress(null)
    setLogs([])
    setSyncResult(null)
    setChangedLaws([])  // content 영역 초기화

    const eventSource = lawSearchApi.syncLawsStream()
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'start':
            setLogs((prev) => [...prev, data.message])
            break

          case 'progress':
            setProgress({
              type: data.type,
              current: data.current,
              total: data.total,
              law_name: data.law_name,
              status: data.status,
              result: data.result,
            })
            // 비교 완료 시에만 로그 추가 (너무 많은 로그 방지)
            if (data.status === 'compared') {
              setLogs((prev) => {
                const newLogs = [...prev, data.message]
                // 최근 50개만 유지
                return newLogs.slice(-50)
              })
            }
            break

          case 'changed':
            // content 영역에 변경된 법령 추가
            setChangedLaws((prev) => [...prev, data.law])
            setLogs((prev) => [...prev.slice(-49), `[변경] ${data.law.law_name}`])
            break

          case 'error':
            setLogs((prev) => [...prev, `[오류] ${data.message}`])
            break

          case 'complete':
            setSyncing(false)
            setSyncResult({
              total: data.total,
              updated: data.updated,
              failed: data.failed,
              changedCount: data.changed_count,
              changedLaws: data.changed_laws,
            })
            setLogs((prev) => [...prev, data.message])
            eventSource.close()
            // 데이터 새로고침
            queryClient.invalidateQueries({ queryKey: ['amendments'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-sync-dates'] })
            break
        }
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    eventSource.onerror = () => {
      setSyncing(false)
      setLogs((prev) => [...prev, '[오류] 연결이 끊어졌습니다.'])
      eventSource.close()
    }
  }

  const handleCloseModal = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }
    setSyncModalOpen(false)
    setSyncing(false)
  }

  // 테이블용 간결한 변경내용 렌더링
  const renderChangeValuesCompact = (oldValues: Record<string, any> | null, newValues: Record<string, any> | null) => {
    if (!oldValues && !newValues) return <Text type="secondary">변경 없음</Text>

    const changedFields: string[] = []
    const fields = new Set([
      ...Object.keys(oldValues || {}),
      ...Object.keys(newValues || {}),
    ])

    fields.forEach((field) => {
      const oldVal = oldValues?.[field]
      const newVal = newValues?.[field]
      if (oldVal !== newVal) {
        changedFields.push(field)
      }
    })

    if (changedFields.length === 0) return <Text type="secondary">변경 없음</Text>

    return (
      <div style={{ fontSize: 12 }}>
        {changedFields.map((field) => {
          const oldVal = oldValues?.[field]
          const newVal = newValues?.[field]
          return (
            <div key={field} style={{ marginBottom: 2 }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{fieldNames[field] || field}: </Text>
              <Text delete style={{ fontSize: 11, color: '#ff4d4f' }}>{oldVal || '(없음)'}</Text>
              <Text style={{ fontSize: 11 }}> → </Text>
              <Text strong style={{ fontSize: 11, color: '#52c41a' }}>{newVal || '(없음)'}</Text>
            </div>
          )
        })}
      </div>
    )
  }

  // 법령 변경 테이블 컬럼
  const columns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      width: 250,
    },
    {
      title: 'API 상태',
      dataIndex: 'api_status',
      key: 'api_status',
      width: 100,
      render: (status: string) => {
        const config = apiStatusConfig[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '소관부처',
      dataIndex: 'dept_name',
      key: 'dept_name',
      width: 120,
      render: (dept: string) => dept || '-',
    },
    {
      title: '변경내용',
      key: 'changes',
      width: 280,
      render: (_: any, record: any) => {
        if (record.api_status !== 'success') {
          return <Text type="secondary">{record.api_message || '-'}</Text>
        }
        return renderChangeValuesCompact(record.old_values, record.new_values)
      },
    },
    {
      title: '동기화일시',
      dataIndex: 'sync_date',
      key: 'sync_date',
      width: 150,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '작업',
      key: 'action',
      width: 120,
      render: (_: any, record: any) => {
        // 해당 법령과 연계된 조례가 있는지 확인
        const hasLinkedOrdinance = amendmentsData?.items?.some(
          (a: any) => a.law_name === record.law_name && !a.processed
        )
        return (
          <Button
            size="small"
            disabled={!hasLinkedOrdinance || record.api_status !== 'success'}
            loading={analyzeMutation.isPending}
            onClick={() => {
              const amendment = amendmentsData?.items?.find(
                (a: any) => a.law_name === record.law_name && !a.processed
              )
              if (amendment) {
                analyzeMutation.mutate(amendment.id)
              }
            }}
          >
            영향 분석
          </Button>
        )
      },
    },
  ]

  // content 영역 변경된 법령 테이블 컬럼
  const changedLawColumns = [
    {
      title: 'API 상태',
      dataIndex: 'api_status',
      key: 'api_status',
      width: 100,
      render: (status: string, record: ChangedLaw) => {
        const config = apiStatusConfig[status] || { color: 'default', text: status || '변경' }
        return (
          <Tag color={config.color} title={record.api_message}>
            {config.text}
          </Tag>
        )
      },
    },
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      width: 250,
    },
    {
      title: '법령유형',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 80,
    },
    {
      title: '소관부처',
      dataIndex: 'dept_name',
      key: 'dept_name',
      width: 120,
    },
    {
      title: '변경내용',
      key: 'changes',
      width: 350,
      render: (_: any, record: ChangedLaw) => {
        // API 실패인 경우 오류 메시지 표시
        if (record.api_status === 'no_response' || record.api_status === 'not_found') {
          return <Text type="danger">{record.api_message}</Text>
        }
        // 변경 내용 표시 (공포일, 시행일, 제개정구분 신구비교)
        const changeItems = Object.entries(record.changes || {}).map(([field, change]) => {
          return (
            <div key={field} style={{ marginBottom: 2 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>{fieldNames[field] || field}: </Text>
              <Text delete style={{ fontSize: 12, color: '#ff4d4f' }}>{change.old || '(없음)'}</Text>
              <Text style={{ fontSize: 12 }}> → </Text>
              <Text strong style={{ fontSize: 12, color: '#52c41a' }}>{change.new || '(없음)'}</Text>
            </div>
          )
        })
        return <div>{changeItems.length > 0 ? changeItems : <Text type="secondary">변경 없음</Text>}</div>
      },
    },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'requesting':
        return <LoadingOutlined spin style={{ color: '#1890ff' }} />
      case 'received':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'compared':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      default:
        return null
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>법령 개정 목록</Title>
        <Button type="primary" icon={<SyncOutlined />} onClick={handleStartSync}>
          법령 동기화
        </Button>
      </div>

      {/* 통계 카드 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="전체 변경" value={stats.total} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="대기"
                value={stats.pending}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="승인됨"
                value={stats.approved}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="반려됨"
                value={stats.rejected}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 동기화 결과 - content 영역에 변경된 법령 표시 */}
      {changedLaws.length > 0 && (
        <Card
          title={
            <Space>
              <span>동기화 결과 ({changedLaws.length}건)</span>
              {syncResult && (
                <Tag color="blue">
                  전체 {syncResult.total}건 / 성공 {syncResult.updated}건 / 실패 {syncResult.failed}건
                </Tag>
              )}
            </Space>
          }
          style={{ marginBottom: 16 }}
          extra={
            <Space>
              <Select
                value={resultFilter}
                onChange={setResultFilter}
                style={{ width: 140 }}
                options={[
                  { value: 'all', label: '전체 보기' },
                  { value: 'failed', label: '실패만 보기' },
                  { value: 'changed', label: '변경만 보기' },
                ]}
              />
              <Button type="link" danger onClick={() => { setChangedLaws([]); setResultFilter('all'); }}>
                결과 지우기
              </Button>
            </Space>
          }
        >
          <Table
            dataSource={
              resultFilter === 'all'
                ? changedLaws
                : resultFilter === 'failed'
                ? changedLaws.filter((law) => law.api_status === 'no_response' || law.api_status === 'not_found')
                : changedLaws.filter((law) => law.api_status === 'success' && Object.keys(law.changes || {}).length > 0)
            }
            columns={changedLawColumns}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 1200 }}
          />
        </Card>
      )}

      {/* 필터 */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="동기화 날짜"
          style={{ width: 220 }}
          value={selectedSyncDate}
          onChange={(value) => {
            setSelectedSyncDate(value)
            setPage(1)
          }}
          options={syncDates?.map((d: SyncDate) => ({
            value: d.sync_date,
            label: `${d.sync_date} (${d.success}/${d.total}건)`,
          })) || []}
        />
        <Select
          placeholder="API 상태"
          style={{ width: 120 }}
          allowClear
          value={apiStatusFilter}
          onChange={(value) => {
            setApiStatusFilter(value)
            setPage(1)
          }}
          options={[
            { value: 'success', label: '성공' },
            { value: 'no_response', label: '응답없음' },
            { value: 'not_found', label: '미발견' },
          ]}
        />
      </Space>

      {/* 테이블 */}
      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          total: data?.total || 0,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `총 ${total}건`,
        }}
        scroll={{ x: 1100 }}
      />

      {/* 동기화 진행 모달 - 경과만 표시 */}
      <Modal
        title="법령 동기화"
        open={syncModalOpen}
        onCancel={handleCloseModal}
        footer={[
          <Button key="close" onClick={handleCloseModal} disabled={syncing}>
            닫기
          </Button>,
        ]}
        width={700}
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {/* 진행률 */}
        {progress && (
          <div style={{ marginBottom: 16 }}>
            <Progress
              percent={Math.round(((progress.current || 0) / (progress.total || 1)) * 100)}
              status={syncing ? 'active' : 'success'}
              format={() => `${progress.current} / ${progress.total}`}
            />
            <Space style={{ marginTop: 8 }}>
              {getStatusIcon(progress.status || '')}
              <Text>
                {progress.law_name}
                {progress.status === 'requesting' && ' - API 요청 중...'}
                {progress.status === 'received' && ' - 응답 수신'}
                {progress.status === 'compared' && ` - 비교 완료 (${progress.result})`}
              </Text>
            </Space>
          </div>
        )}

        {/* 완료 결과 */}
        {syncResult && (
          <Alert
            type={syncResult.changedCount > 0 ? 'warning' : 'success'}
            message="동기화 완료"
            description={
              <Descriptions column={2} size="small">
                <Descriptions.Item label="전체">{syncResult.total}건</Descriptions.Item>
                <Descriptions.Item label="성공">{syncResult.updated}건</Descriptions.Item>
                <Descriptions.Item label="실패">{syncResult.failed}건</Descriptions.Item>
                <Descriptions.Item label="변경 감지">{syncResult.changedCount}건</Descriptions.Item>
              </Descriptions>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 완료 시 안내 메시지 */}
        {syncResult && changedLaws.length > 0 && (
          <Alert
            type="info"
            message="변경된 법령 목록은 모달을 닫으면 페이지에서 확인할 수 있습니다."
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 로그 */}
        <Card title="진행 로그" size="small">
          <div
            style={{
              maxHeight: 300,
              overflow: 'auto',
              fontFamily: 'monospace',
              fontSize: 12,
              background: '#f5f5f5',
              padding: 8,
              borderRadius: 4,
            }}
          >
            {logs.map((log, idx) => (
              <div key={idx} style={{ color: log.includes('[오류]') ? 'red' : log.includes('[변경]') ? 'orange' : 'inherit' }}>
                {log}
              </div>
            ))}
            {syncing && <div><LoadingOutlined spin /> 진행 중...</div>}
          </div>
        </Card>
      </Modal>
    </div>
  )
}
