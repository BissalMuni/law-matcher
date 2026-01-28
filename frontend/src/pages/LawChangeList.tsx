import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
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
  Form,
  Popconfirm,
  Spin,
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  SyncOutlined,
  LoadingOutlined,
  DownloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { lawChangesApi, lawSearchApi, lawsApi, ordinanceApi } from '../services/api'
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
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [status, setStatus] = useState<string>(() => searchParams.get('status') || undefined)
  const [apiStatus, setApiStatus] = useState<string>(() => searchParams.get('apiStatus') || 'all')
  const [deptName, setDeptName] = useState<string>(() => searchParams.get('deptName') || undefined)
  const [search, setSearch] = useState<string>(() => searchParams.get('search') || undefined)
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [selectedSyncDate, setSelectedSyncDate] = useState<string>(() => searchParams.get('syncDate') || undefined)

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

  // 조례 상세 모달 (법령명 클릭 시)
  const [ordinanceModalOpen, setOrdinanceModalOpen] = useState(false)
  const [selectedLawForOrdinance, setSelectedLawForOrdinance] = useState<LawChange | null>(null)
  const [linkedOrdinances, setLinkedOrdinances] = useState<any[]>([])
  const [selectedOrdinance, setSelectedOrdinance] = useState<any | null>(null)
  const [ordinanceLoading, setOrdinanceLoading] = useState(false)

  // 상위법령 수정 모달
  const [parentLawModalOpen, setParentLawModalOpen] = useState(false)
  const [editingParentLaw, setEditingParentLaw] = useState<any | null>(null)
  const [parentLawForm] = Form.useForm()

  // 필터 상태 변경 시 URL 쿼리 파라미터 업데이트
  useEffect(() => {
    const params = new URLSearchParams()
    if (page > 1) params.set('page', String(page))
    if (status) params.set('status', status)
    if (apiStatus && apiStatus !== 'all') params.set('apiStatus', apiStatus)
    if (deptName) params.set('deptName', deptName)
    if (search) params.set('search', search)
    if (selectedSyncDate) params.set('syncDate', selectedSyncDate)
    setSearchParams(params, { replace: true })
  }, [page, status, apiStatus, deptName, search, selectedSyncDate, setSearchParams])

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
        api_status: apiStatus === 'all' ? undefined : apiStatus,
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

  // 조례의 상위법령 조회
  const { data: parentLaws, refetch: refetchParentLaws } = useQuery({
    queryKey: ['ordinance-parent-laws', selectedOrdinance?.id],
    queryFn: () => ordinanceApi.getParentLaws(selectedOrdinance?.id),
    enabled: !!selectedOrdinance?.id,
  })

  // 조례의 조문 조회
  const { data: articles } = useQuery({
    queryKey: ['ordinance-articles', selectedOrdinance?.id],
    queryFn: () => ordinanceApi.getArticles(selectedOrdinance?.id),
    enabled: !!selectedOrdinance?.id,
  })

  // 상위법령 추가 mutation
  const createParentLawMutation = useMutation({
    mutationFn: (data: any) => ordinanceApi.createParentLaw(selectedOrdinance?.id, data),
    onSuccess: () => {
      message.success('상위법령이 추가되었습니다.')
      refetchParentLaws()
      setParentLawModalOpen(false)
      parentLawForm.resetFields()
    },
    onError: () => {
      message.error('상위법령 추가에 실패했습니다.')
    },
  })

  // 상위법령 수정 mutation
  const updateParentLawMutation = useMutation({
    mutationFn: ({ parentLawId, data }: { parentLawId: number; data: any }) =>
      ordinanceApi.updateParentLaw(parentLawId, data),
    onSuccess: () => {
      message.success('상위법령이 수정되었습니다.')
      refetchParentLaws()
      setParentLawModalOpen(false)
      setEditingParentLaw(null)
      parentLawForm.resetFields()
    },
    onError: () => {
      message.error('상위법령 수정에 실패했습니다.')
    },
  })

  // 상위법령 삭제 mutation
  const deleteParentLawMutation = useMutation({
    mutationFn: (parentLawId: number) => ordinanceApi.deleteParentLaw(parentLawId),
    onSuccess: () => {
      message.success('상위법령이 삭제되었습니다.')
      refetchParentLaws()
    },
    onError: () => {
      message.error('상위법령 삭제에 실패했습니다.')
    },
  })

  // 법령 삭제 mutation (laws + law_changes 모두 삭제)
  const deleteLawMutation = useMutation({
    mutationFn: (lawId: number) => lawsApi.delete(lawId),
    onSuccess: () => {
      message.success('법령이 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    },
    onError: () => {
      message.error('법령 삭제에 실패했습니다.')
    },
  })

  // 법령명 클릭 핸들러 - 연계 조례 조회
  const handleLawNameClick = async (record: LawChange) => {
    setSelectedLawForOrdinance(record)
    setOrdinanceLoading(true)
    setOrdinanceModalOpen(true)

    try {
      // 법령 ID로 연계된 조례 조회
      const ordinances = await lawsApi.getOrdinances(record.law_id)
      setLinkedOrdinances(ordinances || [])

      // 조례가 1개면 바로 선택
      if (ordinances && ordinances.length === 1) {
        const ordinanceDetail = await ordinanceApi.getById(ordinances[0].ordinance_id)
        setSelectedOrdinance(ordinanceDetail)
      } else {
        setSelectedOrdinance(null)
      }
    } catch (error) {
      message.error('연계 조례 조회에 실패했습니다.')
      setLinkedOrdinances([])
    } finally {
      setOrdinanceLoading(false)
    }
  }

  // 조례 선택 핸들러
  const handleOrdinanceSelect = async (ordinance: any) => {
    setOrdinanceLoading(true)
    try {
      const ordinanceDetail = await ordinanceApi.getById(ordinance.ordinance_id)
      setSelectedOrdinance(ordinanceDetail)
    } catch (error) {
      message.error('조례 상세 조회에 실패했습니다.')
    } finally {
      setOrdinanceLoading(false)
    }
  }

  // 조례 모달 닫기
  const handleOrdinanceModalClose = () => {
    setOrdinanceModalOpen(false)
    setSelectedLawForOrdinance(null)
    setLinkedOrdinances([])
    setSelectedOrdinance(null)
  }

  // 상위법령 추가 핸들러
  const handleAddParentLaw = () => {
    setEditingParentLaw(null)
    parentLawForm.resetFields()
    // 현재 법령 정보로 폼 초기화
    if (selectedLawForOrdinance) {
      parentLawForm.setFieldsValue({
        law_name: selectedLawForOrdinance.law_name,
        law_type: selectedLawForOrdinance.law_type,
      })
    }
    setParentLawModalOpen(true)
  }

  // 상위법령 수정 핸들러
  const handleEditParentLaw = (record: any) => {
    setEditingParentLaw(record)
    parentLawForm.setFieldsValue({
      ...record,
    })
    setParentLawModalOpen(true)
  }

  // 상위법령 폼 제출
  const handleParentLawSubmit = (values: any) => {
    const data = {
      law_name: values.law_name,
      law_type: values.law_type,
      related_articles: values.related_articles,
    }
    if (editingParentLaw) {
      updateParentLawMutation.mutate({ parentLawId: editingParentLaw.id, data })
    } else {
      createParentLawMutation.mutate(data)
    }
  }

  // 상위법령 테이블 컬럼
  const parentLawColumns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
    },
    {
      title: '법령ID',
      dataIndex: 'law_id',
      key: 'law_id',
      width: 100,
    },
    {
      title: '법령유형',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 90,
    },
    {
      title: '공포일자',
      dataIndex: 'proclaimed_date',
      key: 'proclaimed_date',
      width: 110,
    },
    {
      title: '시행일자',
      dataIndex: 'enforced_date',
      key: 'enforced_date',
      width: 110,
    },
    {
      title: '관련조문',
      dataIndex: 'related_articles',
      key: 'related_articles',
      width: 120,
    },
    {
      title: '작업',
      key: 'action',
      width: 80,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEditParentLaw(record)} />
          <Popconfirm
            title="삭제 확인"
            description="이 상위법령 매핑을 삭제하시겠습니까?"
            onConfirm={() => deleteParentLawMutation.mutate(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

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
      width: 220,
      render: (text: string, record: LawChange) => (
        <a onClick={() => handleLawNameClick(record)}>
          {text}
        </a>
      ),
    },
    {
      title: '법령구분',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 90,
      render: (type: string) => type || '-',
    },
    {
      title: 'API상태',
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
      title: '조례관할부서',
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
      width: 250,
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
          <Popconfirm
            title="법령 삭제"
            description="이 법령과 관련된 모든 데이터가 삭제됩니다. 계속하시겠습니까?"
            onConfirm={() => deleteLawMutation.mutate(record.law_id)}
            okText="삭제"
            okButtonProps={{ danger: true }}
            cancelText="취소"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              loading={deleteLawMutation.isPending}
            >
              삭제
            </Button>
          </Popconfirm>
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
    dept_name: '조례관할부서',
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
              style={{ width: 120 }}
              value={apiStatus}
              onChange={(value) => setApiStatus(value)}
              options={[
                { value: 'all', label: '전체' },
                { value: 'success', label: '성공' },
                { value: 'no_response', label: '응답없음' },
                { value: 'not_found', label: '미발견' },
              ]}
            />
            <Select
              placeholder="조례관할부서"
              style={{ width: 180 }}
              allowClear
              showSearch
              onChange={setDeptName}
              options={departments?.map((d: any) => ({
                value: d.dept_name,
                label: `${d.dept_name} (${d.pending}/${d.total})`,
              })) || []}
            />

            {/* 엑셀 다운로드 */}
            <Button
              icon={<DownloadOutlined />}
              onClick={async () => {
                try {
                  await lawChangesApi.exportExcel({
                    status,
                    api_status: apiStatus === 'all' ? undefined : apiStatus,
                    dept_name: deptName,
                    sync_date: selectedSyncDate,
                    search,
                  })
                  message.success('엑셀 파일이 다운로드되었습니다.')
                } catch (error) {
                  message.error('엑셀 다운로드 중 오류가 발생했습니다.')
                }
              }}
            >
              엑셀 다운로드
            </Button>

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
            <Descriptions.Item label="조례관할부서">
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

      {/* 조례 상세 모달 (법령명 클릭 시) */}
      <Modal
        title={
          selectedOrdinance ? (
            <Space>
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={() => setSelectedOrdinance(null)}
                style={{ marginRight: 8 }}
              />
              {selectedOrdinance.name}
            </Space>
          ) : (
            `연계 자치법규 - ${selectedLawForOrdinance?.law_name}`
          )
        }
        open={ordinanceModalOpen}
        onCancel={handleOrdinanceModalClose}
        footer={[
          <Button key="close" onClick={handleOrdinanceModalClose}>
            닫기
          </Button>,
        ]}
        width={900}
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {ordinanceLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : selectedOrdinance ? (
          /* 조례 상세 화면 */
          <div>
            <Card title="기본 정보" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="자치법규 코드">{selectedOrdinance.code}</Descriptions.Item>
                <Descriptions.Item label="분류">{selectedOrdinance.category}</Descriptions.Item>
                <Descriptions.Item label="소관부서">{selectedOrdinance.department}</Descriptions.Item>
                <Descriptions.Item label="상태">{selectedOrdinance.status}</Descriptions.Item>
                <Descriptions.Item label="제정일">{selectedOrdinance.enacted_date}</Descriptions.Item>
                <Descriptions.Item label="시행일">{selectedOrdinance.enforced_date}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card
              title="상위법령"
              size="small"
              style={{ marginBottom: 16 }}
              extra={
                <Button type="primary" icon={<PlusOutlined />} size="small" onClick={handleAddParentLaw}>
                  추가
                </Button>
              }
            >
              <Table
                dataSource={parentLaws || []}
                rowKey="id"
                size="small"
                pagination={false}
                columns={parentLawColumns}
                locale={{ emptyText: '상위법령 없음' }}
              />
            </Card>

            <Card title="조문" size="small">
              <Table
                dataSource={articles || []}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 5 }}
                columns={[
                  { title: '조', dataIndex: 'article_no', key: 'article_no', width: 80 },
                  { title: '항', dataIndex: 'paragraph_no', key: 'paragraph_no', width: 60 },
                  { title: '내용', dataIndex: 'content', key: 'content' },
                ]}
              />
            </Card>
          </div>
        ) : linkedOrdinances.length > 0 ? (
          /* 연계 조례 목록 */
          <List
            dataSource={linkedOrdinances}
            renderItem={(item: any) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => handleOrdinanceSelect(item)}
              >
                <List.Item.Meta
                  title={<a>{item.ordinance_name}</a>}
                  description={
                    <Space>
                      <span>{item.ordinance_category}</span>
                      {item.related_articles && <span>| 관련조문: {item.related_articles}</span>}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            연계된 자치법규가 없습니다.
          </div>
        )}
      </Modal>

      {/* 상위법령 추가/수정 모달 */}
      <Modal
        title={editingParentLaw ? '상위법령 수정' : '상위법령 추가'}
        open={parentLawModalOpen}
        onCancel={() => {
          setParentLawModalOpen(false)
          setEditingParentLaw(null)
          parentLawForm.resetFields()
        }}
        onOk={() => parentLawForm.submit()}
        confirmLoading={createParentLawMutation.isPending || updateParentLawMutation.isPending}
      >
        <Form form={parentLawForm} layout="vertical" onFinish={handleParentLawSubmit}>
          <Form.Item
            name="law_name"
            label="법령명"
            rules={[{ required: true, message: '법령명을 입력하세요' }]}
          >
            <Input placeholder="예: 지방자치법" />
          </Form.Item>
          <Form.Item
            name="law_type"
            label="법령 유형"
            rules={[{ required: true, message: '법령 유형을 선택하세요' }]}
          >
            <Select
              placeholder="유형 선택"
              options={[
                { value: '법률', label: '법률' },
                { value: '시행령', label: '시행령' },
                { value: '시행규칙', label: '시행규칙' },
              ]}
            />
          </Form.Item>
          <Form.Item name="related_articles" label="관련 조문">
            <Input placeholder="예: 제1조, 제2조" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
