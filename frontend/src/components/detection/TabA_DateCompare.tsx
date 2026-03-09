import { Tag, Descriptions, Empty } from 'antd'
import type { DetectionResult } from '../../types/api'

interface ByLawDetail {
  law_id: number
  law_name?: string
  law_proclaimed_date?: string | null
  ordinance_date?: string | null
  days_diff?: number | null
}

interface Props {
  results: DetectionResult[]
  lawMap: Record<number, string>  // law_id → law_name
}

export default function TabA_DateCompare({ results, lawMap }: Props) {
  const methodResult = results.find(r => r.method === 'proclaimed_date')
  const byLaw: ByLawDetail[] = methodResult?.detail?.by_law || []

  if (!methodResult || byLaw.length === 0) {
    return <Empty description="공포일자 비교 결과가 없습니다." />
  }

  return (
    <div>
      {byLaw.map((item, idx) => {
        // 법령 공포일이 조례 기준일보다 이후면 검토 필요
        const needsRevision = item.days_diff != null && item.days_diff > 0
        return (
          <div key={item.law_id ?? idx} style={{ marginBottom: 16 }}>
            <Descriptions
              title={lawMap[item.law_id] || item.law_name || `법령 #${item.law_id}`}
              bordered
              size="small"
              column={2}
            >
              <Descriptions.Item label="판별 결과">
                <Tag color={needsRevision ? 'error' : 'success'}>
                  {needsRevision ? '검토 필요' : '정상'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="일수 차이">
                {item.days_diff != null ? `${item.days_diff}일` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="법령 공포일자">
                {item.law_proclaimed_date || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="조례 기준일자">
                {item.ordinance_date || '-'}
              </Descriptions.Item>
            </Descriptions>
          </div>
        )
      })}
    </div>
  )
}
