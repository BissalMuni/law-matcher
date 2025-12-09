import { useState } from 'react'
import { Table, Tag, Typography, Space, Select, Button } from 'antd'
import { SyncOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { amendmentApi, syncApi } from '../services/api'
import dayjs from 'dayjs'

const { Title } = Typography

export default function AmendmentList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [processed, setProcessed] = useState<boolean>()

  const { data, isLoading } = useQuery({
    queryKey: ['amendments', page, processed],
    queryFn: () =>
      amendmentApi.getList({
        page,
        size: 20,
        processed,
      }),
  })

  const syncMutation = useMutation({
    mutationFn: () => syncApi.syncLaws(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amendments'] })
    },
  })

  const analyzeMutation = useMutation({
    mutationFn: (id: number) => amendmentApi.analyze(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['amendments'] })
      queryClient.invalidateQueries({ queryKey: ['reviews'] })
    },
  })

  const changeTypeColor: Record<string, string> = {
    ENACTED: 'green',
    AMENDED: 'blue',
    ABOLISHED: 'red',
  }

  const columns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
    },
    {
      title: '개정유형',
      dataIndex: 'change_type',
      key: 'change_type',
      width: 100,
      render: (type: string) => (
        <Tag color={changeTypeColor[type]}>{type}</Tag>
      ),
    },
    {
      title: '감지일시',
      dataIndex: 'detected_at',
      key: 'detected_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '처리여부',
      dataIndex: 'processed',
      key: 'processed',
      width: 100,
      render: (processed: boolean) => (
        <Tag color={processed ? 'green' : 'orange'}>
          {processed ? '완료' : '대기'}
        </Tag>
      ),
    },
    {
      title: '작업',
      key: 'action',
      width: 120,
      render: (_: any, record: any) => (
        <Button
          size="small"
          disabled={record.processed}
          loading={analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate(record.id)}
        >
          영향 분석
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>법령 개정 목록</Title>
        <Button
          type="primary"
          icon={<SyncOutlined />}
          loading={syncMutation.isPending}
          onClick={() => syncMutation.mutate()}
        >
          법령 동기화
        </Button>
      </div>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="처리여부"
          style={{ width: 120 }}
          allowClear
          onChange={setProcessed}
          options={[
            { value: false, label: '대기' },
            { value: true, label: '완료' },
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
