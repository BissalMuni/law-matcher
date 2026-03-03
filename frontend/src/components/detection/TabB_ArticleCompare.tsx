import { Alert, Button, Empty, Space, Spin, Table, Tag, Typography } from 'antd'
import { useDetectionResults, useRunDetection } from '../../services/api'

const { Text } = Typography

interface TabBArticleCompareProps {
  ordinanceId: number
  enabled?: boolean
}

interface ChangedArticleItem {
  article_no: string
  revision_type_detail?: string | null
  change_flag?: string | null
}

interface ArticleChangeDetail {
  changed_articles?: ChangedArticleItem[]
  mapped_changed_articles?: string[]
  new_articles?: string[]
  mapped_articles?: string[]
}

export default function TabB_ArticleCompare({ ordinanceId, enabled = true }: TabBArticleCompareProps) {
  const { data, isLoading, isError, error } = useDetectionResults(ordinanceId, enabled)
  const runDetection = useRunDetection(ordinanceId)

  if (!enabled) {
    return null
  }

  if (isLoading) {
    return <Spin />
  }

  if (isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="조문비교 결과를 불러오지 못했습니다."
        description={error instanceof Error ? error.message : '알 수 없는 오류'}
      />
    )
  }

  const articleResult = data?.results?.find((result) => result.method === 'article_change')
  const byLaw = (articleResult?.detail?.by_law as ArticleChangeDetail[] | undefined) || []

  const changedArticlesMap = new Map<string, ChangedArticleItem>()
  const mappedChanged = new Set<string>()
  const newArticles = new Set<string>()
  const mappedArticles = new Set<string>()

  byLaw.forEach((detail) => {
    ;(detail.changed_articles || []).forEach((item) => {
      if (item.article_no && !changedArticlesMap.has(item.article_no)) {
        changedArticlesMap.set(item.article_no, item)
      }
    })
    ;(detail.mapped_changed_articles || []).forEach((item) => mappedChanged.add(item))
    ;(detail.new_articles || []).forEach((item) => newArticles.add(item))
    ;(detail.mapped_articles || []).forEach((item) => mappedArticles.add(item))
  })

  const changedRows = Array.from(changedArticlesMap.values())

  if (!articleResult || changedRows.length === 0) {
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Empty description="조문 변경 결과가 없습니다." />
        <Button
          type="primary"
          loading={runDetection.isPending}
          onClick={() => runDetection.mutate(['article_change'])}
        >
          판별 실행
        </Button>
      </Space>
    )
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type={mappedChanged.size > 0 ? 'warning' : 'success'}
        showIcon
        message={
          mappedChanged.size > 0
            ? `매핑 조문 변경 감지: ${mappedChanged.size}건`
            : '매핑 조문 변경 없음'
        }
      />

      {newArticles.size > 0 && (
        <div>
          <Text strong>신설 조문 (매핑 검토 필요)</Text>
          <div style={{ marginTop: 8 }}>
            {Array.from(newArticles).map((articleNo) => (
              <Tag color="blue" key={articleNo}>
                {articleNo}
              </Tag>
            ))}
          </div>
        </div>
      )}

      <Table
        rowKey={(record) => record.article_no}
        size="small"
        pagination={false}
        dataSource={changedRows}
        columns={[
          {
            title: '조문번호',
            dataIndex: 'article_no',
            key: 'article_no',
            render: (value: string) =>
              mappedChanged.has(value) ? <Text strong style={{ color: '#cf1322' }}>{value}</Text> : value,
          },
          {
            title: '제개정유형',
            dataIndex: 'revision_type_detail',
            key: 'revision_type_detail',
            width: 140,
            render: (value: string | null) => value || '-',
          },
          {
            title: '변경여부',
            dataIndex: 'change_flag',
            key: 'change_flag',
            width: 120,
            render: (value: string | null) =>
              value === 'Y' ? <Tag color="red">Y</Tag> : <Tag>N</Tag>,
          },
          {
            title: '매핑상태',
            key: 'mapping_status',
            width: 160,
            render: (_, record: ChangedArticleItem) => {
              if (mappedChanged.has(record.article_no)) {
                return <Tag color="red">매핑 조문 변경</Tag>
              }
              if (mappedArticles.has(record.article_no)) {
                return <Tag color="orange">매핑 조문</Tag>
              }
              return <Tag>비매핑 조문</Tag>
            },
          },
        ]}
      />
    </Space>
  )
}
