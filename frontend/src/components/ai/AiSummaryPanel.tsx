import { Card, Empty, Typography } from 'antd'
import AiLabel from './AiLabel'
import type { LlmAnalysisResult } from '../../types/api'

const { Text, Paragraph } = Typography

interface AiSummaryPanelProps {
  result: LlmAnalysisResult | null
  loading?: boolean
}

/**
 * AI 요약 표시 패널 — 개정검토 탭에 배치
 * 주요 변경사항, 변경 조문 목록, 조례 영향을 구조화 표시
 */
export default function AiSummaryPanel({ result, loading }: AiSummaryPanelProps) {
  if (!result || result.status !== 'success') {
    return null
  }

  return (
    <Card
      size="small"
      title={
        <span>
          AI 개정내용 요약{' '}
          <AiLabel providerName={result.provider_name} modelName={result.model_name} showModel />
        </span>
      }
      loading={loading}
      style={{ marginBottom: 16 }}
    >
      {result.summary_text ? (
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {result.summary_text.split('\n').map((line, idx) => {
            if (line.startsWith('### ')) {
              return (
                <Text key={idx} strong style={{ display: 'block', marginTop: idx > 0 ? 12 : 0, marginBottom: 4 }}>
                  {line.replace('### ', '')}
                </Text>
              )
            }
            if (line.startsWith('- ')) {
              return (
                <div key={idx} style={{ paddingLeft: 16 }}>
                  • {line.replace('- ', '')}
                </div>
              )
            }
            return line ? <Paragraph key={idx} style={{ marginBottom: 4 }}>{line}</Paragraph> : null
          })}
        </div>
      ) : (
        <Empty description="요약 데이터 없음" />
      )}
      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          생성일: {new Date(result.created_at).toLocaleString('ko-KR')}
        </Text>
      </div>
    </Card>
  )
}
