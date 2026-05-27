import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Empty,
  Input,
  List,
  Space,
  Spin,
  Steps,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlusOutlined,
  SaveOutlined,
  DeleteOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  BookOutlined,
} from '@ant-design/icons'
import {
  draftingApi,
  DraftingSection,
  DraftingStage,
} from '../../services/draftingApi'
import DraftingChat from './DraftingChat'
import ValidationPanel from './ValidationPanel'
import MonacoEditor from '../../components/drafting/MonacoEditor'

const { Title, Text, Paragraph } = Typography

const STAGE_STATUS_DESC: Record<string, string> = {
  locked: '잠금',
  available: '작성 가능',
  in_progress: '작성 중',
  validating: '검증 중',
  confirmed: '확정',
  stale: '재검토 필요',
  failed: '실패',
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function DraftingWorkspace() {
  const { id } = useParams<{ id: string }>()
  const projectId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [selectedStageId, setSelectedStageId] = useState<number | null>(null)
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null)
  const [draftLabel, setDraftLabel] = useState('')
  const [draftTitle, setDraftTitle] = useState('')
  const [draftBody, setDraftBody] = useState('')

  const { data: project, isLoading } = useQuery({
    queryKey: ['drafting', 'project', projectId],
    queryFn: () => draftingApi.getProject(projectId),
    enabled: !!projectId,
  })

  const stages = project?.stages ?? []
  const sections = project?.sections ?? []

  // 초기 선택
  useEffect(() => {
    if (stages.length && selectedStageId === null) {
      const main = stages.find((s) => s.key === 'main') ?? stages[0]
      setSelectedStageId(main.id)
    }
  }, [stages, selectedStageId])

  const stageSections = useMemo(
    () => sections.filter((s) => s.stage_id === selectedStageId).sort((a, b) => a.sort_order - b.sort_order),
    [sections, selectedStageId],
  )

  const selectSection = (sec: DraftingSection) => {
    setSelectedSectionId(sec.id)
    setDraftLabel(sec.article_label ?? '')
    setDraftTitle(sec.title)
    setDraftBody(sec.body)
  }

  const upsertMutation = useMutation({
    mutationFn: (payload: Partial<DraftingSection> & { project_id: number; stage_id: number }) =>
      draftingApi.upsertSection(payload),
    onSuccess: () => {
      message.success('저장되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['drafting', 'project', projectId] })
    },
    onError: () => message.error('저장에 실패했습니다.'),
  })

  const deleteMutation = useMutation({
    mutationFn: (sectionId: number) => draftingApi.deleteSection(sectionId),
    onSuccess: () => {
      message.success('조문이 삭제되었습니다.')
      setSelectedSectionId(null)
      queryClient.invalidateQueries({ queryKey: ['drafting', 'project', projectId] })
    },
  })

  const saveSection = () => {
    if (!selectedStageId) return
    upsertMutation.mutate({
      id: selectedSectionId ?? undefined,
      project_id: projectId,
      stage_id: selectedStageId,
      article_label: draftLabel,
      title: draftTitle,
      body: draftBody,
      article_no: selectedSectionId
        ? stageSections.find((s) => s.id === selectedSectionId)?.article_no ?? 0
        : stageSections.length + 1,
      sort_order: selectedSectionId
        ? stageSections.find((s) => s.id === selectedSectionId)?.sort_order ?? 0
        : stageSections.length,
    })
  }

  const newSection = () => {
    setSelectedSectionId(null)
    setDraftLabel('')
    setDraftTitle('')
    setDraftBody('')
  }

  const exportDoc = async (format: 'docx' | 'pdf') => {
    if (!project) return
    try {
      const blob = await draftingApi.exportDocument({
        project_title: project.title,
        municipality: project.municipality,
        sections: sections
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((s, i) => ({
            article_label: s.article_label || `제${s.article_no}조`,
            title: s.title,
            body: s.body,
            order: i,
          })),
        format,
      })
      downloadBlob(blob, `${project.title}.${format}`)
    } catch {
      message.error('내보내기에 실패했습니다.')
    }
  }

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  }
  if (!project) {
    return <Empty description="프로젝트를 찾을 수 없습니다." />
  }

  const selectedStage: DraftingStage | null =
    stages.find((s) => s.id === selectedStageId) ?? null

  return (
    <div>
      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/drafting')}>
            목록
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {project.title}
          </Title>
          <Tag color="blue">{project.municipality}</Tag>
        </Space>
        <Space>
          <Button icon={<FileWordOutlined />} onClick={() => exportDoc('docx')}>
            DOCX
          </Button>
          <Button icon={<FilePdfOutlined />} onClick={() => exportDoc('pdf')}>
            PDF
          </Button>
        </Space>
      </div>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        {/* 좌: 단계 */}
        <Card size="small" title="단계" style={{ width: 220, flexShrink: 0 }}>
          <Steps
            direction="vertical"
            size="small"
            current={stages.findIndex((s) => s.id === selectedStageId)}
            items={stages.map((s) => ({
              title: (
                <a onClick={() => setSelectedStageId(s.id)}>{s.label}</a>
              ),
              description: STAGE_STATUS_DESC[s.status] ?? s.status,
            }))}
          />
        </Card>

        {/* 중: 조문 편집 */}
        <Card
          size="small"
          title={`조문 — ${selectedStage?.label ?? ''}`}
          style={{ flex: 1, minWidth: 0 }}
          extra={
            <Button size="small" icon={<PlusOutlined />} onClick={newSection}>
              새 조문
            </Button>
          }
        >
          <div style={{ display: 'flex', gap: 12 }}>
            <List
              size="small"
              style={{ width: 200, flexShrink: 0, maxHeight: 480, overflow: 'auto' }}
              bordered
              dataSource={stageSections}
              locale={{ emptyText: '조문 없음' }}
              renderItem={(sec) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background: selectedSectionId === sec.id ? '#e6f4ff' : undefined,
                  }}
                  onClick={() => selectSection(sec)}
                >
                  <Space direction="vertical" size={0}>
                    <Text strong>{sec.article_label || `제${sec.article_no}조`}</Text>
                    {sec.change_type && sec.change_type !== 'unchanged' && (
                      <Tag color="orange">{sec.change_type}</Tag>
                    )}
                  </Space>
                </List.Item>
              )}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Input
                  placeholder="조문 라벨 (예: 제1조(목적))"
                  value={draftLabel}
                  onChange={(e) => setDraftLabel(e.target.value)}
                />
                <Input
                  placeholder="조 제목 (예: 목적)"
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                />
                <MonacoEditor value={draftBody} onChange={setDraftBody} height={340} />
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    loading={upsertMutation.isPending}
                    onClick={saveSection}
                  >
                    저장
                  </Button>
                  {selectedSectionId && (
                    <Button
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => deleteMutation.mutate(selectedSectionId)}
                    >
                      삭제
                    </Button>
                  )}
                </Space>
              </Space>
            </div>
          </div>
        </Card>

        {/* 우: 도구 패널 */}
        <Card size="small" style={{ width: 420, flexShrink: 0 }}>
          <Tabs
            defaultActiveKey="parent-laws"
            items={[
              {
                key: 'parent-laws',
                label: '상위법령',
                children:
                  project.parent_laws.length === 0 ? (
                    <Empty description="연결된 상위법령이 없습니다." />
                  ) : (
                    <List
                      size="small"
                      dataSource={project.parent_laws}
                      renderItem={(p) => (
                        <List.Item>
                          <List.Item.Meta
                            avatar={<BookOutlined />}
                            title={p.law_name}
                            description={
                              <Space size={4} wrap>
                                <Tag>{p.law_type}</Tag>
                                {p.related_articles && (
                                  <Text type="secondary">관련: {p.related_articles}</Text>
                                )}
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ),
              },
              {
                key: 'ai',
                label: 'AI 작성',
                children: (
                  <DraftingChat
                    stage={selectedStage}
                    parentLaws={project.parent_laws}
                    onApply={(text) => {
                      setDraftBody((prev) => (prev ? `${prev}\n${text}` : text))
                      message.info('AI 작성 결과를 에디터에 적용했습니다. 저장을 눌러 반영하세요.')
                    }}
                  />
                ),
              },
              {
                key: 'validate',
                label: '검증',
                children: <ValidationPanel sections={sections} />,
              },
            ]}
          />
        </Card>
      </div>

      <Paragraph type="secondary" style={{ marginTop: 16 }}>
        <Tooltip title="개정 모드에서는 등록 조례의 원문이 original_body로 보존됩니다.">
          <Text type="secondary">종류: {project.kind} · 조문 {sections.length}개</Text>
        </Tooltip>
      </Paragraph>
    </div>
  )
}
