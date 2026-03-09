import { Alert, Button, Empty, Select, Space, Spin, Tag, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useRevisionReason, useRunDetection } from '../../services/api'
import type { DetectionResult } from '../../types/api'

const { Paragraph, Text, Title } = Typography

interface MatchDetail {
  extracted_articles?: string[]
  mapped_articles?: string[]
  review_required_articles?: string[]
  reference_articles?: string[]
}

interface ReasonDetail {
  law_id?: number
  law_name?: string
  revision_reason?: string | null
  amendment_content?: string | null
  match?: MatchDetail
  note?: string | null
}

interface TabCReasonCompareProps {
  ordinanceId: number
  results: DetectionResult[]
  lawMap: Record<number, string>  // law_id → law_name
}

export default function TabC_ReasonCompare({ ordinanceId, results, lawMap }: TabCReasonCompareProps) {
  const runDetection = useRunDetection(ordinanceId)
  const [selectedLawId, setSelectedLawId] = useState<number | undefined>(undefined)

  // lawMap에서 Select 옵션 목록 생성
  const parentLaws = useMemo(() =>
    Object.entries(lawMap).map(([id, name]) => ({
      law_internal_id: Number(id),
      law_name: name,
    })),
    [lawMap]
  )

  useEffect(() => {
    if (!selectedLawId && parentLaws.length > 0) {
      setSelectedLawId(parentLaws[0].law_internal_id)
    }
  }, [parentLaws, selectedLawId])

  const { data: revisionReason, isLoading: isReasonLoading, isError: isReasonError } = useRevisionReason(
    selectedLawId,
    !!selectedLawId
  )

  // 판별 결과에서 revision_reason 방식 추출
  const reasonResultByLaw = useMemo(() => {
    const reasonResult = results.find(r => r.method === 'revision_reason')
    const byLaw = (reasonResult?.detail?.by_law as ReasonDetail[] | undefined) || []
    const map = new Map<number, ReasonDetail>()
    byLaw.forEach((item) => {
      if (item.law_id) {
        map.set(item.law_id, item)
      }
    })
    return map
  }, [results])

  const selectedDetected = selectedLawId ? reasonResultByLaw.get(selectedLawId) : undefined
  const match = selectedDetected?.match
  const extractedArticles = match?.extracted_articles || revisionReason?.extracted_articles || []
  const reviewRequired = match?.review_required_articles || []
  const referenceArticles = match?.reference_articles || []

  const showEmpty = !selectedDetected && !revisionReason
  if (showEmpty) {
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Empty description="개정이유 기반 판별 결과가 없습니다." />
        <Button
          type="primary"
          loading={runDetection.isPending}
          onClick={() => runDetection.mutate(['revision_reason'])}
        >
          판별 실행
        </Button>
      </Space>
    )
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Select
        style={{ minWidth: 320 }}
        placeholder="법령 선택"
        value={selectedLawId}
        onChange={(value) => setSelectedLawId(value)}
        options={parentLaws.map((law) => ({ label: law.law_name, value: law.law_internal_id }))}
      />

      {selectedDetected?.note && (
        <Alert type="warning" showIcon message={selectedDetected.note} />
      )}

      <div>
        <Title level={5}>제개정이유</Title>
        {isReasonLoading ? (
          <Spin size="small" />
        ) : (
          <Paragraph
            ellipsis={{ rows: 6, expandable: true, symbol: '더보기' }}
            style={{ whiteSpace: 'pre-wrap' }}
          >
            {selectedDetected?.revision_reason || revisionReason?.revision_reason || '데이터 없음'}
          </Paragraph>
        )}
        {isReasonError && <Text type="danger">제개정이유 조회 중 오류가 발생했습니다.</Text>}
      </div>

      <div>
        <Title level={5}>개정문</Title>
        <Paragraph
          ellipsis={{ rows: 8, expandable: true, symbol: '더보기' }}
          style={{ whiteSpace: 'pre-wrap' }}
        >
          {selectedDetected?.amendment_content || revisionReason?.amendment_content || '데이터 없음'}
        </Paragraph>
      </div>

      <div>
        <Title level={5}>추출 조문번호</Title>
        {extractedArticles.length > 0 ? (
          extractedArticles.map((articleNo) => (
            <Tag key={articleNo} color={reviewRequired.includes(articleNo) ? 'red' : 'default'}>
              {articleNo}
            </Tag>
          ))
        ) : (
          <Text type="secondary">추출된 조문번호가 없습니다.</Text>
        )}
      </div>

      <div>
        <Title level={5}>매핑 대조 결과</Title>
        {reviewRequired.length > 0 ? (
          <Alert
            type="error"
            showIcon
            message={`검토 필요 조문: ${reviewRequired.join(', ')}`}
          />
        ) : (
          <Alert type="success" showIcon message="매핑 조문 중 검토 필요 항목이 없습니다." />
        )}
        {referenceArticles.length > 0 && (
          <Alert
            style={{ marginTop: 8 }}
            type="info"
            showIcon
            message={`참고(매핑 검토) 조문: ${referenceArticles.join(', ')}`}
          />
        )}
      </div>
    </Space>
  )
}
