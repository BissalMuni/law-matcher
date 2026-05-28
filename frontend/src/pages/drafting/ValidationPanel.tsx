import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Empty,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  CriterionCell,
  draftingApi,
  DraftingSection,
  ValidationCellResult,
} from '../../services/draftingApi'

const { Text } = Typography

const VERDICT_TAG: Record<string, { text: string; color: string }> = {
  pass: { text: '적합', color: 'green' },
  fail: { text: '부적합', color: 'red' },
  na: { text: '해당없음', color: 'default' },
  pending: { text: '미판정', color: 'gold' },
}

interface Props {
  sections: DraftingSection[]
}

/** 정밀 검증 매트릭스 — 선택한 기준 × 조문을 셀 단위로 판단 */
const rowKeyOf = (r: ValidationCellResult) =>
  `${r.article_id}|${r.source}/${r.criterion_id}`

export default function ValidationPanel({ sections }: Props) {
  const [selectedCriteria, setSelectedCriteria] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<ValidationCellResult[]>([])
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
  const [summary, setSummary] = useState<{ total: number; filled: number; complete: boolean } | null>(
    null,
  )

  const { data: catalog } = useQuery({
    queryKey: ['drafting', 'criteria'],
    queryFn: draftingApi.listCriteria,
  })

  const criteriaOptions = useMemo(
    () =>
      (catalog ?? []).map((c) => ({
        label: `${c.source}/${c.criterion_id} ${c.title ?? ''}`,
        value: `${c.source}/${c.criterion_id}`,
      })),
    [catalog],
  )

  const run = async () => {
    if (sections.length === 0 || selectedCriteria.length === 0) {
      message.warning('검증할 조문과 기준을 선택하세요.')
      return
    }
    setRunning(true)
    try {
      const criteria: CriterionCell[] = selectedCriteria.map((v) => {
        const [source, criterion_id] = v.split('/')
        const found = catalog?.find((c) => `${c.source}/${c.criterion_id}` === v)
        return { source: source as CriterionCell['source'], criterion_id, title: found?.title }
      })
      const articles = sections.map((s) => ({
        article_id: s.article_label || `제${s.article_no}조`,
        title: s.title,
        text: s.body,
      }))
      const res = await draftingApi.validatePrecise({ articles, criteria })
      setResults(res.results)
      // 부적합 행은 사유가 바로 보이도록 자동으로 펼친다
      setExpandedKeys(res.results.filter((r) => r.verdict === 'fail').map(rowKeyOf))
      setSummary({ total: res.total_cells, filled: res.filled_cells, complete: res.complete })
    } catch {
      message.error('검증 실행에 실패했습니다. (ANTHROPIC_API_KEY 설정 확인)')
    } finally {
      setRunning(false)
    }
  }

  const columns: ColumnsType<ValidationCellResult> = [
    { title: '조문', dataIndex: 'article_id', key: 'article_id', width: 120, ellipsis: true },
    {
      title: '기준',
      key: 'criterion',
      width: 110,
      render: (_, r) => (
        <Tag color="geekblue">
          {r.source}/{r.criterion_id}
        </Tag>
      ),
    },
    {
      title: '판정',
      dataIndex: 'verdict',
      key: 'verdict',
      width: 80,
      filters: [
        { text: '적합', value: 'pass' },
        { text: '부적합', value: 'fail' },
        { text: '해당없음', value: 'na' },
        { text: '미판정', value: 'pending' },
      ],
      onFilter: (value, r) => r.verdict === value,
      render: (v: string, r) => {
        const t = VERDICT_TAG[v] ?? { text: v, color: 'default' }
        const tag = <Tag color={t.color}>{t.text}</Tag>
        return r.reason ? <Tooltip title={r.reason}>{tag}</Tooltip> : tag
      },
    },
  ]

  const expandedRowRender = (r: ValidationCellResult) => (
    <Space direction="vertical" size={4} style={{ width: '100%' }}>
      {r.reason ? (
        <div>
          <Text strong type={r.verdict === 'fail' ? 'danger' : undefined}>사유: </Text>
          <Text>{r.reason}</Text>
        </div>
      ) : (
        <Text type="secondary">상세 사유 없음</Text>
      )}
      {r.suggestion && (
        <div>
          <Text strong type="success">수정 제안: </Text>
          <Text>{r.suggestion}</Text>
        </div>
      )}
    </Space>
  )

  if (sections.length === 0) {
    return <Empty description="검증할 조문이 없습니다. 본칙에 조문을 먼저 작성하세요." />
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <div>
        <Text strong>검증 기준 선택</Text>
        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="입안심사·정비 기준을 선택하세요"
          style={{ width: '100%', marginTop: 8 }}
          value={selectedCriteria}
          onChange={setSelectedCriteria}
          options={criteriaOptions}
          maxTagCount="responsive"
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
        />
      </div>
      <Space>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={running}
          onClick={run}
          disabled={selectedCriteria.length === 0}
        >
          정밀 검증 실행 ({sections.length}조 × {selectedCriteria.length}기준)
        </Button>
      </Space>

      {summary && (
        <Space size="large">
          <Statistic title="총 셀" value={summary.total} />
          <Statistic title="판정 완료" value={summary.filled} />
          <Statistic
            title="누락 0건"
            valueRender={() =>
              summary.complete ? (
                <Tag color="green">완료</Tag>
              ) : (
                <Tag color="gold">미완료</Tag>
              )
            }
          />
        </Space>
      )}

      {results.length > 0 && (
        <>
          {results.some((r) => r.verdict === 'fail') && (
            <Alert
              type="warning"
              showIcon
              message={`부적합 ${results.filter((r) => r.verdict === 'fail').length}건이 발견되었습니다.`}
            />
          )}
          <Table
            rowKey={rowKeyOf}
            size="small"
            columns={columns}
            dataSource={results}
            pagination={{ pageSize: 20 }}
            expandable={{
              expandedRowRender,
              rowExpandable: (r) => Boolean(r.reason || r.suggestion),
              expandedRowKeys: expandedKeys,
              onExpandedRowsChange: (keys) => setExpandedKeys(keys as string[]),
            }}
          />
        </>
      )}
    </Space>
  )
}
