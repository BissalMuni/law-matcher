import { Card, Empty, Typography, Tag, Collapse } from 'antd'
import { WarningOutlined } from '@ant-design/icons'
import AiLabel from './AiLabel'
import type { LlmAnalysisResult } from '../../types/api'

const { Text, Paragraph } = Typography

interface AiSummaryPanelProps {
  result: LlmAnalysisResult | null
  loading?: boolean
}

/**
 * AI 요약 표시 패널 — 개정검토 탭에 배치
 * 주요 변경사항, 변경 조문 목록, 조례 영향, 개정 필요 조문별 분석 표시
 */
export default function AiSummaryPanel({ result, loading }: AiSummaryPanelProps) {
  if (!result || result.status !== 'success') {
    return null
  }

  const affectedArticles = result.affected_articles_json || []

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

      {/* 개정 필요 조례 조문별 분석 */}
      {affectedArticles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            <WarningOutlined style={{ color: '#faad14', marginRight: 4 }} />
            개정 필요 조례 조문 ({affectedArticles.length}건)
          </Text>
          <Collapse
            size="small"
            items={affectedArticles.map((article, idx) => ({
              key: idx,
              label: (
                <span>
                  <Tag color="orange">{article.article_no}</Tag>
                  {article.article_title || ''}
                </span>
              ),
              children: (
                <div style={{ lineHeight: 1.8 }}>
                  {article.current_content_summary && (
                    <div style={{ marginBottom: 8 }}>
                      <Text type="secondary" strong>현재 내용: </Text>
                      <Text type="secondary">{article.current_content_summary}</Text>
                    </div>
                  )}
                  {article.issue && (
                    <div style={{ marginBottom: 8 }}>
                      <Text strong style={{ color: '#cf1322' }}>문제점: </Text>
                      <Text>{article.issue}</Text>
                    </div>
                  )}
                  {article.recommendation && (
                    <div>
                      <Text strong style={{ color: '#1677ff' }}>개정 권고: </Text>
                      <Text>{article.recommendation}</Text>
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          생성일: {new Date(result.created_at).toLocaleString('ko-KR')}
        </Text>
      </div>
    </Card>
  )
}
