import { useRef, useState } from 'react'
import { Button, Card, Empty, Input, Space, Tag, Typography, message } from 'antd'
import { SendOutlined, ImportOutlined } from '@ant-design/icons'
import { draftingApi, DraftingStage, ParentLaw, streamDraft } from '../../services/draftingApi'

const { Text, Paragraph } = Typography

interface Props {
  stage: DraftingStage | null
  parentLaws: ParentLaw[]
  onApply: (text: string) => void
}

/** 단계별 AI 작성 패널 — 의도 입력 → SSE 스트리밍 → 에디터 적용 */
export default function DraftingChat({ stage, parentLaws, onApply }: Props) {
  const [intent, setIntent] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [output, setOutput] = useState('')
  const [citations, setCitations] = useState<string[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const run = async () => {
    if (!stage || !intent.trim()) return
    setStreaming(true)
    setOutput('')
    setCitations([])
    const ctrl = new AbortController()
    abortRef.current = ctrl

    const parentLawStrings = parentLaws.map((p) =>
      p.related_articles
        ? `${p.law_name} (${p.law_type}) — 관련 조문: ${p.related_articles}`
        : `${p.law_name} (${p.law_type})`,
    )

    await streamDraft(
      {
        stage_key: stage.key,
        intent: intent.trim(),
        wiki_refs: stage.wiki_ref ? [{ criterion_id: stage.wiki_ref }] : [],
        parent_laws: parentLawStrings,
      },
      {
        onCitations: (c) => setCitations(c),
        onDelta: (t) => setOutput((prev) => prev + t),
        onDone: () => setStreaming(false),
        onError: () => {
          setStreaming(false)
          message.error('AI 작성 중 오류가 발생했습니다. (ANTHROPIC_API_KEY 설정 확인)')
        },
      },
      ctrl.signal,
    )
    // 작성 로그 저장 (실패해도 무시)
    try {
      await draftingApi.addMessage(stage.id, { role: 'user', content: intent.trim() })
    } catch {
      /* noop */
    }
  }

  const stop = () => {
    abortRef.current?.abort()
    setStreaming(false)
  }

  if (!stage) {
    return <Empty description="단계를 선택하세요" />
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <div>
        <Text type="secondary">
          단계: <Tag>{stage.label}</Tag>
          {stage.wiki_ref && <Tag color="geekblue">근거 {stage.wiki_ref}</Tag>}
        </Text>
      </div>
      <Input.TextArea
        rows={3}
        placeholder="이 단계에서 작성할 내용의 의도를 적어주세요. 예: 청년 창업 지원의 목적을 명확히 규정"
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
      />
      <Space>
        {!streaming ? (
          <Button type="primary" icon={<SendOutlined />} onClick={run} disabled={!intent.trim()}>
            AI 작성
          </Button>
        ) : (
          <Button danger onClick={stop}>
            중지
          </Button>
        )}
        {output && !streaming && (
          <Button icon={<ImportOutlined />} onClick={() => onApply(output)}>
            에디터에 적용
          </Button>
        )}
      </Space>

      {(output || streaming) && (
        <Card size="small" title="AI 작성 결과" styles={{ body: { maxHeight: 320, overflow: 'auto' } }}>
          <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 8 }}>
            {output || '생성 중…'}
          </Paragraph>
          {citations.length > 0 && (
            <div>
              <Text type="secondary">근거: </Text>
              {citations.map((c) => (
                <Tag key={c} color="blue">
                  {c}
                </Tag>
              ))}
            </div>
          )}
        </Card>
      )}
    </Space>
  )
}
