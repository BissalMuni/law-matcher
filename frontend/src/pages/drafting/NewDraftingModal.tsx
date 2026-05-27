import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Alert,
  Input,
  List,
  Modal,
  Radio,
  Segmented,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd'
import { BookOutlined } from '@ant-design/icons'
import {
  draftingApi,
  DraftingProject,
  ProjectKind,
  SourceOrdinance,
} from '../../services/draftingApi'

const { Text } = Typography

interface Props {
  open: boolean
  onClose: () => void
  onCreated: (project: DraftingProject) => void
}

export default function NewDraftingModal({ open, onClose, onCreated }: Props) {
  const [kind, setKind] = useState<ProjectKind>('amend_partial')
  const [title, setTitle] = useState('')
  const [municipality, setMunicipality] = useState('')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<SourceOrdinance | null>(null)

  const isAmend = kind === 'amend_partial' || kind === 'amend_full'

  useEffect(() => {
    if (!open) {
      setKind('amend_partial')
      setTitle('')
      setMunicipality('')
      setQuery('')
      setSearch('')
      setSelected(null)
    }
  }, [open])

  const { data: ordinances, isFetching } = useQuery({
    queryKey: ['drafting', 'source-ordinances', search],
    queryFn: () => draftingApi.listSourceOrdinances(search || undefined, 30),
    enabled: open && isAmend,
  })

  const { data: preview, isFetching: previewLoading } = useQuery({
    queryKey: ['drafting', 'source-preview', selected?.id],
    queryFn: () => draftingApi.previewSource(selected!.id),
    enabled: !!selected,
  })

  const createMutation = useMutation({
    mutationFn: () =>
      draftingApi.createProject({
        kind,
        title: title.trim(),
        municipality: municipality.trim(),
        ordinance_id: isAmend ? selected?.id ?? null : null,
        source_url: preview?.ordinance.detail_link ?? null,
      }),
    onSuccess: (project) => {
      message.success('입안 프로젝트를 생성했습니다.')
      onCreated(project)
    },
    onError: () => message.error('생성에 실패했습니다.'),
  })

  const canSubmit =
    title.trim() && municipality.trim() && (!isAmend || !!selected)

  const handleSelect = (o: SourceOrdinance) => {
    setSelected(o)
    if (!title) setTitle(o.name)
    if (!municipality && o.org_name) setMunicipality(o.org_name)
  }

  return (
    <Modal
      title="새 입안심사"
      open={open}
      onCancel={onClose}
      onOk={() => createMutation.mutate()}
      okText="생성"
      cancelText="취소"
      okButtonProps={{ disabled: !canSubmit, loading: createMutation.isPending }}
      width={760}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Text strong>입안 종류</Text>
          <div style={{ marginTop: 8 }}>
            <Segmented
              value={kind}
              onChange={(v) => setKind(v as ProjectKind)}
              options={[
                { label: '제정', value: 'enact' },
                { label: '일부개정', value: 'amend_partial' },
                { label: '전부개정', value: 'amend_full' },
              ]}
            />
          </div>
        </div>

        {isAmend && (
          <div>
            <Text strong>대상 조례 (law-matcher 등록분)</Text>
            <Input.Search
              placeholder="조례명 검색"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSearch={(v) => setSearch(v)}
              style={{ marginTop: 8 }}
              allowClear
            />
            <div style={{ maxHeight: 220, overflow: 'auto', marginTop: 8, border: '1px solid #f0f0f0', borderRadius: 6 }}>
              <List
                size="small"
                loading={isFetching}
                dataSource={ordinances ?? []}
                locale={{ emptyText: '검색 결과 없음' }}
                renderItem={(o) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      paddingInline: 12,
                      background: selected?.id === o.id ? '#e6f4ff' : undefined,
                    }}
                    onClick={() => handleSelect(o)}
                  >
                    <Radio checked={selected?.id === o.id} style={{ marginRight: 8 }} />
                    <List.Item.Meta
                      title={o.name}
                      description={
                        <Space size={4} wrap>
                          {o.category && <Tag>{o.category}</Tag>}
                          {o.org_name && <Text type="secondary">{o.org_name}</Text>}
                          <Tag color={o.has_text ? 'green' : 'default'}>
                            {o.has_text ? '본문 보유' : '본문 없음'}
                          </Tag>
                          <Tag icon={<BookOutlined />} color="geekblue">
                            상위법령 {o.parent_law_count}
                          </Tag>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>

            {selected && (
              <div style={{ marginTop: 8 }}>
                {previewLoading ? (
                  <Spin size="small" />
                ) : preview?.found ? (
                  <Alert
                    type="info"
                    showIcon
                    message={`조문 ${preview.section_count}개 · 상위법령 ${preview.parent_laws.length}건이 함께 로드됩니다.`}
                    description={
                      preview.parent_laws.length > 0 ? (
                        <Space wrap size={4}>
                          {preview.parent_laws.map((p) => (
                            <Tag key={p.law_id} color="blue">
                              {p.law_name}
                            </Tag>
                          ))}
                        </Space>
                      ) : (
                        <Text type="secondary">연결된 상위법령이 없습니다.</Text>
                      )
                    }
                  />
                ) : null}
              </div>
            )}
            {selected && !preview?.found && !previewLoading && (
              <Alert
                style={{ marginTop: 8 }}
                type="warning"
                showIcon
                message="이 조례는 본문이 없어 조문이 시드되지 않습니다. 관리에서 조례 본문을 먼저 동기화하세요."
              />
            )}
          </div>
        )}

        <div>
          <Text strong>제명</Text>
          <Input
            placeholder="예: 청년 창업 지원 조례"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ marginTop: 8 }}
          />
        </div>
        <div>
          <Text strong>지자체</Text>
          <Input
            placeholder="예: 서울특별시 강남구"
            value={municipality}
            onChange={(e) => setMunicipality(e.target.value)}
            style={{ marginTop: 8 }}
          />
        </div>
      </Space>
    </Modal>
  )
}
