import { useState } from 'react'
import { Tabs, Button, Spin, message, Badge, Alert } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi } from '../../services/api'
import type { DetectionResult } from '../../types/api'
import TabA_DateCompare from './TabA_DateCompare'
import TabB_ArticleCompare from './TabB_ArticleCompare'
import TabC_ReasonCompare from './TabC_ReasonCompare'

interface Props {
  ordinanceId: number
  lawMap: Record<number, string>  // law_id → law_name
}

export default function DetectionTabs({ ordinanceId, lawMap }: Props) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('A')

  const { data, isLoading } = useQuery({
    queryKey: ['detection-results', ordinanceId],
    queryFn: () => ordinanceApi.getDetectionResults(ordinanceId),
  })

  const runMutation = useMutation({
    mutationFn: () => ordinanceApi.runDetection(ordinanceId),
    onSuccess: () => {
      message.success('판별이 완료되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['detection-results', ordinanceId] })
    },
    onError: () => {
      message.error('판별 실행 중 오류가 발생했습니다.')
    },
  })

  const results: DetectionResult[] = data?.results || []

  // 탭별 건수 및 경고 여부
  const countA = results.filter(r => r.detection_method === 'A_PROCLAIMED_DATE')
  const countB = results.filter(r => r.detection_method === 'B_ARTICLE_CHANGE')
  const countC = results.filter(r => r.detection_method === 'C_REVISION_REASON')
  const hasWarningA = countA.some(r => r.needs_revision)
  const hasWarningB = countB.some(r => r.needs_revision)
  const hasWarningC = countC.some(r => r.needs_revision)
  const hasAnyWarning = hasWarningA || hasWarningB || hasWarningC

  const tabLabel = (label: string, count: number, hasWarning: boolean) => (
    <Badge dot={hasWarning} offset={[6, 0]}>
      <span>{label} ({count})</span>
    </Badge>
  )

  if (isLoading) {
    return <Spin style={{ display: 'block', textAlign: 'center', padding: 24 }} />
  }

  return (
    <div>
      {hasAnyWarning && (
        <Alert
          type="warning"
          message="새로운 변경이 감지되었습니다."
          description={`${[hasWarningA && 'A.공포일자', hasWarningB && 'B.조문변경', hasWarningC && 'C.제개정이유'].filter(Boolean).join(', ')} 방식에서 검토가 필요합니다.`}
          closable
          style={{ marginBottom: 12 }}
        />
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => runMutation.mutate()}
          loading={runMutation.isPending}
        >
          판별 실행
        </Button>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'A',
            label: tabLabel('A. 공포일자', countA.length, hasWarningA),
            children: <TabA_DateCompare results={results} lawMap={lawMap} />,
          },
          {
            key: 'B',
            label: tabLabel('B. 조문변경', countB.length, hasWarningB),
            children: <TabB_ArticleCompare results={results} lawMap={lawMap} />,
          },
          {
            key: 'C',
            label: tabLabel('C. 제개정이유', countC.length, hasWarningC),
            children: <TabC_ReasonCompare results={results} lawMap={lawMap} />,
          },
        ]}
      />
    </div>
  )
}
