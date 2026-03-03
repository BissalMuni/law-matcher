import { Alert, Button, Empty, Space, Spin, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'
import { useDetectionResults, useRunDetection } from '../../services/api'

const { Text } = Typography

interface ParentLawItem {
  id: number
  law_internal_id?: number
  law_name: string
  law_type: string
  proclaimed_date?: string
}

interface ProclaimedDateDetail {
  law_id?: number
  law_name?: string
  law_proclaimed_date?: string | null
  days_diff?: number | null
  needs_revision?: boolean
}

interface TabALawCompareProps {
  ordinanceId: number
  parentLaws: ParentLawItem[]
  enabled?: boolean
}

function toDateValue(value?: string | null) {
  if (!value) return 0
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.valueOf() : 0
}

export default function TabA_LawCompare({ ordinanceId, parentLaws, enabled = true }: TabALawCompareProps) {
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
        message="법령비교 결과를 불러오지 못했습니다."
        description={error instanceof Error ? error.message : '알 수 없는 오류'}
      />
    )
  }

  const proclaimedResult = data?.results?.find((result) => result.method === 'proclaimed_date')
  const byLaw = (proclaimedResult?.detail?.by_law as ProclaimedDateDetail[] | undefined) || []
  const byLawMap = new Map<number, ProclaimedDateDetail>()
  byLaw.forEach((item) => {
    if (item.law_id) {
      byLawMap.set(item.law_id, item)
    }
  })

  const mergedRows = parentLaws.map((law) => {
    const detected = byLawMap.get(law.law_internal_id || law.id)
    const daysDiff = typeof detected?.days_diff === 'number' ? detected.days_diff : null
    const needsRevision =
      typeof detected?.needs_revision === 'boolean'
        ? detected.needs_revision
        : typeof daysDiff === 'number'
          ? daysDiff > 0
          : false

    return {
      ...law,
      law_proclaimed_date: detected?.law_proclaimed_date || law.proclaimed_date || null,
      days_diff: daysDiff,
      needs_revision: needsRevision,
    }
  })

  const sortedRows = [...mergedRows].sort(
    (a, b) => toDateValue(b.law_proclaimed_date) - toDateValue(a.law_proclaimed_date)
  )

  if (!proclaimedResult || sortedRows.length === 0) {
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Empty description="판별 결과가 없습니다." />
        <Button
          type="primary"
          loading={runDetection.isPending}
          onClick={() => runDetection.mutate(['proclaimed_date'])}
        >
          판별 실행
        </Button>
      </Space>
    )
  }

  return (
    <Table
      rowKey={(row) => row.law_internal_id || row.id}
      size="small"
      pagination={false}
      dataSource={sortedRows}
      columns={[
        {
          title: '법령명',
          dataIndex: 'law_name',
          key: 'law_name',
        },
        {
          title: '법령유형',
          dataIndex: 'law_type',
          key: 'law_type',
          width: 100,
        },
        {
          title: '공포일자',
          dataIndex: 'law_proclaimed_date',
          key: 'law_proclaimed_date',
          width: 140,
          render: (value: string | null) => value || '-',
        },
        {
          title: '차이(일)',
          dataIndex: 'days_diff',
          key: 'days_diff',
          width: 120,
          render: (value: number | null) => (typeof value === 'number' ? value : '-'),
        },
        {
          title: '판별결과',
          dataIndex: 'needs_revision',
          key: 'needs_revision',
          width: 180,
          render: (value: boolean) =>
            value ? (
              <Tag color="red">개정 검토 필요</Tag>
            ) : (
              <Tag color="green">최신 상태</Tag>
            ),
        },
      ]}
      summary={(pageData) => {
        const needsRevisionCount = pageData.filter((row) => row.needs_revision).length
        return (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={5}>
              <Text strong>
                총 {pageData.length}건 중 {needsRevisionCount}건 개정 검토 필요
              </Text>
            </Table.Summary.Cell>
          </Table.Summary.Row>
        )
      }}
    />
  )
}
