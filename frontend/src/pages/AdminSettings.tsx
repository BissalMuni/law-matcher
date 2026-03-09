import { useState } from 'react'
import { Card, Table, Switch, InputNumber, Select, Input, Button, message, Tag, Space, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, SaveOutlined, CloudServerOutlined, DatabaseOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../services/api'
import type { LlmProvider, LlmProviderListResponse } from '../types/api'

const { Title, Text } = Typography

export default function AdminSettings() {
  const queryClient = useQueryClient()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValues, setEditValues] = useState<{
    model_name?: string
    api_key?: string
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
    const payload: Record<string, any> = {}
    if (editValues.model_name !== undefined) payload.model_name = editValues.model_name
    if (editValues.rate_limit_per_minute !== undefined) payload.rate_limit_per_minute = editValues.rate_limit_per_minute
    // API 키: 빈 문자열이면 전송하지 않음 (변경 없음)
    if (editValues.api_key) payload.api_key = editValues.api_key

    updateMutation.mutate({
      id: provider.id,
      data: payload,
    })
  }

  const renderApiKeySource = (record: LlmProvider) => {
    if (record.api_key_source === 'env') {
      return <Tag icon={<CloudServerOutlined />} color="success">ENV 설정됨</Tag>
    }
    if (record.api_key_source === 'db') {
      return <Tag icon={<DatabaseOutlined />} color="processing">DB 설정됨</Tag>
    }
    return <Tag icon={<CloseCircleOutlined />} color="error">미설정</Tag>
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
      width: 220,
      render: (text: string, record: LlmProvider) =>
        editingId === record.id ? (
          <Select
            size="small"
            defaultValue={text}
            onChange={(value) => setEditValues((prev) => ({ ...prev, model_name: value }))}
            style={{ width: 200 }}
            options={record.available_models.map((m) => ({
              value: m.id,
              label: m.name,
            }))}
          />
        ) : (
          <Text code>{text}</Text>
        ),
    },
    {
      title: 'API 키',
      key: 'api_key',
      width: 200,
      render: (_: any, record: LlmProvider) =>
        editingId === record.id ? (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            {renderApiKeySource(record)}
            <Input.Password
              size="small"
              placeholder="새 API 키 입력 (변경 시에만)"
              onChange={(e) => setEditValues((prev) => ({ ...prev, api_key: e.target.value }))}
              style={{ width: 180 }}
            />
          </Space>
        ) : (
          renderApiKeySource(record)
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
            활성 프로바이더는 1개만 설정할 수 있습니다. API 키는 서버 환경변수(ENV) 또는 DB에서 관리할 수 있습니다.
          </Text>
        </div>
      </Card>
    </div>
  )
}
