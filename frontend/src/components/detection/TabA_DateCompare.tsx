import { Tag, Descriptions, Empty } from 'antd'
import type { DetectionResult } from '../../types/api'

interface Props {
  results: DetectionResult[]
  lawMap: Record<number, string>  // law_id → law_name
}

export default function TabA_DateCompare({ results, lawMap }: Props) {
  const filtered = results.filter(r => r.detection_method === 'A_PROCLAIMED_DATE')

  if (filtered.length === 0) {
    return <Empty description="공포일자 비교 결과가 없습니다." />
  }

  return (
    <div>
      {filtered.map(r => (
        <div key={r.id} style={{ marginBottom: 16 }}>
          <Descriptions
            title={lawMap[r.law_id] || `법령 #${r.law_id}`}
            bordered
            size="small"
            column={2}
          >
            <Descriptions.Item label="판별 결과">
              <Tag color={r.needs_revision ? 'error' : 'success'}>
                {r.needs_revision ? '검토 필요' : '정상'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="일수 차이">
              {r.detail?.days_diff != null ? `${r.detail.days_diff}일` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="법령 공포일자">
              {r.detail?.law_proclaimed_date || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="조례 제정일자">
              {r.detail?.ordinance_enacted_date || '-'}
            </Descriptions.Item>
          </Descriptions>
        </div>
      ))}
    </div>
  )
}
