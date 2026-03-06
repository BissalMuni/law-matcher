import { Tag } from 'antd'
import { RobotOutlined } from '@ant-design/icons'

interface AiLabelProps {
  providerName?: string
  modelName?: string
  showModel?: boolean
}

/**
 * "AI 생성" 라벨 배지 (Constitution VIII 필수)
 * AI가 생성한 콘텐츠에 붙여서 명확히 구분
 */
export default function AiLabel({ providerName, modelName, showModel = false }: AiLabelProps) {
  return (
    <Tag icon={<RobotOutlined />} color="purple">
      AI 생성
      {showModel && providerName && ` · ${providerName}`}
      {showModel && modelName && ` (${modelName})`}
    </Tag>
  )
}
