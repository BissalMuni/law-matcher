import { Card, Col, Descriptions, Row, Tag, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { DetectionResultsResponse } from '../../types/api'

const { Text } = Typography

interface DetectionSummaryProps {
  detectionResults?: DetectionResultsResponse
}

const METHOD_LABEL: Record<string, string> = {
  proclaimed_date: '법령비교',
  article_change: '조문비교',
  revision_reason: '개정이유비교',
}

export default function DetectionSummary({ detectionResults }: DetectionSummaryProps) {
  const results = detectionResults?.results || []
  const activeResults = results.filter((result) => result.method in METHOD_LABEL)
  const values = activeResults.map((result) => result.needs_revision)
  const allEqual = values.length <= 1 || values.every((value) => value === values[0])

  return (
    <Card
      title="판별 요약"
      extra={
        <Tag color={allEqual ? 'green' : 'orange'}>
          {allEqual ? '3탭 결과 일치' : '3탭 결과 불일치'}
        </Tag>
      }
    >
      <Row gutter={[12, 12]}>
        {activeResults.map((result) => (
          <Col xs={24} md={8} key={result.method}>
            <Card size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="방식">{METHOD_LABEL[result.method] || result.method}</Descriptions.Item>
                <Descriptions.Item label="판정">
                  {result.needs_revision ? (
                    <Text type="danger">
                      <CloseCircleOutlined /> 개정 검토 필요
                    </Text>
                  ) : (
                    <Text type="success">
                      <CheckCircleOutlined /> 최신 상태
                    </Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        ))}
      </Row>
    </Card>
  )
}
