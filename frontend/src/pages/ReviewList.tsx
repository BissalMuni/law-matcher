import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Tag, Typography, Space, Select, Button } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { reviewApi } from '../services/api'
import dayjs from 'dayjs'

const { Title } = Typography

export default function ReviewList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [needRevision, setNeedRevision] = useState<boolean | undefined>(() => {
    const v = searchParams.get('needRevision')
    return v ? v === 'true' : undefined
  })
  const [status, setStatus] = useState<string | undefined>(() => searchParams.get('status') || undefined)
  const [urgency, setUrgency] = useState<string | undefined>(() => searchParams.get('urgency') || undefined)

  // 필터 상태 변경 시 URL 쿼리 파라미터 업데이트
  useEffect(() => {
    const params = new URLSearchParams()
    if (page > 1) params.set('page', String(page))
    if (needRevision !== undefined) params.set('needRevision', String(needRevision))
    if (status) params.set('status', status)
    if (urgency) params.set('urgency', urgency)
    setSearchParams(params, { replace: true })
  }, [page, needRevision, status, urgency, setSearchParams])

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', page, needRevision, status, urgency],
    queryFn: () =>
      reviewApi.getList({
        page,
        size: 20,
        need_revision: needRevision,
        status,
        urgency,
      }),
  })

  const urgencyColor: Record<string, string> = {
    HIGH: 'red',
    MEDIUM: 'orange',
    LOW: 'blue',
  }

  const statusColor: Record<string, string> = {
    PENDING: 'orange',
    REVIEWED: 'blue',
    COMPLETED: 'green',
  }

  const columns = [
    {
      title: '자치법규',
      dataIndex: 'ordinance_name',
      key: 'ordinance_name',
      render: (text: string, record: any) => (
        <a onClick={() => navigate(`/reviews/${record.id}`)}>{text || `조례 #${record.ordinance_id}`}</a>
      ),
    },
    {
      title: '상위법령',
      dataIndex: 'law_name',
      key: 'law_name',
    },
    {
      title: '개정필요',
      dataIndex: 'need_revision',
      key: 'need_revision',
      width: 100,
      render: (need: boolean) => (
        <Tag color={need ? 'red' : 'green'}>{need ? '필요' : '불필요'}</Tag>
      ),
    },
    {
      title: '긴급도',
      dataIndex: 'revision_urgency',
      key: 'revision_urgency',
      width: 80,
      render: (urgency: string) =>
        urgency ? <Tag color={urgencyColor[urgency]}>{urgency}</Tag> : '-',
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColor[status]}>{status}</Tag>
      ),
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>개정 검토 목록</Title>
        <Button icon={<DownloadOutlined />}>리포트 다운로드</Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="개정필요"
          style={{ width: 120 }}
          allowClear
          onChange={setNeedRevision}
          options={[
            { value: true, label: '필요' },
            { value: false, label: '불필요' },
          ]}
        />
        <Select
          placeholder="상태"
          style={{ width: 120 }}
          allowClear
          onChange={setStatus}
          options={[
            { value: 'PENDING', label: 'PENDING' },
            { value: 'REVIEWED', label: 'REVIEWED' },
            { value: 'COMPLETED', label: 'COMPLETED' },
          ]}
        />
        <Select
          placeholder="긴급도"
          style={{ width: 120 }}
          allowClear
          onChange={setUrgency}
          options={[
            { value: 'HIGH', label: 'HIGH' },
            { value: 'MEDIUM', label: 'MEDIUM' },
            { value: 'LOW', label: 'LOW' },
          ]}
        />
      </Space>

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
      />
    </div>
  )
}
