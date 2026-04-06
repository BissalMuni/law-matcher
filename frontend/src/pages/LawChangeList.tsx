import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
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
  Tabs,
  Tooltip,
} from 'antd'
import {
  HistoryOutlined,
  SyncOutlined,
  LoadingOutlined,
  DownloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { lawChangesApi, lawSearchApi, lawsApi, ordinanceApi } from '../services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography

interface LawChange {
  id: number
  law_id: number
  law_name: string
  law_type: string | null
  revision_type: string | null
  sync_date: string
  sync_batch_id: string | null
  api_status: string
  api_message: string | null
  old_values: Record<string, any> | null
  new_values: Record<string, any> | null
  dept_name: string | null
  dept_code: number | null
  created_at: string
}

interface SyncBatch {
  sync_batch_id: string
  sync_date: string
  total: number
  changed: number
  no_change: number
  no_response: number
  not_found: number
  error: number
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
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [apiStatus, setApiStatus] = useState<string>(() => searchParams.get('apiStatus') || 'all')
  const [changedField, setChangedField] = useState<string | undefined>(() => searchParams.get('changedField') || undefined)
  const [search, setSearch] = useState<string>(() => searchParams.get('search') || undefined)
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([])
  const [selectedBatchId, setSelectedBatchId] = useState<string | undefined>(() => searchParams.get('batchId') || undefined)
  const [revisionType, setRevisionType] = useState<string | undefined>(() => searchParams.get('revisionType') || undefined)

  // 동기화 상태
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncProgress, setSyncProgress] = useState<SyncProgress | null>(null)
  const [syncLogs, setSyncLogs] = useState<SyncProgress[]>([])
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logContainerRef = useRef<HTMLDivElement>(null)

  // 상세 모달
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [selectedChange, setSelectedChange] = useState<LawChange | null>(null)

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
  const [verifyingLawName, setVerifyingLawName] = useState(false)

  // 필터 상태 변경 시 URL 쿼리 파라미터 업데이트
  useEffect(() => {
    const params = new URLSearchParams()
    if (page > 1) params.set('page', String(page))
    if (apiStatus && apiStatus !== 'all') params.set('apiStatus', apiStatus)
    if (changedField) params.set('changedField', changedField)
    if (search) params.set('search', search)
    if (selectedBatchId) params.set('batchId', selectedBatchId)
    if (revisionType) params.set('revisionType', revisionType)
    setSearchParams(params, { replace: true })
  }, [page, apiStatus, changedField, search, selectedBatchId, revisionType, setSearchParams])

  // 동기화 배치 목록 조회
  const { data: syncBatches } = useQuery({
    queryKey: ['law-changes-sync-batches'],
    queryFn: () => lawChangesApi.getSyncBatches(),
  })

  // 제개정구분 목록 조회
  const { data: revisionTypes } = useQuery({
    queryKey: ['law-changes-revision-types'],
    queryFn: () => lawChangesApi.getRevisionTypes(),
  })

  // URL에 syncDate가 있으면 해당 날짜 선택 (뒤로가기 등)
  // 목록 화면이 기본이므로 자동 선택하지 않음

  // 데이터 조회 (날짜 필터 추가)
  const { data, isLoading } = useQuery({
    queryKey: ['law-changes', page, apiStatus, changedField, search, selectedBatchId, revisionType],
    queryFn: () =>
      lawChangesApi.getList({
        page,
        size: 20,
        api_status: apiStatus === 'all' ? undefined : apiStatus,
        changed_field: changedField,
        search,
        sync_batch_id: selectedBatchId,
        revision_type: revisionType,
      }),
    enabled: !isSyncing && !!selectedBatchId,
  })

  // 통계 조회 (선택된 배치 기준)
  const { data: stats } = useQuery({
    queryKey: ['law-changes-stats', selectedBatchId],
    queryFn: () => lawChangesApi.getStats({ sync_batch_id: selectedBatchId }),
    enabled: !isSyncing && !!selectedBatchId,
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
  const handleStartSync = async () => {
    try {
      setIsSyncing(true)
      setSyncProgress(null)
      setSyncLogs([])
      setSelectedBatchId(undefined)

      await lawSearchApi.startSync()
      setSyncLogs((prev) => [...prev, { type: 'start', message: '법령 동기화를 시작합니다...' }])

      // 폴링으로 진행 상태 확인
      pollTimerRef.current = setInterval(async () => {
        try {
          const progress = await lawSearchApi.getSyncProgress()
          setSyncProgress(progress)

          if (progress.status === 'COMPLETED' || progress.status === 'FAILED') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
            setIsSyncing(false)
            setSyncProgress(null)

            if (progress.status === 'COMPLETED') {
              setSyncLogs((prev) => [...prev, { type: 'complete', message: `동기화 완료: ${progress.current || 0}건 처리`, updated: progress.updated || 0, failed: progress.failed || 0, changed_count: progress.changed_count || 0 }])
              message.success('동기화가 완료되었습니다.')
            } else {
              setSyncLogs((prev) => [...prev, { type: 'error', message: '동기화 중 오류가 발생했습니다.' }])
              message.error('동기화 중 오류가 발생했습니다.')
            }

            queryClient.invalidateQueries({ queryKey: ['law-changes'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-sync-batches'] })
          }
        } catch (e) {
          console.error('Polling error:', e)
        }
      }, 3000)
    } catch (e) {
      setIsSyncing(false)
      message.error('동기화 시작에 실패했습니다.')
    }
  }

  // 동기화 중지
  const handleStopSync = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    setIsSyncing(false)
    message.warning('동기화가 중지되었습니다.')
  }

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

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

  // 법령 일괄 삭제 mutation
  const bulkDeleteLawMutation = useMutation({
    mutationFn: (lawIds: number[]) => lawsApi.bulkDelete(lawIds),
    onSuccess: (result) => {
      message.success(result.message)
      setSelectedRowKeys([])
      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
      queryClient.invalidateQueries({ queryKey: ['law-changes-sync-batches'] })
    },
    onError: () => {
      message.error('법령 일괄 삭제에 실패했습니다.')
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

  // 상위법령 실제 저장 처리
  const executeParentLawSave = (values: any) => {
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

  // 상위법령 폼 제출 (법령명 검증 후 저장)
  const handleParentLawSubmit = async (values: any) => {
    const lawNameChanged = !editingParentLaw || editingParentLaw.law_name !== values.law_name

    // 법령명이 변경된 경우 법제처 API로 검증
    if (lawNameChanged) {
      setVerifyingLawName(true)
      try {
        const result = await lawSearchApi.searchByName(values.law_name)
        if (result.success) {
          executeParentLawSave(values)
        } else {
          Modal.confirm({
            title: '법령명 검증 실패',
            content: result.message || `'${values.law_name}'에 대한 법제처 API 응답이 없습니다. 강제로 적용하시겠습니까?`,
            okText: '강제적용',
            okButtonProps: { danger: true },
            cancelText: '취소',
            onOk: () => {
              executeParentLawSave(values)
            },
          })
        }
      } catch {
        Modal.confirm({
          title: '법령명 검증 실패',
          content: '법제처 API 연결에 실패했습니다. 강제로 적용하시겠습니까?',
          okText: '강제적용',
          okButtonProps: { danger: true },
          cancelText: '취소',
          onOk: () => {
            executeParentLawSave(values)
          },
        })
      } finally {
        setVerifyingLawName(false)
      }
    } else {
      // 법령명 변경 없으면 바로 저장
      executeParentLawSave(values)
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

  const apiStatusConfig: Record<string, { color: string; text: string }> = {
    success: { color: 'green', text: '변경감지' },
    no_change: { color: 'blue', text: '변경없음' },
    no_response: { color: 'red', text: '응답없음' },
    not_found: { color: 'orange', text: '미발견' },
    error: { color: 'volcano', text: '오류' },
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
      title: '제개정구분',
      dataIndex: 'revision_type',
      key: 'revision_type',
      width: 100,
      render: (type: string) => type || '-',
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
      render: (date: string) => dayjs.utc(date).local().format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '작업',
      key: 'action',
      width: 150,
      render: (_: any, record: LawChange) => (
        <Space>
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

  // 동기화 로그 UI 렌더링
  const renderSyncLogContent = () => (
    <Card>
      {isSyncing && (
        <div style={{ marginBottom: 16 }}>
          <Space>
            <LoadingOutlined spin style={{ fontSize: 18 }} />
            <Text strong>법령 동기화 진행 중...</Text>
            <Button danger size="small" onClick={handleStopSync}>
              중지
            </Button>
          </Space>
        </div>
      )}

      {isSyncing && syncProgress && syncProgress.total && (
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
                    {apiStatusConfig[log.law.api_status]?.text || log.law.api_status}
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
      <Title level={4} style={{ marginBottom: 16 }}>법령 변경 관리</Title>

      <Tabs
        defaultActiveKey="list"
        onChange={(key) => {
          if (key === 'list') setSelectedBatchId(undefined)
        }}
        destroyOnHidden={false}
        items={[
          {
            key: 'sync',
            label: isSyncing ? <span><LoadingOutlined spin /> 동기화 진행</span> : <span><SyncOutlined /> 동기화</span>,
            children: (
              <div>
                {!isSyncing && (
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Tooltip title="법제처 API에서 전체 법령 변경사항을 동기화합니다">
                        <Button
                          type="primary"
                          icon={<SyncOutlined />}
                          onClick={handleStartSync}
                        >
                          법령 동기화 시작
                        </Button>
                      </Tooltip>
                      <Tooltip title="백그라운드에서 진행 중인 동기화 상태를 확인합니다">
                        <Button
                          icon={<SyncOutlined />}
                          onClick={async () => {
                          try {
                            const progress = await lawSearchApi.getSyncProgress()
                            if (progress.status === 'RUNNING') {
                              setIsSyncing(true)
                              setSyncProgress(progress)
                              message.info(`동기화 진행 중: ${progress.current || 0} / ${progress.total || 0}`)
                              // 폴링 시작
                              if (!pollTimerRef.current) {
                                pollTimerRef.current = setInterval(async () => {
                                  try {
                                    const p = await lawSearchApi.getSyncProgress()
                                    setSyncProgress(p)
                                    if (p.status === 'COMPLETED' || p.status === 'FAILED') {
                                      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
                                      pollTimerRef.current = null
                                      setIsSyncing(false)
                                      if (p.status === 'COMPLETED') {
                                        setSyncLogs((prev) => [...prev, { type: 'complete', message: `동기화 완료: ${p.current || 0}건 처리` }])
                                        message.success('동기화가 완료되었습니다.')
                                      } else {
                                        message.error('동기화 중 오류가 발생했습니다.')
                                      }
                                      queryClient.invalidateQueries({ queryKey: ['law-changes'] })
                                      queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
                                      queryClient.invalidateQueries({ queryKey: ['law-changes-sync-batches'] })
                                    }
                                  } catch (e) {
                                    console.error('Polling error:', e)
                                  }
                                }, 3000)
                              }
                            } else {
                              message.info(`현재 상태: ${progress.status === 'IDLE' ? '대기 중' : progress.status}`)
                            }
                          } catch {
                            message.error('상태 확인 실패')
                          }
                        }}
                      >
                        상태 확인
                      </Button>
                      </Tooltip>
                      <Tooltip title="동기화 상태를 초기화합니다 (FAILED 상태 해제)">
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          onClick={async () => {
                            try {
                              await lawSearchApi.clearSyncProgress()
                              setIsSyncing(false)
                              setSyncProgress(null)
                              setSyncLogs([])
                              message.success('동기화 상태가 초기화되었습니다.')
                            } catch {
                              message.error('초기화 실패')
                            }
                          }}
                        >
                          초기화
                        </Button>
                      </Tooltip>
                    </Space>
                  </div>
                )}
                {(isSyncing || syncLogs.length > 0) && renderSyncLogContent()}
              </div>
            ),
          },
          {
            key: 'list',
            label: '동기화 이력',
              children: (
                <Table
                  columns={[
                    {
                      title: '동기화 일시',
                      dataIndex: 'sync_date',
                      key: 'sync_date',
                      width: 180,
                      render: (v: string) => dayjs.utc(v).local().format('YYYY-MM-DD HH:mm'),
                    },
                    {
                      title: '전체',
                      dataIndex: 'total',
                      key: 'total',
                      width: 100,
                      align: 'center' as const,
                    },
                    {
                      title: '변경감지',
                      dataIndex: 'changed',
                      key: 'changed',
                      width: 100,
                      align: 'center' as const,
                      render: (v: number) => <Text style={{ color: v > 0 ? '#fa8c16' : undefined }}>{v}</Text>,
                    },
                    {
                      title: '변경없음',
                      dataIndex: 'no_change',
                      key: 'no_change',
                      width: 100,
                      align: 'center' as const,
                      render: (v: number) => <Text style={{ color: '#52c41a' }}>{v}</Text>,
                    },
                    {
                      title: '응답없음',
                      dataIndex: 'no_response',
                      key: 'no_response',
                      width: 100,
                      align: 'center' as const,
                      render: (v: number) => <Text style={{ color: v > 0 ? '#ff4d4f' : undefined }}>{v}</Text>,
                    },
                    {
                      title: '미발견',
                      dataIndex: 'not_found',
                      key: 'not_found',
                      width: 100,
                      align: 'center' as const,
                      render: (v: number) => <Text style={{ color: v > 0 ? '#ff4d4f' : undefined }}>{v}</Text>,
                    },
                    {
                      title: '오류',
                      dataIndex: 'error',
                      key: 'error',
                      width: 100,
                      align: 'center' as const,
                      render: (v: number) => <Text style={{ color: v > 0 ? '#ff4d4f' : undefined }}>{v}</Text>,
                    },
                    {
                      title: '작업',
                      key: 'action',
                      width: 100,
                      align: 'center' as const,
                      render: (_: any, record: SyncBatch) => (
                        <Popconfirm
                          title="동기화 데이터 삭제"
                          description={`이 동기화 배치의 데이터 ${record.total}건을 모두 삭제합니다.`}
                          onConfirm={async (e) => {
                            e?.stopPropagation()
                            try {
                              await lawChangesApi.deleteBySyncBatch(record.sync_batch_id)
                              message.success('삭제되었습니다.')
                              queryClient.invalidateQueries({ queryKey: ['law-changes-sync-batches'] })
                            } catch {
                              message.error('삭제에 실패했습니다.')
                            }
                          }}
                          onCancel={(e) => e?.stopPropagation()}
                          okText="삭제"
                          okButtonProps={{ danger: true }}
                          cancelText="취소"
                        >
                          <Button
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            onClick={(e) => e.stopPropagation()}
                          >
                            삭제
                          </Button>
                        </Popconfirm>
                      ),
                    },
                  ]}
                  dataSource={syncBatches || []}
                  rowKey="sync_batch_id"
                  pagination={false}
                  onRow={(record: SyncBatch) => ({
                    onClick: () => {
                      setSelectedBatchId(record.sync_batch_id)
                      setPage(1)
                    },
                    style: { cursor: 'pointer' },
                  })}
                />
              ),
            },
            {
              key: 'detail',
              label: selectedBatchId ? `동기화 상세` : '동기화 상세',
              disabled: !selectedBatchId,
              children: selectedBatchId ? (
                <>
                  {/* 1행: 필터 + 엑셀 다운로드 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <Space wrap>
                      <Space.Compact>
                        <Input
                          placeholder="법령명 검색"
                          style={{ width: 200 }}
                          allowClear
                          onPressEnter={(e) => setSearch((e.target as HTMLInputElement).value)}
                          onChange={(e) => !e.target.value && setSearch('')}
                        />
                        <Button
                          icon={<SearchOutlined />}
                          onClick={() => {
                            const input = document.querySelector('input[placeholder="법령명 검색"]') as HTMLInputElement
                            if (input) setSearch(input.value)
                          }}
                        />
                      </Space.Compact>
                      <Select
                        placeholder="API상태"
                        style={{ width: 120 }}
                        allowClear
                        value={apiStatus === 'all' ? undefined : apiStatus}
                        onChange={(value) => {
                          setApiStatus(value || 'all')
                          setPage(1)
                        }}
                        options={[
                          { value: 'all', label: '전체' },
                          { value: 'success', label: '변경감지' },
                          { value: 'no_change', label: '변경없음' },
                          { value: 'no_response', label: '응답없음' },
                          { value: 'not_found', label: '미발견' },
                          { value: 'error', label: '오류' },
                        ]}
                      />
                      <Select
                        placeholder="변경내용"
                        style={{ width: 140 }}
                        allowClear
                        value={changedField}
                        onChange={(value) => {
                          setChangedField(value)
                          setPage(1)
                        }}
                        options={[
                          { value: 'proclaimed_date', label: '공포일' },
                          { value: 'enforced_date', label: '시행일' },
                          { value: 'revision_type', label: '제개정구분' },
                          { value: 'law_id', label: '법령ID' },
                          { value: 'dept_name', label: '소관부처' },
                        ]}
                      />
                      <Select
                        placeholder="제개정구분"
                        style={{ width: 140 }}
                        allowClear
                        value={revisionType}
                        onChange={(value) => {
                          setRevisionType(value)
                          setPage(1)
                        }}
                        options={revisionTypes?.map((rt: { revision_type: string; count: number }) => ({
                          value: rt.revision_type,
                          label: `${rt.revision_type} (${rt.count})`,
                        })) || []}
                      />
                    </Space>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={async () => {
                        try {
                          await lawChangesApi.exportExcel({
                            api_status: apiStatus === 'all' ? undefined : apiStatus,
                            sync_batch_id: selectedBatchId,
                            search,
                            changed_field: changedField,
                            revision_type: revisionType,
                          })
                          message.success('엑셀 파일이 다운로드되었습니다.')
                          } catch (error) {
                            message.error('엑셀 다운로드 중 오류가 발생했습니다.')
                          }
                        }}
                      >
                        엑셀 다운로드
                      </Button>
                  </div>

                  {/* 2행: 통계 태그 + 삭제 버튼 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <Space>
                      <Text strong>{syncBatches?.find((b: SyncBatch) => b.sync_batch_id === selectedBatchId)?.sync_date ? dayjs.utc(syncBatches.find((b: SyncBatch) => b.sync_batch_id === selectedBatchId).sync_date).local().format('YYYY-MM-DD HH:mm') : selectedBatchId}</Text>
                      {stats && (
                        <>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'all' ? undefined : 'default'}
                            onClick={() => { setApiStatus('all'); setPage(1) }}
                          >전체 {stats.total}</Tag>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'success' ? 'green' : 'default'}
                            onClick={() => { setApiStatus(apiStatus === 'success' ? 'all' : 'success'); setPage(1) }}
                          >변경감지 {stats.by_api_status?.success || 0}</Tag>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'no_change' ? 'blue' : 'default'}
                            onClick={() => { setApiStatus(apiStatus === 'no_change' ? 'all' : 'no_change'); setPage(1) }}
                          >변경없음 {stats.by_api_status?.no_change || 0}</Tag>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'no_response' ? 'red' : 'default'}
                            onClick={() => { setApiStatus(apiStatus === 'no_response' ? 'all' : 'no_response'); setPage(1) }}
                          >응답없음 {stats.by_api_status?.no_response || 0}</Tag>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'not_found' ? 'orange' : 'default'}
                            onClick={() => { setApiStatus(apiStatus === 'not_found' ? 'all' : 'not_found'); setPage(1) }}
                          >미발견 {stats.by_api_status?.not_found || 0}</Tag>
                          <Tag
                            style={{ cursor: 'pointer' }}
                            color={apiStatus === 'error' ? 'volcano' : 'default'}
                            onClick={() => { setApiStatus(apiStatus === 'error' ? 'all' : 'error'); setPage(1) }}
                          >오류 {stats.by_api_status?.error || 0}</Tag>
                        </>
                      )}
                    </Space>
                    {selectedRowKeys.length > 0 && (
                      <Popconfirm
                        title="법령 일괄 삭제"
                        description={`선택된 ${selectedRowKeys.length}건의 법령과 관련된 모든 데이터가 삭제됩니다. 계속하시겠습니까?`}
                        onConfirm={() => {
                          const items = data?.items || []
                          const lawIds = [
                            ...new Set(
                              items
                                .filter((item: LawChange) => selectedRowKeys.includes(item.id))
                                .map((item: LawChange) => item.law_id)
                            ),
                          ]
                          bulkDeleteLawMutation.mutate(lawIds)
                        }}
                        okText="삭제"
                        okButtonProps={{ danger: true }}
                        cancelText="취소"
                      >
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          loading={bulkDeleteLawMutation.isPending}
                        >
                          선택 삭제 ({selectedRowKeys.length})
                        </Button>
                      </Popconfirm>
                    )}
                  </div>

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
              ) : null,
            },
          ]}
        />

      {/* 상세 모달 */}
      <Modal
        title="법령 변경 상세"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            닫기
          </Button>,
        ]}
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
            <Descriptions.Item label="동기화 일시">
              {dayjs.utc(selectedChange.sync_date).local().format('YYYY-MM-DD HH:mm:ss')}
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
          </Descriptions>
        )}
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
              color: item.api_status === 'success' ? 'green' : item.api_status === 'not_found' ? 'orange' : 'red',
              children: (
                <div key={item.id}>
                  <div style={{ marginBottom: 4 }}>
                    <Text strong>{dayjs.utc(item.sync_date).local().format('YYYY-MM-DD HH:mm')}</Text>
                    <Tag color={apiStatusConfig[item.api_status]?.color} style={{ marginLeft: 8 }}>
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
              <a onClick={() => {
                handleOrdinanceModalClose()
                navigate(`/ordinances/${selectedOrdinance.id}`)
              }}>{selectedOrdinance.name}</a>
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
        confirmLoading={verifyingLawName || createParentLawMutation.isPending || updateParentLawMutation.isPending}
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
