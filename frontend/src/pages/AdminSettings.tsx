import { useState } from 'react'
import { Card, Table, Switch, InputNumber, Input, Button, message, Tag, Space, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, SaveOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../services/api'
import type { LlmProvider, LlmProviderListResponse } from '../types/api'

const { Title, Text } = Typography

export default function AdminSettings() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValues, setEditValues] = useState<{
    model_name?: string
    rate_limit_per_minute?: number
  }>({})

  const { data, isLoading } = useQuery<LlmProviderListResponse>({
    queryKey: ['llm-providers'],
    queryFn: adminApi.getLlmProviders,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => adminApi.updateLlmProvider(id, data),
    onSuccess: () => {
      message.success('설정이 저장되었습니다')
      queryClient.invalidateQueries({ queryKey: ['llm-providers'] })
      setEditingId(null)
      setEditValues({})
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '설정 저장에 실패했습니다')
    },
  })

  const handleActiveToggle = (provider: LlmProvider) => {
    updateMutation.mutate({
      id: provider.id,
      data: { is_active: !provider.is_active },
    })
  }

  const handleSave = (provider: LlmProvider) => {
    updateMutation.mutate({
      id: provider.id,
      data: editValues,
    })
  }

  const columns = [
    {
      title: '프로바이더',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 120,
    },
    {
      title: '모델명',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 200,
      render: (text: string, record: LlmProvider) =>
        editingId === record.id ? (
          <Input
            size="small"
            defaultValue={text}
            onChange={(e) => setEditValues((prev) => ({ ...prev, model_name: e.target.value }))}
            style={{ width: 180 }}
          />
        ) : (
          <Text code>{text}</Text>
        ),
    },
    {
      title: 'API 키',
      dataIndex: 'api_key_configured',
      key: 'api_key_configured',
      width: 100,
      render: (configured: boolean, record: LlmProvider) =>
        configured ? (
          <Tag icon={<CheckCircleOutlined />} color="success">설정됨</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">미설정</Tag>
        ),
    },
    {
      title: '활성',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean, record: LlmProvider) => (
        <Switch
          checked={active}
          onChange={() => handleActiveToggle(record)}
          loading={updateMutation.isPending}
          size="small"
        />
      ),
    },
    {
      title: 'Rate Limit (분당)',
      dataIndex: 'rate_limit_per_minute',
      key: 'rate_limit_per_minute',
      width: 130,
      render: (val: number, record: LlmProvider) =>
        editingId === record.id ? (
          <InputNumber
            size="small"
            min={1}
            max={100}
            defaultValue={val}
            onChange={(v) => setEditValues((prev) => ({ ...prev, rate_limit_per_minute: v ?? undefined }))}
          />
        ) : (
          `${val}회`
        ),
    },
    {
      title: '',
      key: 'action',
      width: 100,
      render: (_: any, record: LlmProvider) =>
        editingId === record.id ? (
          <Space>
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              onClick={() => handleSave(record)}
              loading={updateMutation.isPending}
            >
              저장
            </Button>
            <Button size="small" onClick={() => { setEditingId(null); setEditValues({}) }}>
              취소
            </Button>
          </Space>
        ) : (
          <Button size="small" onClick={() => { setEditingId(record.id); setEditValues({}) }}>
            편집
          </Button>
        ),
    },
  ]

  return (
    <div>
      <Title level={4}>LLM 설정</Title>
      <Card>
        <Table
          dataSource={data?.providers || []}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">
            활성 프로바이더는 1개만 설정할 수 있습니다. API 키는 서버 환경변수로 관리됩니다.
          </Text>
        </div>
      </Card>
    </div>
  )
}
