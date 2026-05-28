import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Empty, Input, List, Segmented, Spin, Tag, Typography } from 'antd'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { draftingApi, CriterionCell } from '../../services/draftingApi'

const { Title, Paragraph, Text } = Typography

const SOURCE_LABEL: Record<string, string> = {
  ebansimsa: '입안심사 기준',
  jungbigijun: '자치법규 정비기준',
}

/**
 * 입안심사 기준(위키) 뷰어 — ebansimsa/jungbigijun 기준서를 사람이 열람.
 * 백엔드 /drafting/criteria(목록) + /drafting/criteria/content(본문) 사용.
 * AI 검증·작성이 인용하는 바로 그 기준 원문을 담당자가 직접 확인할 수 있게 한다.
 */
export default function DraftingWiki() {
  const [source, setSource] = useState<'ebansimsa' | 'jungbigijun'>('ebansimsa')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<string | null>(null) // registry id

  const { data: criteria, isLoading } = useQuery({
    queryKey: ['drafting', 'criteria'],
    queryFn: draftingApi.listCriteria,
  })

  const filtered = useMemo(() => {
    const list = (criteria ?? []).filter((c) => c.source === source)
    const q = search.trim().toLowerCase()
    const matched = q
      ? list.filter(
          (c) =>
            c.criterion_id.toLowerCase().includes(q) ||
            (c.title ?? '').toLowerCase().includes(q),
        )
      : list
    // 코드 자연 정렬 (2.1.2 < 2.1.10)
    return [...matched].sort((a, b) =>
      a.criterion_id.localeCompare(b.criterion_id, undefined, { numeric: true }),
    )
  }, [criteria, source, search])

  const { data: content, isFetching: contentLoading } = useQuery({
    queryKey: ['drafting', 'criterion-content', selected],
    queryFn: () => draftingApi.getCriterionContent(selected!),
    enabled: !!selected,
  })

  const html = useMemo(() => {
    if (!content) return ''
    return DOMPurify.sanitize(marked.parse(content) as string)
  }, [content])

  const selectCriterion = (c: CriterionCell) => setSelected(`${c.source}/${c.criterion_id}`)

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>
        입안심사 기준
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        AI 작성·검증이 근거로 인용하는 입안심사·정비기준 원문을 직접 열람합니다.
      </Paragraph>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        {/* 좌: 기준 목록 */}
        <Card size="small" style={{ width: 340, flexShrink: 0 }}>
          <Segmented
            block
            value={source}
            onChange={(v) => {
              setSource(v as 'ebansimsa' | 'jungbigijun')
              setSelected(null)
            }}
            options={[
              { label: '입안심사', value: 'ebansimsa' },
              { label: '정비기준', value: 'jungbigijun' },
            ]}
          />
          <Input.Search
            placeholder="번호·제목 검색 (예: 2.1.4, 정의)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ marginTop: 8 }}
            allowClear
          />
          <div style={{ maxHeight: 'calc(100vh - 320px)', overflow: 'auto', marginTop: 8 }}>
            <List
              size="small"
              loading={isLoading}
              dataSource={filtered}
              locale={{ emptyText: '결과 없음' }}
              renderItem={(c) => {
                const rid = `${c.source}/${c.criterion_id}`
                return (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      paddingInline: 8,
                      background: selected === rid ? '#e6f4ff' : undefined,
                    }}
                    onClick={() => selectCriterion(c)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Tag color="geekblue" style={{ marginInlineEnd: 2 }}>
                        {c.criterion_id}
                      </Tag>
                      <Text>{c.title}</Text>
                    </div>
                  </List.Item>
                )
              }}
            />
          </div>
        </Card>

        {/* 우: 본문 */}
        <Card
          size="small"
          style={{ flex: 1, minWidth: 0 }}
          title={selected ? `${SOURCE_LABEL[source]} · ${selected.split('/')[1]}` : SOURCE_LABEL[source]}
        >
          {!selected ? (
            <Empty description="왼쪽에서 기준을 선택하세요" />
          ) : contentLoading ? (
            <Spin />
          ) : (
            <div
              className="wiki-markdown"
              style={{ maxHeight: 'calc(100vh - 280px)', overflow: 'auto', lineHeight: 1.7 }}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          )}
        </Card>
      </div>
    </div>
  )
}
