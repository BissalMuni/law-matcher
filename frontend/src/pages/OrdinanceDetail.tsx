import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Descriptions,
  Table,
  Card,
  Tabs,
  Button,
  Space,
  Typography,
  Spin,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  List,
  Tag,
  Timeline,
  Alert,
} from 'antd'
import { ArrowLeftOutlined, PlusOutlined, EditOutlined, DeleteOutlined, CheckOutlined, CloseOutlined, LinkOutlined, UserOutlined, BankOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi, lawsApi, useDetectionResults, useRevisionReason } from '../services/api'
import dayjs from 'dayjs'
import { useAuth } from '../contexts/AuthContext'
import TabA_LawCompare from '../components/detection/TabA_LawCompare'
import TabB_ArticleCompare from '../components/detection/TabB_ArticleCompare'
import TabC_ReasonCompare from '../components/detection/TabC_ReasonCompare'

const { Title } = Typography

interface ParentLaw {
  id: number
  law_internal_id: number  // Law 테이블 PK (연계 조례 조회용)
  law_id: string
  law_type: string
  law_name: string
  proclaimed_date?: string
  enforced_date?: string
  revision_type?: string
  related_articles?: string
}

interface UserBrief {
  id: number
  username: string
  full_name: string | null
  user_type: string
}

interface OrdinanceReview {
  id: number
  ordinance_id: number
  reviewer_type: string  // "DEPARTMENT" | "GENERAL"
  reviewer_name?: string
  reviewer_department?: string
  review_content: string
  review_result?: string
  created_by?: UserBrief | null
  updated_by?: UserBrief | null
  approval_status?: string  // "pending" | "approved" | "rejected"
  approved_by?: UserBrief | null
  approved_at?: string
  approval_note?: string
  created_at: string
  updated_at: string
}

export default function OrdinanceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingParentLaw, setEditingParentLaw] = useState<ParentLaw | null>(null)
  const [form] = Form.useForm()
  const [activeDetectionTab, setActiveDetectionTab] = useState('law_compare')
  const [loadedDetectionTabs, setLoadedDetectionTabs] = useState<Record<string, boolean>>({
    law_compare: true,
  })
  const [detectionAlertDismissed, setDetectionAlertDismissed] = useState(false)

  // 검토이력 상태
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
  const [editingReview, setEditingReview] = useState<OrdinanceReview | null>(null)
  const [reviewForm] = Form.useForm()

  const { data: ordinance, isLoading } = useQuery({
    queryKey: ['ordinance', id],
    queryFn: () => ordinanceApi.getById(Number(id)),
    enabled: !!id,
  })

  const { data: parentLaws } = useQuery({
    queryKey: ['ordinance', id, 'parent-laws'],
    queryFn: () => ordinanceApi.getParentLaws(Number(id)),
    enabled: !!id,
  })

  const { data: detectionResults } = useDetectionResults(Number(id), !!id)
  const firstParentLawId = parentLaws?.[0]?.law_internal_id
  const {
    isError: isRevisionReasonApiError,
  } = useRevisionReason(firstParentLawId, !!firstParentLawId && !!loadedDetectionTabs.reason_compare)

  // 검토이력 조회
  const { data: reviews } = useQuery({
    queryKey: ['ordinance', id, 'reviews'],
    queryFn: () => ordinanceApi.getReviews(Number(id)),
    enabled: !!id,
  })

  // 연계 조례 모달
  const [lawOrdinanceModalOpen, setLawOrdinanceModalOpen] = useState(false)
  const [selectedLaw, setSelectedLaw] = useState<ParentLaw | null>(null)

  // 연계 조례 조회
  const { data: linkedOrdinances, isLoading: linkedOrdinancesLoading } = useQuery({
    queryKey: ['law-ordinances', selectedLaw?.law_internal_id],
    queryFn: () => selectedLaw?.law_internal_id ? lawsApi.getOrdinances(selectedLaw.law_internal_id) : null,
    enabled: !!selectedLaw?.law_internal_id && lawOrdinanceModalOpen,
  })

  // 법령 삭제
  const deleteLawMutation = useMutation({
    mutationFn: (lawId: number) => lawsApi.delete(lawId),
    onSuccess: () => {
      message.success('법령이 삭제되었습니다.')
      setLawOrdinanceModalOpen(false)
      setSelectedLaw(null)
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'parent-laws'] })
    },
    onError: () => {
      message.error('법령 삭제에 실패했습니다.')
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: {
      law_id?: string
      law_type: string
      law_name: string
      proclaimed_date?: string
      enforced_date?: string
      related_articles?: string
    }) => ordinanceApi.createParentLaw(Number(id), data),
    onSuccess: () => {
      message.success('상위법령이 추가되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'parent-laws'] })
      handleModalClose()
    },
    onError: () => {
      message.error('상위법령 추가에 실패했습니다.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ parentLawId, data }: { parentLawId: number; data: any }) =>
      ordinanceApi.updateParentLaw(parentLawId, data),
    onSuccess: () => {
      message.success('상위법령이 수정되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'parent-laws'] })
      handleModalClose()
    },
    onError: () => {
      message.error('상위법령 수정에 실패했습니다.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (parentLawId: number) => ordinanceApi.deleteParentLaw(parentLawId),
    onSuccess: () => {
      message.success('상위법령이 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'parent-laws'] })
    },
    onError: () => {
      message.error('상위법령 삭제에 실패했습니다.')
    },
  })

  const setNoParentLawMutation = useMutation({
    mutationFn: () => ordinanceApi.setNoParentLaw(Number(id)),
    onSuccess: () => {
      message.success('상위법령 없음으로 설정되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id] })
    },
    onError: () => {
      message.error('설정에 실패했습니다.')
    },
  })

  const unsetNoParentLawMutation = useMutation({
    mutationFn: () => ordinanceApi.unsetNoParentLaw(Number(id)),
    onSuccess: () => {
      message.success('상위법령 없음 설정이 해제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id] })
    },
    onError: () => {
      message.error('설정 해제에 실패했습니다.')
    },
  })

  // 검토이력 mutation
  const createReviewMutation = useMutation({
    mutationFn: (data: {
      reviewer_type: string
      reviewer_name?: string
      reviewer_department?: string
      review_content: string
      review_result?: string
    }) => ordinanceApi.createReview(Number(id), data),
    onSuccess: () => {
      message.success('검토의견이 등록되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'reviews'] })
      handleReviewModalClose()
    },
    onError: () => {
      message.error('검토의견 등록에 실패했습니다.')
    },
  })

  const updateReviewMutation = useMutation({
    mutationFn: ({ reviewId, data }: { reviewId: number; data: any }) =>
      ordinanceApi.updateReview(reviewId, data),
    onSuccess: () => {
      message.success('검토의견이 수정되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'reviews'] })
      handleReviewModalClose()
    },
    onError: () => {
      message.error('검토의견 수정에 실패했습니다.')
    },
  })

  const deleteReviewMutation = useMutation({
    mutationFn: (reviewId: number) => ordinanceApi.deleteReview(reviewId),
    onSuccess: () => {
      message.success('검토의견이 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'reviews'] })
    },
    onError: () => {
      message.error('검토의견 삭제에 실패했습니다.')
    },
  })

  // 검토의견 승인/반려 mutation
  const approveReviewMutation = useMutation({
    mutationFn: ({ reviewId, approval_status, approval_note }: {
      reviewId: number
      approval_status: string
      approval_note?: string
    }) => ordinanceApi.approveReview(reviewId, { approval_status, approval_note }),
    onSuccess: (_, variables) => {
      message.success(variables.approval_status === 'approved' ? '승인되었습니다.' : '반려되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['ordinance', id, 'reviews'] })
    },
    onError: () => {
      message.error('처리에 실패했습니다.')
    },
  })

  const handleModalClose = () => {
    setIsModalOpen(false)
    setEditingParentLaw(null)
    form.resetFields()
  }

  const handleReviewModalClose = () => {
    setIsReviewModalOpen(false)
    setEditingReview(null)
    reviewForm.resetFields()
  }

  const handleAdd = () => {
    setEditingParentLaw(null)
    form.resetFields()
    setIsModalOpen(true)
  }

  const handleEdit = (record: ParentLaw) => {
    setEditingParentLaw(record)
    form.setFieldsValue({
      ...record,
      proclaimed_date: record.proclaimed_date ? dayjs(record.proclaimed_date) : undefined,
      enforced_date: record.enforced_date ? dayjs(record.enforced_date) : undefined,
    })
    setIsModalOpen(true)
  }

  // 상위법령 법령명 클릭 시 연계 조례 모달 열기
  const handleLawNameClick = (record: ParentLaw) => {
    setSelectedLaw(record)
    setLawOrdinanceModalOpen(true)
  }

  const handleSubmit = (values: any) => {
    const data = {
      law_name: values.law_name,
      law_type: values.law_type,
      proclaimed_date: values.proclaimed_date?.format('YYYY-MM-DD'),
      enforced_date: values.enforced_date?.format('YYYY-MM-DD'),
      related_articles: values.related_articles,
    }
    if (editingParentLaw) {
      updateMutation.mutate({ parentLawId: editingParentLaw.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  // 검토이력 핸들러
  const handleAddReview = () => {
    setEditingReview(null)
    reviewForm.resetFields()

    // 로그인한 사용자 정보로 자동 입력
    // ADMIN -> GENERAL (구청 총괄), USER -> DEPARTMENT (부서 담당자)
    if (user) {
      reviewForm.setFieldsValue({
        reviewer_type: user.user_type === 'ADMIN' ? 'GENERAL' : 'DEPARTMENT',
        reviewer_name: user.full_name || user.username,
        reviewer_department: user.department_name || undefined,
      })
    }

    setIsReviewModalOpen(true)
  }

  const handleEditReview = (record: OrdinanceReview) => {
    setEditingReview(record)
    reviewForm.setFieldsValue(record)
    setIsReviewModalOpen(true)
  }

  const handleReviewSubmit = (values: any) => {
    if (editingReview) {
      updateReviewMutation.mutate({ reviewId: editingReview.id, data: values })
    } else {
      createReviewMutation.mutate(values)
    }
  }

  const handleDetectionTabChange = (key: string) => {
    setActiveDetectionTab(key)
    setLoadedDetectionTabs((prev) => (prev[key] ? prev : { ...prev, [key]: true }))
  }

  useEffect(() => {
    if (isRevisionReasonApiError && activeDetectionTab === 'reason_compare') {
      setActiveDetectionTab('law_compare')
    }
  }, [activeDetectionTab, isRevisionReasonApiError])

  const reviewResultColor: Record<string, string> = {
    '개정필요': 'red',
    '개정불필요': 'green',
    '검토중': 'orange',
    '보류': 'default',
  }

  const parentLawColumns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      render: (text: string, record: ParentLaw) => (
        <Space>
          <a
            href={`https://www.law.go.kr/법령/${encodeURIComponent(record.law_name)}`}
            target="_blank"
            rel="noopener noreferrer"
            title="법제처에서 보기"
          >
            {text}
          </a>
          <a
            onClick={() => handleLawNameClick(record)}
            title="연계 자치법규 보기"
          >
            <LinkOutlined style={{ color: '#1890ff' }} />
          </a>
        </Space>
      ),
    },
    {
      title: '법령ID',
      dataIndex: 'law_id',
      key: 'law_id',
      width: 100,
    },
    {
      title: '법령유형',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 90,
    },
    {
      title: '공포일자',
      dataIndex: 'proclaimed_date',
      key: 'proclaimed_date',
      width: 110,
    },
    {
      title: '시행일자',
      dataIndex: 'enforced_date',
      key: 'enforced_date',
      width: 110,
    },
    {
      title: '개정구분',
      dataIndex: 'revision_type',
      key: 'revision_type',
      width: 100,
    },
    { title: '관련조문', dataIndex: 'related_articles', key: 'related_articles', width: 120 },
    {
      title: '작업',
      key: 'action',
      width: 80,
      render: (_: any, record: ParentLaw) => (
        <Space size="small">
          <Button type="text" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm
            title="삭제 확인"
            description="이 상위법령 매핑을 삭제하시겠습니까?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  if (isLoading) {
    return <Spin size="large" />
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          목록
        </Button>
      </Space>

      <Title level={4}>{ordinance?.name}</Title>

      {!detectionAlertDismissed && !!detectionResults?.results?.some((result) => result.needs_revision) && (
        <Alert
          type="warning"
          showIcon
          closable
          onClose={() => setDetectionAlertDismissed(true)}
          style={{ marginBottom: 16 }}
          message="새로운 변경이 감지되었습니다."
          description="판별 결과에서 개정 검토 필요 항목이 확인되었습니다."
        />
      )}

      <Card title="기본 정보" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="자치법규 코드">{ordinance?.code}</Descriptions.Item>
          <Descriptions.Item label="분류">{ordinance?.category}</Descriptions.Item>
          <Descriptions.Item label="소관부서">{ordinance?.department}</Descriptions.Item>
          <Descriptions.Item label="상태">{ordinance?.status}</Descriptions.Item>
          <Descriptions.Item label="제정일">{ordinance?.enacted_date}</Descriptions.Item>
          <Descriptions.Item label="시행일">{ordinance?.enforced_date}</Descriptions.Item>
          <Descriptions.Item label="상위법령 없음">
            {ordinance?.no_parent_law ? '확인됨' : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="상위법령"
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            {ordinance?.no_parent_law ? (
              <Popconfirm
                title="상위법령 없음 해제"
                description="상위법령 없음 설정을 해제하시겠습니까?"
                onConfirm={() => unsetNoParentLawMutation.mutate()}
                okText="해제"
                cancelText="취소"
              >
                <Button icon={<CloseOutlined />} loading={unsetNoParentLawMutation.isPending}>
                  없음 해제
                </Button>
              </Popconfirm>
            ) : (
              <Popconfirm
                title="상위법령 없음 확인"
                description="이 조례에 상위법령이 없음을 확인하시겠습니까?"
                onConfirm={() => setNoParentLawMutation.mutate()}
                okText="확인"
                cancelText="취소"
              >
                <Button icon={<CheckOutlined />} loading={setNoParentLawMutation.isPending}>
                  없음
                </Button>
              </Popconfirm>
            )}
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              추가
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={parentLaws || []}
          rowKey="id"
          size="small"
          pagination={false}
          columns={parentLawColumns}
          locale={{ emptyText: ordinance?.no_parent_law ? '상위법령 없음 (확인됨)' : '상위법령 없음' }}
        />
      </Card>

      <Card title="개정검토" style={{ marginBottom: 16 }}>
        <Tabs activeKey={activeDetectionTab} onChange={handleDetectionTabChange}>
          <Tabs.TabPane tab="법령비교" key="law_compare">
            <TabA_LawCompare
              ordinanceId={Number(id)}
              parentLaws={parentLaws || []}
              enabled={loadedDetectionTabs.law_compare}
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="조문비교" key="article_compare">
            {loadedDetectionTabs.article_compare ? (
              <TabB_ArticleCompare ordinanceId={Number(id)} enabled={loadedDetectionTabs.article_compare} />
            ) : null}
          </Tabs.TabPane>
          <Tabs.TabPane tab="개정이유비교" key="reason_compare" disabled={isRevisionReasonApiError}>
            {loadedDetectionTabs.reason_compare && !isRevisionReasonApiError ? (
              <TabC_ReasonCompare
                ordinanceId={Number(id)}
                parentLaws={parentLaws || []}
                enabled={loadedDetectionTabs.reason_compare}
              />
            ) : isRevisionReasonApiError ? (
              <Alert
                type="error"
                showIcon
                message="개정이유비교 탭을 사용할 수 없습니다."
                description="탭C API 장애로 인해 해당 탭이 비활성화되었습니다. 탭A/B는 계속 사용할 수 있습니다."
              />
            ) : null}
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 검토이력 카드 */}
      <Card
        title="검토결과"
        style={{ marginBottom: 16 }}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddReview}>
            검토의견 추가
          </Button>
        }
      >
        {reviews?.items?.length > 0 ? (
          <Timeline
            items={reviews.items.map((review: OrdinanceReview) => ({
              color: review.reviewer_type === 'GENERAL' ? 'blue' : 'green',
              children: (
                <div key={review.id}>
                  <div style={{ marginBottom: 8 }}>
                    <Space wrap>
                      <Tag color={review.reviewer_type === 'GENERAL' ? 'blue' : 'green'}>
                        {review.reviewer_type === 'GENERAL' ? '구청 총괄' : '부서 담당자'}
                      </Tag>
                      {review.review_result && (
                        <Tag color={reviewResultColor[review.review_result] || 'default'}>
                          {review.review_result}
                        </Tag>
                      )}
                      {review.approval_status === 'approved' && (
                        <Tag color="success" icon={<CheckCircleOutlined />}>승인됨</Tag>
                      )}
                      {review.approval_status === 'rejected' && (
                        <Tag color="error" icon={<CloseCircleOutlined />}>반려됨</Tag>
                      )}
                      {(!review.approval_status || review.approval_status === 'pending') && (
                        <Tag color="warning">승인대기</Tag>
                      )}
                      <span style={{ color: '#666', fontSize: 13 }}>
                        <UserOutlined style={{ marginRight: 4 }} />
                        {review.created_by
                          ? (review.created_by.full_name || review.created_by.username)
                          : (review.reviewer_name || '작성자 정보 없음')
                        }
                      </span>
                      {review.reviewer_department && (
                        <span style={{ color: '#999', fontSize: 12 }}>
                          <BankOutlined style={{ marginRight: 4 }} />
                          {review.reviewer_department}
                        </span>
                      )}
                    </Space>
                  </div>
                  <div style={{ marginBottom: 8 }}>{review.review_content}</div>
                  {review.approval_note && (
                    <div style={{ marginBottom: 8, padding: 8, background: '#f5f5f5', borderRadius: 4, fontSize: 12 }}>
                      <strong>{review.approval_status === 'approved' ? '승인' : '반려'} 사유:</strong> {review.approval_note}
                      {review.approved_by && (
                        <span style={{ marginLeft: 8, color: '#999' }}>
                          ({review.approved_by.full_name || review.approved_by.username}, {review.approved_at && new Date(review.approved_at).toLocaleString()})
                        </span>
                      )}
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                    <span style={{ color: '#999', fontSize: 12 }}>
                      작성: {new Date(review.created_at).toLocaleString()}
                      {review.updated_at !== review.created_at && review.updated_by && (
                        <span style={{ marginLeft: 8 }}>
                          | 수정: {new Date(review.updated_at).toLocaleString()}
                          ({review.updated_by.full_name || review.updated_by.username})
                        </span>
                      )}
                    </span>
                    <Space size="small">
                      {user?.user_type === 'ADMIN' && (!review.approval_status || review.approval_status === 'pending') && (
                        <>
                          <Popconfirm
                            title="검토의견 승인"
                            description="이 검토의견을 승인하시겠습니까?"
                            onConfirm={() => approveReviewMutation.mutate({
                              reviewId: review.id,
                              approval_status: 'approved',
                            })}
                            okText="승인"
                            cancelText="취소"
                          >
                            <Button type="primary" size="small" icon={<CheckCircleOutlined />}>
                              승인
                            </Button>
                          </Popconfirm>
                          <Popconfirm
                            title="검토의견 반려"
                            description="이 검토의견을 반려하시겠습니까?"
                            onConfirm={() => approveReviewMutation.mutate({
                              reviewId: review.id,
                              approval_status: 'rejected',
                            })}
                            okText="반려"
                            cancelText="취소"
                            okButtonProps={{ danger: true }}
                          >
                            <Button danger size="small" icon={<CloseCircleOutlined />}>
                              반려
                            </Button>
                          </Popconfirm>
                        </>
                      )}
                      {/* 본인 작성 의견만 수정/삭제 가능 */}
                      {user && review.created_by?.id === user.id && (
                        <>
                          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEditReview(review)} />
                          <Popconfirm
                            title="삭제 확인"
                            description="이 검토의견을 삭제하시겠습니까?"
                            onConfirm={() => deleteReviewMutation.mutate(review.id)}
                            okText="삭제"
                            cancelText="취소"
                          >
                            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </>
                      )}
                    </Space>
                  </div>
                </div>
              ),
            }))}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
            등록된 검토의견이 없습니다.
          </div>
        )}
      </Card>

      {/* 검토이력 모달 */}
      <Modal
        title={editingReview ? '검토의견 수정' : '검토의견 추가'}
        open={isReviewModalOpen}
        onCancel={handleReviewModalClose}
        onOk={() => reviewForm.submit()}
        confirmLoading={createReviewMutation.isPending || updateReviewMutation.isPending}
      >
        <Form form={reviewForm} layout="vertical" onFinish={handleReviewSubmit}>
          <Form.Item
            name="reviewer_type"
            label="검토자 유형"
            rules={[{ required: true, message: '검토자 유형을 선택하세요' }]}
          >
            <Select
              placeholder="유형 선택"
              disabled={!editingReview}
              options={[
                { value: 'DEPARTMENT', label: '부서 담당자' },
                { value: 'GENERAL', label: '구청 총괄' },
              ]}
            />
          </Form.Item>
          <Form.Item name="reviewer_name" label="검토자명">
            <Input placeholder="예: 홍길동" disabled={!editingReview} />
          </Form.Item>
          <Form.Item name="reviewer_department" label="소속부서">
            <Input placeholder="예: 법무담당관" disabled />
          </Form.Item>
          <Form.Item
            name="review_content"
            label="검토의견"
            rules={[{ required: true, message: '검토의견을 입력하세요' }]}
          >
            <Input.TextArea rows={4} placeholder="검토의견을 입력하세요" />
          </Form.Item>
          <Form.Item name="review_result" label="검토결과">
            <Select
              placeholder="결과 선택"
              allowClear
              options={[
                { value: '개정필요', label: '개정필요' },
                { value: '개정불필요', label: '개정불필요' },
                { value: '검토중', label: '검토중' },
                { value: '보류', label: '보류' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingParentLaw ? '상위법령 수정' : '상위법령 추가'}
        open={isModalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="law_name"
            label="법령명"
            rules={[{ required: true, message: '법령명을 입력하세요' }]}
          >
            <Input placeholder="예: 지방자치법" />
          </Form.Item>
          <Form.Item
            name="law_type"
            label="법령 유형"
            rules={[{ required: true, message: '법령 유형을 선택하세요' }]}
          >
            <Select
              placeholder="유형 선택"
              options={[
                { value: '법률', label: '법률' },
                { value: '시행령', label: '시행령' },
                { value: '시행규칙', label: '시행규칙' },
              ]}
            />
          </Form.Item>
          <Form.Item name="related_articles" label="관련 조문">
            <Input placeholder="예: 제1조, 제2조" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 연계 조례 모달 */}
      <Modal
        title={`연계 자치법규 - ${selectedLaw?.law_name}`}
        open={lawOrdinanceModalOpen}
        onCancel={() => {
          setLawOrdinanceModalOpen(false)
          setSelectedLaw(null)
        }}
        footer={
          <Popconfirm
            title="법령 삭제"
            description="이 법령과 관련된 모든 데이터가 삭제됩니다. 계속하시겠습니까?"
            onConfirm={() => {
              if (selectedLaw?.law_internal_id) {
                deleteLawMutation.mutate(selectedLaw.law_internal_id)
              }
            }}
            okText="삭제"
            cancelText="취소"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleteLawMutation.isPending}>
              법령 삭제
            </Button>
          </Popconfirm>
        }
        width={700}
      >
        {linkedOrdinancesLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : linkedOrdinances?.length > 0 ? (
          <List
            dataSource={linkedOrdinances}
            renderItem={(item: any) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <a href={`/ordinances/${item.id}`} target="_blank" rel="noopener noreferrer">
                      {item.name}
                    </a>
                  }
                  description={
                    <Space>
                      <span>{item.category}</span>
                      {item.related_articles && <span>| 관련조문: {item.related_articles}</span>}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 24, color: '#999' }}>
            연계된 자치법규가 없습니다.
          </div>
        )}
      </Modal>
    </div>
  )
}
