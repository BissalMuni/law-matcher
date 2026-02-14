import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Tabs,
  Descriptions,
  List,
  Button,
  Tag,
  Timeline,
  Modal,
  Form,
  Select,
  Input,
  message,
  Popconfirm,
  Spin,
} from 'antd'
import {
  ArrowLeftOutlined,
  LinkOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { articleApi, ordinanceApi } from '../services/api'

const { TabPane } = Tabs
const { TextArea } = Input

interface ArticleDetail {
  id: number
  law_id: number
  law_name: string
  law_type: string
  article_no: string
  article_title: string
  article_content: string
  paragraphs?: any
  ordinance_count: number
  change_count: number
  last_changed_date?: string
  has_recent_change: boolean
  last_synced_at?: string
}

interface OrdinanceMapping {
  id: number
  ordinance_id: number
  ordinance_name: string
  ordinance_category: string
  department: string
  mapping_reason?: string
  related_article_nos?: string
  created_at: string
}

interface ArticleChange {
  id: number
  change_date: string
  change_type: string
  old_content?: string
  new_content?: string
  diff_html?: string
  detected_at: string
  notified: boolean
}

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState('content')
  const [mappingModalOpen, setMappingModalOpen] = useState(false)
  const [diffModalOpen, setDiffModalOpen] = useState(false)
  const [selectedChange, setSelectedChange] = useState<ArticleChange | null>(null)
  const [form] = Form.useForm()

  // 조문 상세 조회
  const { data: article, isLoading } = useQuery<ArticleDetail>({
    queryKey: ['article', id],
    queryFn: () => articleApi.getById(parseInt(id!)),
    enabled: !!id,
  })

  // 연계 조례 목록 조회
  const { data: mappingsData } = useQuery<{ items: OrdinanceMapping[]; total: number }>({
    queryKey: ['article-ordinances', id],
    queryFn: () => articleApi.getOrdinances(parseInt(id!)),
    enabled: !!id,
  })

  // 변경 이력 조회
  const { data: historyData } = useQuery<{ items: ArticleChange[]; total: number }>({
    queryKey: ['article-history', id],
    queryFn: () => articleApi.getHistory(parseInt(id!)),
    enabled: !!id,
  })

  // 조례 목록 조회 (연계 추가용)
  const { data: ordinancesData } = useQuery({
    queryKey: ['ordinances-list'],
    queryFn: () => ordinanceApi.getList({ page: 1, size: 1000 }),
  })

  // 연계 추가 Mutation
  const createMappingMutation = useMutation({
    mutationFn: (data: any) => articleApi.createMapping(parseInt(id!), data),
    onSuccess: () => {
      message.success('연계가 추가되었습니다.')
      setMappingModalOpen(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['article-ordinances', id] })
      queryClient.invalidateQueries({ queryKey: ['article', id] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail?.message || '연계 추가 중 오류가 발생했습니다.')
    },
  })

  // 연계 삭제 Mutation
  const deleteMappingMutation = useMutation({
    mutationFn: (mappingId: number) => articleApi.deleteMapping(parseInt(id!), mappingId),
    onSuccess: () => {
      message.success('연계가 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['article-ordinances', id] })
      queryClient.invalidateQueries({ queryKey: ['article', id] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail?.message || '연계 삭제 중 오류가 발생했습니다.')
    },
  })

  // 연계 추가 핸들러
  const handleAddMapping = () => {
    form.validateFields().then((values) => {
      createMappingMutation.mutate(values)
    })
  }

  // 연계 삭제 핸들러
  const handleDeleteMapping = (mappingId: number) => {
    deleteMappingMutation.mutate(mappingId)
  }

  // Diff 모달 열기
  const showDiffModal = (change: ArticleChange) => {
    setSelectedChange(change)
    setDiffModalOpen(true)
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!article) {
    return <div>조문을 찾을 수 없습니다.</div>
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/articles')}
          style={{ marginBottom: 16 }}
        >
          목록으로
        </Button>

        <Card>
          <Descriptions title={`${article.law_name} ${article.article_no}`} column={2}>
            <Descriptions.Item label="조문제목">{article.article_title || '-'}</Descriptions.Item>
            <Descriptions.Item label="법령유형">
              <Tag color="blue">{article.law_type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="연계 조례">
              <Tag color="green">{article.ordinance_count}건</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="변경 이력">
              {article.change_count}건
              {article.has_recent_change && (
                <Tag color="red" style={{ marginLeft: 8 }}>
                  최근 변경
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="최근 변경일">
              {article.last_changed_date || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="동기화 일시">
              {article.last_synced_at || '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </div>

      {/* Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 조문 내용 탭 */}
          <TabPane tab="조문 내용" key="content">
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {article.article_content}
            </div>

            {/* 항/호/목 표시 (paragraphs가 있는 경우) */}
            {article.paragraphs?.paragraphs && article.paragraphs.paragraphs.length > 0 && (
              <div style={{ marginTop: 24 }}>
                {article.paragraphs.paragraphs.map((para: any, index: number) => (
                  <div key={index} style={{ marginBottom: 16 }}>
                    <div style={{ fontWeight: 'bold' }}>
                      {para.no && `${para.no}. `}
                      {para.content}
                    </div>
                    {para.items && para.items.length > 0 && (
                      <div style={{ paddingLeft: 24 }}>
                        {para.items.map((item: any, itemIndex: number) => (
                          <div key={itemIndex} style={{ marginTop: 8 }}>
                            {item.no && `${item.no}. `}
                            {item.content}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabPane>

          {/* 연계 조례 탭 */}
          <TabPane
            tab={`연계 조례 (${mappingsData?.total || 0})`}
            key="ordinances"
            tabBarExtraContent={
              <Button type="primary" icon={<LinkOutlined />} onClick={() => setMappingModalOpen(true)}>
                연계 추가
              </Button>
            }
          >
            <List
              dataSource={mappingsData?.items || []}
              renderItem={(mapping) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      onClick={() => navigate(`/ordinances/${mapping.ordinance_id}`)}
                    >
                      상세보기
                    </Button>,
                    <Popconfirm
                      title="연계를 삭제하시겠습니까?"
                      onConfirm={() => handleDeleteMapping(mapping.id)}
                      okText="삭제"
                      cancelText="취소"
                    >
                      <Button type="link" danger>
                        삭제
                      </Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={mapping.ordinance_name}
                    description={
                      <>
                        <Tag>{mapping.ordinance_category}</Tag>
                        <Tag color="blue">{mapping.department}</Tag>
                        {mapping.mapping_reason && (
                          <div style={{ marginTop: 8 }}>사유: {mapping.mapping_reason}</div>
                        )}
                        {mapping.related_article_nos && (
                          <div>관련 조례 조문: {mapping.related_article_nos}</div>
                        )}
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </TabPane>

          {/* 변경 이력 탭 */}
          <TabPane
            tab={`변경 이력 (${historyData?.total || 0})`}
            key="history"
            icon={<HistoryOutlined />}
          >
            <Timeline>
              {historyData?.items.map((change) => (
                <Timeline.Item
                  key={change.id}
                  color={change.change_type === 'created' ? 'green' : change.change_type === 'updated' ? 'blue' : 'red'}
                >
                  <p>
                    <strong>{change.change_date}</strong> -{' '}
                    {change.change_type === 'created'
                      ? '신규 생성'
                      : change.change_type === 'updated'
                      ? '내용 변경'
                      : '삭제'}
                  </p>
                  {(change.change_type === 'updated' || change.change_type === 'deleted') && (
                    <Button type="link" onClick={() => showDiffModal(change)}>
                      변경 내용 보기
                    </Button>
                  )}
                  <div style={{ fontSize: 12, color: '#888' }}>
                    감지: {change.detected_at}
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          </TabPane>
        </Tabs>
      </Card>

      {/* 연계 추가 모달 */}
      <Modal
        title="조문-조례 연계 추가"
        open={mappingModalOpen}
        onCancel={() => setMappingModalOpen(false)}
        onOk={handleAddMapping}
        confirmLoading={createMappingMutation.isPending}
        okText="추가"
        cancelText="취소"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="조례"
            name="ordinance_id"
            rules={[{ required: true, message: '조례를 선택해주세요' }]}
          >
            <Select
              showSearch
              placeholder="조례 검색"
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={ordinancesData?.items?.map((ord: any) => ({
                value: ord.id,
                label: `${ord.name} (${ord.ordinance_category})`,
              }))}
            />
          </Form.Item>

          <Form.Item label="연계 사유" name="mapping_reason">
            <TextArea rows={3} placeholder="연계 사유를 입력하세요" />
          </Form.Item>

          <Form.Item label="관련 조례 조문" name="related_article_nos">
            <Input placeholder="예: 제3조, 제4조" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Diff 모달 */}
      <Modal
        title={`조문 변경 내용 (${selectedChange?.change_date})`}
        open={diffModalOpen}
        onCancel={() => setDiffModalOpen(false)}
        width={1000}
        footer={[
          <Button key="close" onClick={() => setDiffModalOpen(false)}>
            닫기
          </Button>,
        ]}
      >
        {selectedChange?.diff_html ? (
          <div dangerouslySetInnerHTML={{ __html: selectedChange.diff_html }} />
        ) : (
          <div>
            <div style={{ marginBottom: 16 }}>
              <strong>이전 내용:</strong>
              <div style={{ whiteSpace: 'pre-wrap', padding: 12, background: '#f5f5f5' }}>
                {selectedChange?.old_content || '-'}
              </div>
            </div>
            <div>
              <strong>새 내용:</strong>
              <div style={{ whiteSpace: 'pre-wrap', padding: 12, background: '#f5f5f5' }}>
                {selectedChange?.new_content || '-'}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
