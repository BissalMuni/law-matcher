import { Alert, Button, Card, Col, Empty, Row, Select, Space, Spin, Typography } from 'antd'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ordinanceApi, useDetectionResults, useRunDetection } from '../services/api'
import TabA_LawCompare from '../components/detection/TabA_LawCompare'
import TabB_ArticleCompare from '../components/detection/TabB_ArticleCompare'
import TabC_ReasonCompare from '../components/detection/TabC_ReasonCompare'
import DetectionSummary from '../components/detection/DetectionSummary'

const { Title } = Typography

export default function DetectionCompare() {
  const [search, setSearch] = useState('')
  const [selectedOrdinanceId, setSelectedOrdinanceId] = useState<number | undefined>(undefined)

  const { data: ordinanceData, isLoading: ordinancesLoading } = useQuery({
    queryKey: ['detection-compare', 'ordinances', search],
    queryFn: () => ordinanceApi.getList({ page: 1, size: 50, search }),
  })

  const ordinances = ordinanceData?.items || []

  const { data: parentLaws, isLoading: parentLawsLoading } = useQuery({
    queryKey: ['detection-compare', 'parent-laws', selectedOrdinanceId],
    queryFn: () => ordinanceApi.getParentLaws(selectedOrdinanceId as number),
    enabled: !!selectedOrdinanceId,
  })

  const { data: detectionResults, isLoading: detectionLoading } = useDetectionResults(selectedOrdinanceId, !!selectedOrdinanceId)
  const runDetection = useRunDetection(selectedOrdinanceId || 0)

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Title level={4}>탭 비교</Title>

      <Card>
        <Space wrap>
          <Select
            showSearch
            style={{ minWidth: 360 }}
            placeholder="조례 선택"
            loading={ordinancesLoading}
            value={selectedOrdinanceId}
            onSearch={setSearch}
            filterOption={false}
            onChange={(value) => setSelectedOrdinanceId(value)}
            options={ordinances.map((item: any) => ({ label: item.name, value: item.id }))}
          />
          <Button
            type="primary"
            disabled={!selectedOrdinanceId}
            loading={runDetection.isPending}
            onClick={() => runDetection.mutate(undefined)}
          >
            전체 판별 실행
          </Button>
        </Space>
      </Card>

      {!selectedOrdinanceId ? (
        <Empty description="비교할 조례를 선택하세요." />
      ) : (
        <>
          {runDetection.isError && (
            <Alert
              type="error"
              showIcon
              message="판별 실행 중 오류가 발생했습니다."
              description={
                runDetection.error instanceof Error ? runDetection.error.message : '서버 응답을 확인해주세요.'
              }
            />
          )}
          <DetectionSummary detectionResults={detectionResults} />

          {detectionLoading || parentLawsLoading ? (
            <Spin />
          ) : (
            <Row gutter={[12, 12]}>
              <Col xs={24} xl={8}>
                <Card title="법령비교">
                  <TabA_LawCompare
                    ordinanceId={selectedOrdinanceId}
                    parentLaws={parentLaws || []}
                    enabled
                  />
                </Card>
              </Col>
              <Col xs={24} xl={8}>
                <Card title="조문비교">
                  <TabB_ArticleCompare ordinanceId={selectedOrdinanceId} enabled />
                </Card>
              </Col>
              <Col xs={24} xl={8}>
                <Card title="개정이유비교">
                  <TabC_ReasonCompare
                    ordinanceId={selectedOrdinanceId}
                    parentLaws={parentLaws || []}
                    enabled
                  />
                </Card>
              </Col>
            </Row>
          )}
        </>
      )}
    </Space>
  )
}
