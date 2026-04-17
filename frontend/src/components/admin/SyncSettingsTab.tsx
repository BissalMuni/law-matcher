import { useEffect, useState } from 'react'
import { Card, Radio, Select, Button, Space, Typography, Descriptions, Alert, message } from 'antd'
import { SaveOutlined, LinkOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { adminApi } from '../../services/api'
import type { SyncSettingsResponse } from '../../services/api'

const { Text } = Typography

const INTERVAL_OPTIONS = [
  { label: '1시간', value: 1 },
  { label: '3시간', value: 3 },
  { label: '6시간', value: 6 },
  { label: '12시간', value: 12 },
  { label: '24시간 (매일)', value: 24 },
  { label: '72시간 (3일)', value: 72 },
  { label: '168시간 (매주)', value: 168 },
]

export default function SyncSettingsTab() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'MANUAL' | 'AUTO'>('MANUAL')
  const [intervalHours, setIntervalHours] = useState<number>(24)

  const { data, isLoading } = useQuery<SyncSettingsResponse>({
    queryKey: ['sync-settings'],
    queryFn: adminApi.getSyncSettings,
  })

  useEffect(() => {
    if (data) {
      setMode(data.auto_sync_enabled ? 'AUTO' : 'MANUAL')
      setIntervalHours(data.interval_hours)
    }
  }, [data])

  const updateMutation = useMutation({
    mutationFn: adminApi.updateSyncSettings,
    onSuccess: () => {
      message.success('동기화 설정이 저장되었습니다')
      queryClient.invalidateQueries({ queryKey: ['sync-settings'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '저장에 실패했습니다')
    },
  })

  const handleSave = () => {
    updateMutation.mutate({
      auto_sync_enabled: mode === 'AUTO',
      interval_hours: intervalHours,
    })
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return '-'
    return dayjs(iso).format('YYYY-MM-DD HH:mm')
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="자동 동기화" loading={isLoading}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>동기화 모드</Text>
            <div style={{ marginTop: 8 }}>
              <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
                <Radio value="MANUAL">수동 (관리자가 직접 실행)</Radio>
                <Radio value="AUTO">자동 (지정 주기로 실행)</Radio>
              </Radio.Group>
            </div>
          </div>

          {mode === 'AUTO' && (
            <div>
              <Text strong>실행 주기</Text>
              <div style={{ marginTop: 8 }}>
                <Select
                  style={{ width: 200 }}
                  value={intervalHours}
                  onChange={setIntervalHours}
                  options={INTERVAL_OPTIONS}
                />
              </div>
            </div>
          )}

          <Descriptions size="small" column={1} bordered>
            <Descriptions.Item label="마지막 실행">
              {formatDate(data?.last_sync_at ?? null)}
            </Descriptions.Item>
            <Descriptions.Item label="다음 실행 예정">
              {mode === 'AUTO' ? formatDate(data?.next_sync_at ?? null) : '자동 실행 꺼짐'}
            </Descriptions.Item>
          </Descriptions>

          <Alert
            type="info"
            showIcon
            message="자동 동기화는 5분 간격으로 스케줄러가 체크하여 실행됩니다. 저장 후 최대 5분 내에 반영됩니다."
          />

          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={updateMutation.isPending}
          >
            저장
          </Button>
        </Space>
      </Card>

      <Card title="수동 동기화 / 이력">
        <Space direction="vertical">
          <Text>수동 동기화 실행 및 이력은 법령변경감지 페이지에서 관리합니다.</Text>
          <Button
            type="default"
            icon={<LinkOutlined />}
            onClick={() => navigate('/amendments')}
          >
            법령변경감지로 이동
          </Button>
        </Space>
      </Card>
    </Space>
  )
}
