import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Empty, Space, Spin, Tag, Tooltip, Typography, message } from 'antd'
import { ThunderboltOutlined, AimOutlined } from '@ant-design/icons'
import {
  CriterionCell,
  draftingApi,
  DraftingSection,
  ValidationCellResult,
} from '../../services/draftingApi'

const { Text, Paragraph } = Typography

const VERDICT_TAG: Record<string, { text: string; color: string }> = {
  pass: { text: '적합', color: 'green' },
  fail: { text: '부적합', color: 'red' },
  na: { text: '해당없음', color: 'default' },
  pending: { text: '미판정', color: 'gold' },
}

interface Props {
  section: DraftingSection
  projectId: number
}

/**
 * 조문 중심 핵심 UI — 이 조문에 적용되는 기준을 칩으로 보여주고,
 * 칩을 누르면 그 기준에 따른 AI 분석(판정·사유·제안)을 즉시 표시한다.
 */
export default function ArticleCriteriaBar({ section, projectId }: Props) {
  const queryClient = useQueryClient()
  const chips = section.mapped_criteria ?? []
  const [activeKey, setActiveKey] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Record<string, ValidationCellResult>>({})

  const mapMutation = useMutation({
    mutationFn: () => draftingApi.mapSectionCriteria(section.id),
    onSuccess: () => {
      message.success('적용 기준을 매핑했습니다.')
      queryClient.invalidateQueries({ queryKey: ['drafting', 'project', projectId] })
    },
    onError: () => message.error('기준 매핑 실패 (ANTHROPIC_API_KEY 확인)'),
  })

  const analyzeMutation = useMutation({
    mutationFn: async (c: CriterionCell) => {
      const res = await draftingApi.validatePrecise({
        articles: [
          {
            article_id: section.article_label || `제${section.article_no}조`,
            title: section.title,
            text: section.body,
          },
        ],
        criteria: [c],
      })
      return res.results[0]
    },
    onSuccess: (result, c) => {
      const key = `${c.source}/${c.criterion_id}`
      setAnalysis((prev) => ({ ...prev, [key]: result }))
      // 검증 결과 영속화 (조문별)
      draftingApi
        .saveValidations(section.id, [
          {
            criterion_id: result.criterion_id,
            source: result.source,
            verdict: result.verdict,
            severity: result.severity,
            reason: result.reason,
            suggestion: result.suggestion,
          },
        ], false)
        .catch(() => undefined)
    },
    onError: () => message.error('분석 실패 (ANTHROPIC_API_KEY 확인)'),
  })

  const clickChip = (c: CriterionCell) => {
    const key = `${c.source}/${c.criterion_id}`
    setActiveKey(key)
    if (!analysis[key]) analyzeMutation.mutate(c)
  }

  const active = activeKey ? analysis[activeKey] : null

  return (
    <Card size="small" style={{ marginTop: 8 }} styles={{ body: { padding: 12 } }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Text strong style={{ marginRight: 4 }}>
          적용 기준
        </Text>
        {chips.length === 0 ? (
          <Button
            size="small"
            icon={<AimOutlined />}
            loading={mapMutation.isPending}
            onClick={() => mapMutation.mutate()}
          >
            기준 매핑
          </Button>
        ) : (
          <>
            {chips.map((c) => {
              const key = `${c.source}/${c.criterion_id}`
              const verdict = analysis[key]?.verdict
              const color =
                activeKey === key
                  ? 'blue'
                  : verdict
                    ? VERDICT_TAG[verdict]?.color ?? 'geekblue'
                    : 'geekblue'
              return (
                <Tooltip key={key} title={c.title ?? ''}>
                  <Tag
                    color={color}
                    style={{ cursor: 'pointer', marginBottom: 4 }}
                    onClick={() => clickChip(c)}
                  >
                    {c.source}/{c.criterion_id}
                    {verdict && ` · ${VERDICT_TAG[verdict]?.text}`}
                  </Tag>
                </Tooltip>
              )
            })}
            <Button
              size="small"
              type="text"
              icon={<AimOutlined />}
              loading={mapMutation.isPending}
              onClick={() => mapMutation.mutate()}
            >
              재매핑
            </Button>
          </>
        )}
      </div>

      {activeKey && (
        <div style={{ marginTop: 10 }}>
          {analyzeMutation.isPending && !active ? (
            <Spin size="small" />
          ) : active ? (
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Space>
                <Tag color="geekblue">{activeKey}</Tag>
                <Tag color={VERDICT_TAG[active.verdict]?.color}>
                  {VERDICT_TAG[active.verdict]?.text ?? active.verdict}
                </Tag>
              </Space>
              {active.reason && (
                <Paragraph style={{ marginBottom: 0 }}>
                  <Text strong>사유: </Text>
                  {active.reason}
                </Paragraph>
              )}
              {active.suggestion && (
                <Alert
                  type="warning"
                  showIcon
                  icon={<ThunderboltOutlined />}
                  message="수정 제안"
                  description={active.suggestion}
                />
              )}
            </Space>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="분석 결과 없음" />
          )}
        </div>
      )}
    </Card>
  )
}
