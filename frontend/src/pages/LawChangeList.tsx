import { useState, useEffect, useRef } from 'react'
import {
  Table,
  Tag,
  Typography,
  Space,
  Select,
  Button,
  Card,
  Statistic,
  Row,
  Col,
  Modal,
  Input,
  message,
  Descriptions,
  Timeline,
  Progress,
  List,
  Alert,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  SyncOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { lawChangesApi, lawSearchApi } from '../services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { TextArea } = Input

interface LawChange {
  id: number
  law_id: number
  law_name: string
  law_type: string | null
  sync_date: string
  sync_batch_id: string | null
  api_status: string
  api_message: string | null
  old_values: Record<string, any> | null
  new_values: Record<string, any> | null
  dept_name: string | null
  dept_code: number | null
  status: string
  processed_at: string | null
  processed_by: string | null
  process_note: string | null
  created_at: string
  updated_at: string
}

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

export default function LawChangeList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<string>()
  const [apiStatus, setApiStatus] = useState<string>()
  const [deptName, setDeptName] = useState<string>()
  const [search, setSearch] = useState<string>()
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [selectedSyncDate, setSelectedSyncDate] = useState<string>()

  // SSE 동기화 상태
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null)
  const [syncLogs, setSyncLogs] = useState<SyncProgress[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)
  const logContainerRef = useRef<HTMLDivElement>(null)

  // 상세 모달
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedChange, setSelectedChange] = useState<LawChange | null>(null)

  // 반려 모달
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectNote, setRejectNote] = useState('')
  const [rejectTargetId, setRejectTargetId] = useState<number | null>(null)

  // 일괄 반려 모달
  const [bulkRejectModalOpen, setBulkRejectModalOpen] = useState(false)
  const [bulkRejectNote, setBulkRejectNote] = useState('')

  // 연혁 모달
  const [historyModalOpen, setHistoryModalOpen] = useState(false)
  const [historyLawId, setHistoryLawId] = useState<number | null>(null)
  const [historyLawName, setHistoryLawName] = useState<string>('')

  // 동기화 날짜 목록 조회
  const { data: syncDates } = useQuery({
    queryKey: ['law-changes-sync-dates'],
    queryFn: () => lawChangesApi.getSyncDates(),
  })

  // 최초 로드 시 가장 최근 날짜 선택
  useEffect(() => {
    if (syncDates && syncDates.length > 0 && !selectedSyncDate && !isSyncing) {
      setSelectedSyncDate(syncDates[0].sync_date)
    }
  }, [syncDates, selectedSyncDate, isSyncing])

  // 데이터 조회 (날짜 필터 추가)
  const { data, isLoading } = useQuery({
    queryKey: ['law-changes', page, status, apiStatus, deptName, search, selectedSyncDate],
    queryFn: () =>
      lawChangesApi.getList({
        page,
        size: 20,
        status,
        api_status: apiStatus,
        dept_name: deptName,
        search,
        sync_date: selectedSyncDate,
      }),
    enabled: !isSyncing && !!selectedSyncDate,
  })

  // 통계 조회
  const { data: stats } = useQuery({
    queryKey: ['law-changes-stats'],
    queryFn: () => lawChangesApi.getStats(),
    enabled: !isSyncing,
  })

  // 부서 목록 조회
  const { data: departments } = useQuery({
    queryKey: ['law-changes-departments'],
    queryFn: () => lawChangesApi.getDepartments(),
  })

  // 연혁 조회
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['law-changes-history', historyLawId],
    queryFn: () => historyLawId ? lawChangesApi.getHistory(historyLawId, { size: 50 }) : null,
    enabled: !!historyLawId && historyModalOpen,
  })

  // 로그 스크롤 자동
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [syncLogs])

  // 동기화 시작
  const handleStartSync = () => {
    setIsSyncing(true)
    setSyncProgress(null)
    setSyncLogs([])
    setSelectedSyncDate(undefined)

    const eventSource = lawSearchApi.syncLawsStream()
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data: SyncProgress = JSON.parse(event.data)
        setSyncProgress(data)

        // 변경된 법령 또는 에러만 로그에 추가
        if (data.type === 'changed' || data.type === 'error' || data.type === 'start' || data.type === 'complete') {
          setSyncLogs((prev) => [...prev, data])
        }

        // 완료 시 처리
        if (data.type === 'complete') {
          eventSource.close()
          eventSourceRef.current = null
          setIsSyncing(false)
          message.success(data.message || '동기화가 완료되었습니다.')

          // 데이터 새로고침
          queryClient.invalidateQueries({ queryKey: ['law-changes'] })
          queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
          queryClient.invalidateQueries({ queryKey: ['law-changes-sync-dates'] })
        }
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      eventSource.close()
      eventSourceRef.current = null
      setIsSyncing(false)
      setSyncLogs((prev) => [...prev, { type: 'error', message: '연결이 끊어졌습니다.' }])
      message.error('동기화 중 연결이 끊어졌습니다.')
    }
  }

  // 동기화 중지
  const handleStopSync = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsSyncing(false)
    message.warning('동기화가 중지되었습니다.')
  }

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // 승인 뮤테이션
  const approveMutation = useMutation({
    mutationFn: (id: number) => lawChangesApi.approve(id),
    onSuccess: () => {
      message.success('변경이 승인되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '승인 중 오류가 발생했습니다.')
    },
  })

  // 반려 뮤테이션
  const rejectMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      lawChangesApi.reject(id, { process_note: note }),
    onSuccess: () => {
      message.success('변경이 반려되었습니다.')
      setRejectModalOpen(false)
      setRejectNote('')
      setRejectTargetId(null)
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '반려 중 오류가 발생했습니다.')
    },
  })

  // 일괄 승인 뮤테이션
  const bulkApproveMutation = useMutation({
    mutationFn: (ids: number[]) => lawChangesApi.bulkApprove(ids),
    onSuccess: (result) => {
      message.success(result.message)
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '일괄 승인 중 오류가 발생했습니다.')
    },
  })

  // 일괄 반려 뮤테이션
  const bulkRejectMutation = useMutation({
    mutationFn: ({ ids, note }: { ids: number[]; note: string }) =>
      lawChangesApi.bulkReject(ids, { process_note: note }),
    onSuccess: (result) => {
      message.success(result.message)
      setSelectedRowKeys([])
      setBulkRejectModalOpen(false)
      setBulkRejectNote('')
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '일괄 반려 중 오류가 발생했습니다.')
    },
  })


  const statusConfig: Record<string, { color: string; text: string }> = {
    pending: { color: 'orange', text: '대기' },
    reviewing: { color: 'blue', text: '검토중' },
    approved: { color: 'green', text: '승인됨' },
    rejected: { color: 'red', text: '반려됨' },
  }

  const apiStatusConfig: Record<string, { color: string; text: string }> = {
    success: { color: 'green', text: '성공' },
    no_response: { color: 'red', text: '응답없음' },
    not_found: { color: 'orange', text: '미발견' },
  }

  const columns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      width: 250,
      render: (text: string, record: LawChange) => (
        <a onClick={() => { setSelectedChange(record); setDetailModalOpen(true); }}>
          {text}
        </a>
      ),
    },
    {
      title: '상태',
      dataIndex: 'api_status',
      key: 'api_status',
      width: 100,
      render: (status: string) => {
        const config = apiStatusConfig[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '처리 상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = statusConfig[status] || { color: 'default', text: status }
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
      render: (_: any, record: LawChange) => {
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
      title: '처리일시',
      dataIndex: 'processed_at',
      key: 'processed_at',
      width: 150,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '작업',
      key: 'action',
      width: 200,
      render: (_: any, record: LawChange) => (
        <Space>
          {record.status === 'pending' && record.api_status === 'success' && (
            <Button
              type="primary"
              size="small"
              icon={<CheckCircleOutlined />}
              loading={approveMutation.isPending}
              onClick={() => approveMutation.mutate(record.id)}
            >
              승인
            </Button>
          )}
          {(record.status === 'pending' || record.status === 'reviewing') && (
            <Button
              size="small"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => {
                setRejectTargetId(record.id)
                setRejectModalOpen(true)
              }}
            >
              반려
            </Button>
          )}
          <Button
            size="small"
            icon={<HistoryOutlined />}
            onClick={() => {
              setHistoryLawId(record.law_id)
              setHistoryLawName(record.law_name)
              setHistoryModalOpen(true)
            }}
          >
            연혁
          </Button>
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as number[]),
    getCheckboxProps: (record: LawChange) => ({
      disabled: record.status !== 'pending',
    }),
  }

  const fieldNames: Record<string, string> = {
    proclaimed_date: '공포일',
    enforced_date: '시행일',
    revision_type: '제개정구분',
    law_id: '법령ID',
    dept_name: '소관부처',
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

  // 상세 모달용 변경내용 렌더링
  const renderChangeValues = (oldValues: Record<string, any> | null, newValues: Record<string, any> | null) => {
    if (!oldValues && !newValues) return <Text type="secondary">변경 내용 없음</Text>

    const fields = new Set([
      ...Object.keys(oldValues || {}),
      ...Object.keys(newValues || {}),
    ])

    return (
      <div>
        {Array.from(fields).map((field) => {
          const oldVal = oldValues?.[field]
          const newVal = newValues?.[field]
          if (oldVal === newVal) return null
          return (
            <div key={field} style={{ marginBottom: 4 }}>
              <Text type="secondary">{fieldNames[field] || field}: </Text>
              <Text delete>{oldVal || '(없음)'}</Text>
              <Text> → </Text>
              <Text strong>{newVal || '(없음)'}</Text>
            </div>
          )
        })}
      </div>
    )
  }

  // 동기화 진행 중 UI 렌더링
  const renderSyncingContent = () => (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <LoadingOutlined spin style={{ fontSize: 18 }} />
          <Text strong>법령 동기화 진행 중...</Text>
          <Button danger size="small" onClick={handleStopSync}>
            중지
          </Button>
        </Space>
      </div>

      {syncProgress && syncProgress.total && (
        <div style={{ marginBottom: 16 }}>
          <Progress
            percent={Math.round(((syncProgress.current || 0) / syncProgress.total) * 100)}
            status="active"
            format={() => `${syncProgress.current || 0} / ${syncProgress.total}`}
          />
          {syncProgress.law_name && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              현재: {syncProgress.law_name}
            </Text>
          )}
        </div>
      )}

      <div
        ref={logContainerRef}
        style={{
          maxHeight: 400,
          overflowY: 'auto',
          border: '1px solid #d9d9d9',
          borderRadius: 4,
          padding: 8,
          backgroundColor: '#fafafa',
        }}
      >
        <List
          size="small"
          dataSource={syncLogs}
          renderItem={(log) => (
            <List.Item style={{ padding: '4px 0', borderBottom: 'none' }}>
              {log.type === 'start' && (
                <Alert message={log.message} type="info" style={{ width: '100%' }} />
              )}
              {log.type === 'complete' && (
                <Alert
                  message={log.message}
                  description={`성공: ${log.updated}건, 실패: ${log.failed}건, 변경감지: ${log.changed_count}건`}
                  type="success"
                  style={{ width: '100%' }}
                />
              )}
              {log.type === 'changed' && log.law && (
                <div style={{ width: '100%' }}>
                  <Tag color={log.law.api_status === 'success' ? 'green' : 'red'}>
                    {log.law.api_status === 'success' ? '변경' : log.law.api_status === 'no_response' ? '응답없음' : '미발견'}
                  </Tag>
                  <Text strong>{log.law.law_name}</Text>
                  {log.law.api_status === 'success' && log.law.changes && Object.keys(log.law.changes).length > 0 && (
                    <div style={{ marginLeft: 24, marginTop: 4 }}>
                      {renderChangeValuesCompact(
                        Object.fromEntries(Object.entries(log.law.changes).map(([k, v]: [string, any]) => [k, v.old])),
                        Object.fromEntries(Object.entries(log.law.changes).map(([k, v]: [string, any]) => [k, v.new]))
                      )}
                    </div>
                  )}
                </div>
              )}
              {log.type === 'error' && (
                <Alert message={log.message || log.error} type="error" style={{ width: '100%' }} />
              )}
            </List.Item>
          )}
        />
      </div>
    </Card>
  )

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>법령 변경 관리</Title>
        <Button
          type="primary"
          icon={isSyncing ? <LoadingOutlined /> : <SyncOutlined />}
          onClick={handleStartSync}
          disabled={isSyncing}
        >
          법령 동기화
        </Button>
      </Space>

      {/* 동기화 중일 때 */}
      {isSyncing ? (
        renderSyncingContent()
      ) : (
        <>
          {/* 통계 카드 */}
          {stats && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="전체" value={stats.total} />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="대기"
                    value={stats.pending}
                    valueStyle={{ color: '#fa8c16' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="검토중"
                    value={stats.reviewing}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="승인됨"
                    value={stats.approved}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={4}>
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

          {/* 필터 */}
          <Space style={{ marginBottom: 16 }} wrap>
            <Select
              placeholder="동기화 날짜"
              style={{ width: 200 }}
              value={selectedSyncDate}
              onChange={(value) => {
                setSelectedSyncDate(value)
                setPage(1)
              }}
              options={syncDates?.map((d: SyncDate) => ({
                value: d.sync_date,
                label: `${d.sync_date} (${d.pending}/${d.total})`,
              })) || []}
            />
            <Input.Search
              placeholder="법령명 검색"
              style={{ width: 200 }}
              allowClear
              onSearch={setSearch}
            />
            <Select
              placeholder="처리 상태"
              style={{ width: 120 }}
              allowClear
              onChange={setStatus}
              options={[
                { value: 'pending', label: '대기' },
                { value: 'reviewing', label: '검토중' },
                { value: 'approved', label: '승인됨' },
                { value: 'rejected', label: '반려됨' },
              ]}
            />
            <Select
              placeholder="상태"
              style={{ width: 120 }}
              allowClear
              onChange={setApiStatus}
              options={[
                { value: 'success', label: '성공' },
                { value: 'no_response', label: '응답없음' },
                { value: 'not_found', label: '미발견' },
              ]}
            />
            <Select
              placeholder="소관부처"
              style={{ width: 180 }}
              allowClear
              showSearch
              onChange={setDeptName}
              options={departments?.map((d: any) => ({
                value: d.dept_name,
                label: `${d.dept_name} (${d.pending}/${d.total})`,
              })) || []}
            />

            {/* 일괄 작업 버튼 */}
            {selectedRowKeys.length > 0 && (
              <>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  loading={bulkApproveMutation.isPending}
                  onClick={() => bulkApproveMutation.mutate(selectedRowKeys)}
                >
                  선택 승인 ({selectedRowKeys.length})
                </Button>
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => setBulkRejectModalOpen(true)}
                >
                  선택 반려 ({selectedRowKeys.length})
                </Button>
              </>
            )}
          </Space>

          {/* 테이블 */}
          <Table
            columns={columns}
            dataSource={data?.items || []}
            rowKey="id"
            loading={isLoading}
            rowSelection={rowSelection}
            pagination={{
              current: page,
              total: data?.total || 0,
              pageSize: 20,
              onChange: setPage,
              showTotal: (total) => `총 ${total}건`,
            }}
            scroll={{ x: 1200 }}
          />
        </>
      )}

      {/* 상세 모달 */}
      <Modal
        title="법령 변경 상세"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            닫기
          </Button>,
          selectedChange?.status === 'pending' && selectedChange?.api_status === 'success' && (
            <Button
              key="approve"
              type="primary"
              icon={<CheckCircleOutlined />}
              loading={approveMutation.isPending}
              onClick={() => {
                approveMutation.mutate(selectedChange.id)
                setDetailModalOpen(false)
              }}
            >
              승인
            </Button>
          ),
          (selectedChange?.status === 'pending' || selectedChange?.status === 'reviewing') && (
            <Button
              key="reject"
              danger
              icon={<CloseCircleOutlined />}
              onClick={() => {
                setRejectTargetId(selectedChange?.id || null)
                setRejectModalOpen(true)
                setDetailModalOpen(false)
              }}
            >
              반려
            </Button>
          ),
        ].filter(Boolean)}
        width={700}
      >
        {selectedChange && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="법령명" span={2}>
              {selectedChange.law_name}
            </Descriptions.Item>
            <Descriptions.Item label="법령유형">
              {selectedChange.law_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="소관부처">
              {selectedChange.dept_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="상태">
              <Tag color={apiStatusConfig[selectedChange.api_status]?.color}>
                {apiStatusConfig[selectedChange.api_status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="처리 상태">
              <Tag color={statusConfig[selectedChange.status]?.color}>
                {statusConfig[selectedChange.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="동기화 일시">
              {dayjs(selectedChange.sync_date).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="동기화 배치">
              {selectedChange.sync_batch_id || '-'}
            </Descriptions.Item>
            {selectedChange.api_message && (
              <Descriptions.Item label="API 메시지" span={2}>
                <Text type={selectedChange.api_status !== 'success' ? 'danger' : undefined}>
                  {selectedChange.api_message}
                </Text>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="변경 내용" span={2}>
              {renderChangeValues(selectedChange.old_values, selectedChange.new_values)}
            </Descriptions.Item>
            {selectedChange.processed_at && (
              <>
                <Descriptions.Item label="처리 일시">
                  {dayjs(selectedChange.processed_at).format('YYYY-MM-DD HH:mm:ss')}
                </Descriptions.Item>
                <Descriptions.Item label="처리자">
                  {selectedChange.processed_by || '-'}
                </Descriptions.Item>
              </>
            )}
            {selectedChange.process_note && (
              <Descriptions.Item label="처리 메모" span={2}>
                {selectedChange.process_note}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 반려 모달 */}
      <Modal
        title="변경 반려"
        open={rejectModalOpen}
        onCancel={() => {
          setRejectModalOpen(false)
          setRejectNote('')
          setRejectTargetId(null)
        }}
        onOk={() => {
          if (!rejectNote.trim()) {
            message.warning('반려 사유를 입력해주세요.')
            return
          }
          if (rejectTargetId) {
            rejectMutation.mutate({ id: rejectTargetId, note: rejectNote })
          }
        }}
        okText="반려"
        okButtonProps={{ danger: true, loading: rejectMutation.isPending }}
      >
        <div style={{ marginBottom: 8 }}>
          <ExclamationCircleOutlined style={{ color: '#faad14', marginRight: 8 }} />
          <Text>반려 사유를 입력해주세요.</Text>
        </div>
        <TextArea
          rows={4}
          value={rejectNote}
          onChange={(e) => setRejectNote(e.target.value)}
          placeholder="반려 사유를 입력하세요..."
        />
      </Modal>

      {/* 일괄 반려 모달 */}
      <Modal
        title={`일괄 반려 (${selectedRowKeys.length}건)`}
        open={bulkRejectModalOpen}
        onCancel={() => {
          setBulkRejectModalOpen(false)
          setBulkRejectNote('')
        }}
        onOk={() => {
          if (!bulkRejectNote.trim()) {
            message.warning('반려 사유를 입력해주세요.')
            return
          }
          bulkRejectMutation.mutate({ ids: selectedRowKeys, note: bulkRejectNote })
        }}
        okText="일괄 반려"
        okButtonProps={{ danger: true, loading: bulkRejectMutation.isPending }}
      >
        <div style={{ marginBottom: 8 }}>
          <ExclamationCircleOutlined style={{ color: '#faad14', marginRight: 8 }} />
          <Text>{selectedRowKeys.length}건의 변경을 반려합니다. 반려 사유를 입력해주세요.</Text>
        </div>
        <TextArea
          rows={4}
          value={bulkRejectNote}
          onChange={(e) => setBulkRejectNote(e.target.value)}
          placeholder="반려 사유를 입력하세요..."
        />
      </Modal>

      {/* 연혁 모달 */}
      <Modal
        title={`법령 변경 연혁 - ${historyLawName}`}
        open={historyModalOpen}
        onCancel={() => {
          setHistoryModalOpen(false)
          setHistoryLawId(null)
          setHistoryLawName('')
        }}
        footer={[
          <Button key="close" onClick={() => setHistoryModalOpen(false)}>
            닫기
          </Button>,
        ]}
        width={800}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>로딩 중...</div>
        ) : historyData?.items?.length > 0 ? (
          <Timeline
            items={historyData.items.map((item: LawChange) => ({
              color: item.status === 'approved' ? 'green' : item.status === 'rejected' ? 'red' : 'blue',
              children: (
                <div key={item.id}>
                  <div style={{ marginBottom: 4 }}>
                    <Text strong>{dayjs(item.sync_date).format('YYYY-MM-DD HH:mm')}</Text>
                    <Tag
                      color={statusConfig[item.status]?.color}
                      style={{ marginLeft: 8 }}
                    >
                      {statusConfig[item.status]?.text}
                    </Tag>
                    <Tag color={apiStatusConfig[item.api_status]?.color}>
                      {apiStatusConfig[item.api_status]?.text}
                    </Tag>
                  </div>
                  {item.api_status === 'success' && item.old_values && item.new_values && (
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {renderChangeValues(item.old_values, item.new_values)}
                    </div>
                  )}
                  {item.api_status !== 'success' && (
                    <div style={{ fontSize: 12, color: '#ff4d4f' }}>
                      {item.api_message}
                    </div>
                  )}
                  {item.process_note && (
                    <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                      처리 메모: {item.process_note}
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
            변경 연혁이 없습니다.
          </div>
        )}
      </Modal>
    </div>
  )
}
