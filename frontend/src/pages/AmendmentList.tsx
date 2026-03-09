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
  Row,
  Col,
  Statistic,
} from 'antd'
import { SyncOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { amendmentApi, lawChangesApi } from '../services/api'
import { useSync, type ChangedLaw } from '../contexts/SyncContext'
import dayjs from 'dayjs'

const { Title, Text } = Typography

interface SyncDate {
  sync_date: string
  total: number
  success: number
  pending: number
}

export default function AmendmentList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [selectedSyncDate, setSelectedSyncDate] = useState<string>()
  const [apiStatusFilter, setApiStatusFilter] = useState<string>()

  // 전역 동기화 상태 (탭 전환에도 유지)
  const { syncing, progress, logs, syncResult, changedLaws, startSync, stopSync, clearResult } = useSync()

  // 동기화 모달 표시 여부 (로컬 UI 상태)
  const [syncModalOpen, setSyncModalOpen] = useState(false)
  const [resultFilter, setResultFilter] = useState<string>('all')

  // 동기화 중이면 자동으로 모달 열기 (다른 탭에서 돌아왔을 때)
  useEffect(() => {
    if (syncing) {
      setSyncModalOpen(true)
    }
  }, [syncing])

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
    startSync()
  }

  const handleCloseModal = () => {
    setSyncModalOpen(false)
    // 동기화 중에 모달을 닫아도 동기화는 계속 진행 (전역 상태)
  }

  const handleStopSync = () => {
    stopSync()
    setSyncModalOpen(false)
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
        if (record.api_status === 'no_response' || record.api_status === 'not_found') {
          return <Text type="danger">{record.api_message}</Text>
        }
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
        if (changeItems.length > 0) {
          return <div>{changeItems}</div>
        }

        if (record.article_sync && record.article_sync.changes_detected > 0) {
          return (
            <Text type="warning">
              조문 변경 감지 {record.article_sync.changes_detected}건
              (생성 {record.article_sync.created} / 수정 {record.article_sync.updated} / 삭제 {record.article_sync.deleted})
            </Text>
          )
        }

        return <Text type="secondary">변경 없음</Text>
      },
    },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'requesting':
        return <LoadingOutlined spin style={{ color: '#1890ff' }} />
      case 'received':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'article_syncing':
        return <LoadingOutlined spin style={{ color: '#722ed1' }} />
      case 'article_synced':
        return <CheckCircleOutlined style={{ color: '#722ed1' }} />
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
              <Button type="link" danger onClick={() => { clearResult(); setResultFilter('all'); }}>
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
                : changedLaws.filter(
                  (law) =>
                    law.api_status === 'success'
                    && (
                      Object.keys(law.changes || {}).length > 0
                      || (law.article_sync?.changes_detected || 0) > 0
                    )
                )
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

      {/* 동기화 진행 모달 */}
      <Modal
        title="법령 동기화"
        open={syncModalOpen}
        onCancel={handleCloseModal}
        footer={[
          syncing && (
            <Button key="stop" danger onClick={handleStopSync}>
              중지
            </Button>
          ),
          <Button key="close" onClick={handleCloseModal}>
            {syncing ? '백그라운드로' : '닫기'}
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
                {progress.status === 'article_syncing' && ' - 조문 동기화 중...'}
                {progress.status === 'article_synced' && ' - 조문 동기화 완료'}
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
                <Descriptions.Item label="조문 동기화 법령">{syncResult.articleSyncedLaws}건</Descriptions.Item>
                <Descriptions.Item label="조문 처리">{syncResult.articleSyncedArticles}건</Descriptions.Item>
                <Descriptions.Item label="조문 생성/수정/삭제">
                  {syncResult.articleCreated}/{syncResult.articleUpdated}/{syncResult.articleDeleted}
                </Descriptions.Item>
                <Descriptions.Item label="조문 변경 감지">
                  {syncResult.articleChangesDetected}건
                </Descriptions.Item>
              </Descriptions>
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {syncResult && (
          <Alert
            type={syncResult.articleSyncFailed > 0 ? 'warning' : 'success'}
            message={
              syncResult.articleSyncFailed > 0
                ? `조문 동기화 일부 실패 (${syncResult.articleSyncFailed}건)`
                : '조문 정보 DB 반영 완료'
            }
            style={{ marginBottom: 16 }}
          />
        )}

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
