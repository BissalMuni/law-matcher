import { useState, useEffect } from 'react'
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
  List,
  Input,
} from 'antd'
import {
  SyncOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { amendmentApi, lawChangesApi } from '../services/api'
import { useSync, type ChangedLaw } from '../contexts/SyncContext'
import dayjs from 'dayjs'

const { Title, Text } = Typography

interface SyncDate {
  sync_date: string
  total: number
  success: number
  no_response: number
  not_found: number
}

export default function AmendmentList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [selectedSyncDate, setSelectedSyncDate] = useState<string>()
  const [apiStatusFilter, setApiStatusFilter] = useState<string>()
  const [searchText, setSearchText] = useState<string>()

  // 전역 동기화 상태 (탭 전환에도 유지)
  const { syncing, progress, logs, syncResult, changedLaws, startSync, clearResult } = useSync()

  // 동기화 모달 표시 여부 (로컬 UI 상태)
  const [syncModalOpen, setSyncModalOpen] = useState(false)

  // 동기화 중이면 자동으로 모달 열기 (다른 탭에서 돌아왔을 때)
  useEffect(() => {
    if (syncing) {
      setSyncModalOpen(true)
    }
  }, [syncing])

  // 동기화 날짜 목록 조회
  const { data: syncDates } = useQuery<SyncDate[]>({
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
    queryKey: ['law-changes', page, selectedSyncDate, apiStatusFilter, searchText],
    queryFn: () =>
      lawChangesApi.getList({
        page,
        size: 20,
        sync_date: selectedSyncDate,
        api_status: apiStatusFilter,
        search: searchText,
      }),
    enabled: !!selectedSyncDate,
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
    startSync()
  }

  const handleCloseModal = () => {
    setSyncModalOpen(false)
  }

  // 선택된 날짜의 통계 (syncDates에서 직접 추출)
  const selectedStats = syncDates?.find((d) => d.sync_date === selectedSyncDate)

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
      width: 300,
    },
    {
      title: '법령구분',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 80,
      render: (type: string) => type || '-',
    },
    {
      title: 'API상태',
      dataIndex: 'api_status',
      key: 'api_status',
      width: 90,
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
      render: (_: any, record: any) => record.new_values?.revision_type || record.old_values?.revision_type || '-',
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
      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>법령 변경 관리</Title>
        <Space>
          {syncing && !syncModalOpen && (
            <Button icon={<LoadingOutlined spin />} onClick={() => setSyncModalOpen(true)}>
              동기화 진행 중 ({progress?.current || 0}/{progress?.total || 0})
            </Button>
          )}
          <Button type="primary" icon={<SyncOutlined />} onClick={handleStartSync} disabled={syncing}>
            법령 동기화
          </Button>
        </Space>
      </div>

      {/* 동기화 이력 목록 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <List
          grid={{ gutter: 12, xs: 1, sm: 2, md: 3, lg: 4, xl: 6, xxl: 6 }}
          dataSource={syncDates || []}
          renderItem={(item: SyncDate) => (
            <List.Item style={{ marginBottom: 0 }}>
              <Card
                size="small"
                hoverable
                onClick={() => {
                  setSelectedSyncDate(item.sync_date)
                  setPage(1)
                  setApiStatusFilter(undefined)
                  setSearchText(undefined)
                }}
                style={{
                  cursor: 'pointer',
                  borderColor: selectedSyncDate === item.sync_date ? '#1890ff' : undefined,
                  backgroundColor: selectedSyncDate === item.sync_date ? '#e6f4ff' : undefined,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {item.sync_date}
                </div>
                <Space size={4} wrap>
                  <Tag>{item.total}건</Tag>
                  <Tag color="green">{item.success}</Tag>
                  {item.no_response > 0 && <Tag color="red">{item.no_response}</Tag>}
                  {item.not_found > 0 && <Tag color="orange">{item.not_found}</Tag>}
                </Space>
              </Card>
            </List.Item>
          )}
        />
      </Card>

      {/* 선택된 날짜 통계 + 필터 */}
      {selectedStats && (
        <div style={{ marginBottom: 16 }}>
          <Space size={16} wrap style={{ marginBottom: 12 }}>
            <Text strong style={{ fontSize: 16 }}>{selectedStats.sync_date}</Text>
            <Tag>전체 {selectedStats.total}</Tag>
            <Tag
              color="green"
              style={{ cursor: 'pointer' }}
              onClick={() => { setApiStatusFilter('success'); setPage(1) }}
            >
              성공 {selectedStats.success}
            </Tag>
            {selectedStats.no_response > 0 && (
              <Tag
                color="red"
                style={{ cursor: 'pointer' }}
                onClick={() => { setApiStatusFilter('no_response'); setPage(1) }}
              >
                응답없음 {selectedStats.no_response}
              </Tag>
            )}
            {selectedStats.not_found > 0 && (
              <Tag
                color="orange"
                style={{ cursor: 'pointer' }}
                onClick={() => { setApiStatusFilter('not_found'); setPage(1) }}
              >
                미발견 {selectedStats.not_found}
              </Tag>
            )}
            {apiStatusFilter && (
              <Button type="link" size="small" onClick={() => { setApiStatusFilter(undefined); setPage(1) }}>
                필터 해제
              </Button>
            )}
          </Space>
          <div>
            <Input
              placeholder="법령명 검색"
              prefix={<SearchOutlined />}
              allowClear
              style={{ width: 300 }}
              value={searchText}
              onChange={(e) => {
                setSearchText(e.target.value || undefined)
                setPage(1)
              }}
            />
          </div>
        </div>
      )}

      {/* 법령 테이블 */}
      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{
          current: page,
          total: data?.total || 0,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `총 ${total}건`,
        }}
        scroll={{ x: 900 }}
      />

      {/* 동기화 진행 모달 */}
      <Modal
        title="법령 동기화"
        open={syncModalOpen}
        onCancel={handleCloseModal}
        footer={[
          <Button key="close" onClick={handleCloseModal}>
            닫기
          </Button>,
        ]}
        width={600}
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
      >
        {syncing && (
          <Alert
            type="info"
            message={`${progress?.total || '?'}건의 법령에 대한 동기화를 실행 중입니다.`}
            description="서버 백그라운드에서 실행되므로 이 창을 닫거나 다른 탭으로 이동해도 작업은 계속 진행됩니다. 완료 후 이 페이지에서 결과를 확인할 수 있습니다."
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        {progress && (
          <div style={{ marginBottom: 16 }}>
            <Progress
              percent={Math.round(((progress.current || 0) / (progress.total || 1)) * 100)}
              status={syncing ? 'active' : 'success'}
              format={() => `${progress.current || 0} / ${progress.total || 0}`}
            />
            {progress.law_name && (
              <Space style={{ marginTop: 8 }}>
                {getStatusIcon(progress.status || '')}
                <Text>{progress.law_name}</Text>
              </Space>
            )}
          </div>
        )}

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
