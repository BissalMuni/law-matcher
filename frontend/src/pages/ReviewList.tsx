import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table,
  Tag,
  Typography,
  Space,
  Select,
  Button,
  Modal,
  Form,
  Input,
  message,
  Tooltip,
  Card,
  Tree,
} from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, ApartmentOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi, departmentApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import dayjs from 'dayjs'
import type { TreeDataNode } from 'antd'

const { Title } = Typography
const { TextArea } = Input

interface ReviewItem {
  id: number
  ordinance_id: number
  ordinance_name?: string
  ordinance_department?: string
  reviewer_type: string
  reviewer_name?: string
  reviewer_department?: string
  review_content: string
  review_result?: string
  approval_status?: string
  approved_by?: { username: string; full_name: string | null } | null
  approved_at?: string
  approval_note?: string
  created_by?: { username: string; full_name: string | null } | null
  created_at: string
}

interface DepartmentTreeNode {
  id: number
  code: string
  name: string
  parent_name: string | null
  sort_order: number
  ordinance_count: number
  children: DepartmentTreeNode[]
}

interface DepartmentTreeResponse {
  bureaus: DepartmentTreeNode[]
  zones: DepartmentTreeNode[]
}

const REVIEW_RESULT_COLOR: Record<string, string> = {
  '개정필요': 'red',
  '개정불필요': 'green',
}

const APPROVAL_COLOR: Record<string, string> = {
  pending: 'orange',
  approved: 'green',
  rejected: 'red',
}

const APPROVAL_LABEL: Record<string, string> = {
  pending: '승인대기',
  approved: '승인됨',
  rejected: '반려됨',
}

export default function ReviewList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.user_type === 'ADMIN'

  const [page, setPage] = useState(1)
  const [viewMode, setViewMode] = useState<'reviews' | 'all_revision'>('reviews')
  const [approvalStatus, setApprovalStatus] = useState<string | undefined>('pending')
  const [reviewResult, setReviewResult] = useState<string | undefined>()
  const [reviewerType, setReviewerType] = useState<string | undefined>()
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>()

  // 사이드바 리사이즈
  const [sidebarWidth, setSidebarWidth] = useState(220)
  const isResizing = useRef(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([])
  const [treeInitialized, setTreeInitialized] = useState(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isResizing.current = true
    e.preventDefault()
    const startX = e.clientX
    const startWidth = sidebarWidth

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return
      const newWidth = Math.max(150, Math.min(400, startWidth + e.clientX - startX))
      setSidebarWidth(newWidth)
    }

    const handleMouseUp = () => {
      isResizing.current = false
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [sidebarWidth])

  // 부서 트리 조회
  const { data: departmentTree } = useQuery<DepartmentTreeResponse>({
    queryKey: ['department-tree'],
    queryFn: () => departmentApi.getTree(),
  })

  const treeData: TreeDataNode[] = useMemo(() => {
    if (!departmentTree?.bureaus) return []

    const buildChildren = (nodes: DepartmentTreeNode[]): TreeDataNode[] => {
      return nodes.map(node => ({
        title: `${node.name} (${node.ordinance_count})`,
        key: String(node.id),
        children: node.children.length > 0 ? buildChildren(node.children) : undefined,
      }))
    }

    const rootChildren = buildChildren(departmentTree.bureaus)
    const totalCount = departmentTree.bureaus.reduce((sum, b) => sum + b.ordinance_count, 0)

    return [
      {
        title: `전체 (${totalCount})`,
        key: '__all__',
        icon: <ApartmentOutlined />,
        children: rootChildren,
      },
    ]
  }, [departmentTree])

  const onTreeSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string
    if (key === '__all__' || !key) {
      setSelectedDepartment(undefined)
    } else {
      setSelectedDepartment(key)
    }
    setPage(1)
  }

  const onTreeExpand = (keys: React.Key[]) => {
    setExpandedKeys(keys)
  }

  useEffect(() => {
    if (departmentTree?.bureaus && !treeInitialized) {
      const allKeys: React.Key[] = ['__all__']
      const collectKeys = (nodes: DepartmentTreeNode[]) => {
        for (const node of nodes) {
          allKeys.push(String(node.id))
          if (node.children.length > 0) {
            collectKeys(node.children)
          }
        }
      }
      collectKeys(departmentTree.bureaus)
      setExpandedKeys(allKeys)
      setTreeInitialized(true)
    }
  }, [departmentTree, treeInitialized])

  // 승인/반려 모달 상태
  const [approveModal, setApproveModal] = useState<{
    open: boolean
    reviewId: number | null
    action: 'approved' | 'rejected' | null
    reviewResult: string | null
  }>({ open: false, reviewId: null, action: null, reviewResult: null })
  const [approveForm] = Form.useForm()

  const { data, isLoading } = useQuery({
    queryKey: ['all-reviews', page, viewMode, approvalStatus, reviewResult, reviewerType, selectedDepartment],
    queryFn: () =>
      ordinanceApi.getAllReviews({
        page,
        size: 20,
        view_mode: viewMode,
        approval_status: viewMode === 'reviews' ? approvalStatus : undefined,
        review_result: viewMode === 'reviews' ? reviewResult : undefined,
        reviewer_type: viewMode === 'reviews' ? reviewerType : undefined,
        department_id: selectedDepartment ? Number(selectedDepartment) : undefined,
      }),
  })

  const approveMutation = useMutation({
    mutationFn: ({ reviewId, status, note }: { reviewId: number; status: string; note?: string }) =>
      ordinanceApi.approveReview(reviewId, { approval_status: status, approval_note: note }),
    onSuccess: () => {
      message.success(approveModal.action === 'approved' ? '승인되었습니다.' : '반려되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['all-reviews'] })
      setApproveModal({ open: false, reviewId: null, action: null, reviewResult: null })
      approveForm.resetFields()
    },
    onError: () => {
      message.error('처리 중 오류가 발생했습니다.')
    },
  })

  const handleApproveClick = (review: ReviewItem, action: 'approved' | 'rejected') => {
    setApproveModal({ open: true, reviewId: review.id, action, reviewResult: review.review_result || null })
  }

  const handleApproveSubmit = async () => {
    const values = await approveForm.validateFields()
    if (!approveModal.reviewId || !approveModal.action) return
    approveMutation.mutate({
      reviewId: approveModal.reviewId,
      status: approveModal.action,
      note: values.approval_note,
    })
  }

  // 검토의견 모드 컬럼
  const reviewColumns = [
    {
      title: '자치법규',
      dataIndex: 'ordinance_name',
      key: 'ordinance_name',
      ellipsis: true,
      render: (text: string, record: ReviewItem) => (
        <a onClick={() => navigate(`/ordinances/${record.ordinance_id}`)}>
          {text || `조례 #${record.ordinance_id}`}
        </a>
      ),
    },
    {
      title: '소관부서',
      dataIndex: 'ordinance_department',
      key: 'ordinance_department',
      width: 130,
      ellipsis: true,
    },
    {
      title: '검토자',
      key: 'reviewer',
      width: 140,
      render: (_: unknown, record: ReviewItem) => (
        <div>
          <div>{record.reviewer_name || record.created_by?.full_name || record.created_by?.username}</div>
          <div style={{ fontSize: 11, color: '#888' }}>
            {record.reviewer_department || record.reviewer_type}
          </div>
        </div>
      ),
    },
    {
      title: '검토의견',
      dataIndex: 'review_content',
      key: 'review_content',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '검토결과',
      dataIndex: 'review_result',
      key: 'review_result',
      width: 110,
      render: (result: string) =>
        result ? (
          <Tag color={REVIEW_RESULT_COLOR[result] || 'default'}>{result}</Tag>
        ) : (
          <span style={{ color: '#ccc' }}>-</span>
        ),
    },
    {
      title: '승인상태',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 100,
      render: (status: string) => (
        <Tag color={APPROVAL_COLOR[status] || 'default'}>
          {APPROVAL_LABEL[status] || status}
        </Tag>
      ),
    },
    {
      title: '작성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 110,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD'),
    },
    ...(isAdmin
      ? [
          {
            title: '처리',
            key: 'action',
            width: 110,
            render: (_: unknown, record: ReviewItem) =>
              record.approval_status === 'pending' ? (
                <Space size={4}>
                  <Button
                    size="small"
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleApproveClick(record, 'approved')}
                  >
                    승인
                  </Button>
                  <Button
                    size="small"
                    danger
                    icon={<CloseCircleOutlined />}
                    onClick={() => handleApproveClick(record, 'rejected')}
                  >
                    반려
                  </Button>
                </Space>
              ) : (
                <span style={{ fontSize: 12, color: '#888' }}>
                  {record.approved_by?.full_name || record.approved_by?.username || '-'}
                </span>
              ),
          },
        ]
      : []),
  ]

  const columns = reviewColumns

  return (
    <div>
      <Title level={4}>검토의견 관리</Title>

      <div style={{ display: 'flex', gap: 16 }}>
        {/* 소관부서 사이드 네비 */}
        {isAdmin && (
          <div style={{ width: sidebarWidth, flexShrink: 0, position: 'relative' }}>
            <Card
              size="small"
              title="담당부서"
              style={{ position: 'sticky', top: 16 }}
              styles={{ body: { maxHeight: 'calc(100vh - 200px)', overflow: 'auto', padding: 0 } }}
            >
              <Tree
                showIcon
                expandedKeys={expandedKeys}
                onExpand={onTreeExpand}
                treeData={treeData}
                onSelect={onTreeSelect}
                selectedKeys={selectedDepartment ? [selectedDepartment] : ['__all__']}
              />
            </Card>
            <div
              onMouseDown={handleMouseDown}
              style={{
                position: 'absolute',
                top: 0,
                right: -4,
                width: 8,
                height: '100%',
                cursor: 'col-resize',
                zIndex: 10,
              }}
            />
          </div>
        )}

        {/* 메인 콘텐츠 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Space style={{ marginBottom: 16 }} wrap>
            <Select
              style={{ width: 150 }}
              value={viewMode}
              onChange={(v) => { setViewMode(v); setPage(1) }}
              options={[
                { value: 'all_revision', label: '개정대상 전체' },
                { value: 'reviews', label: '검토의견 있음' },
              ]}
            />
            {viewMode === 'reviews' && (
              <>
                <Select
                  placeholder="승인상태"
                  style={{ width: 120 }}
                  allowClear
                  value={approvalStatus}
                  onChange={(v) => { setApprovalStatus(v); setPage(1) }}
                  options={[
                    { value: 'pending', label: '승인대기' },
                    { value: 'approved', label: '승인됨' },
                    { value: 'rejected', label: '반려됨' },
                  ]}
                />
                <Select
                  placeholder="검토결과"
                  style={{ width: 130 }}
                  allowClear
                  value={reviewResult}
                  onChange={(v) => { setReviewResult(v); setPage(1) }}
                  options={[
                    { value: '개정필요', label: '개정필요' },
                    { value: '개정불필요', label: '개정불필요' },
                  ]}
                />
                <Select
                  placeholder="검토자유형"
                  style={{ width: 130 }}
                  allowClear
                  value={reviewerType}
                  onChange={(v) => { setReviewerType(v); setPage(1) }}
                  options={[
                    { value: 'DEPARTMENT', label: '부서담당자' },
                    { value: 'GENERAL', label: '총괄담당자' },
                  ]}
                />
              </>
            )}
          </Space>

          <div style={{ marginBottom: 8, padding: '4px 8px', background: '#e6f4ff', borderRadius: 4, fontSize: 13 }}>
            <strong>필터 결과: {data?.total || 0}건</strong>
            {viewMode === 'all_revision' && ' (개정대상 전체, 승인된 "개정불필요" 제외)'}
            {viewMode === 'reviews' && approvalStatus && ` (${APPROVAL_LABEL[approvalStatus] || approvalStatus})`}
          </div>

          <Table
            columns={columns}
            dataSource={data?.items || []}
            rowKey="id"
            loading={isLoading}
            size="small"
            pagination={{
              current: page,
              total: data?.total || 0,
              pageSize: 20,
              onChange: setPage,
              showTotal: (total) => `총 ${total}건`,
            }}
          />
        </div>
      </div>

      {/* 승인/반려 모달 */}
      <Modal
        title={approveModal.action === 'approved' ? '검토의견 승인' : '검토의견 반려'}
        open={approveModal.open}
        onOk={handleApproveSubmit}
        onCancel={() => {
          setApproveModal({ open: false, reviewId: null, action: null, reviewResult: null })
          approveForm.resetFields()
        }}
        okText={approveModal.action === 'approved' ? '승인' : '반려'}
        okButtonProps={{
          danger: approveModal.action === 'rejected',
          loading: approveMutation.isPending,
        }}
      >
        {/* 승인/반려 결과 미리보기 */}
        <div style={{ marginBottom: 16, padding: 12, background: '#f6f8fa', borderRadius: 6, fontSize: 13 }}>
          {approveModal.action === 'approved' && approveModal.reviewResult === '개정필요' && (
            <span>승인 시 해당 조례는 <Tag color="error">개정확정</Tag> 상태로 전환됩니다.</span>
          )}
          {approveModal.action === 'approved' && approveModal.reviewResult === '개정불필요' && (
            <span>승인 시 해당 조례는 <Tag color="success">정상</Tag> 상태로 전환됩니다. (빨간불 해제)</span>
          )}
          {approveModal.action === 'rejected' && (
            <span>반려 시 해당 조례는 <Tag color="warning">검토대기</Tag> 상태로 되돌아갑니다.</span>
          )}
        </div>
        <Form form={approveForm} layout="vertical">
          <Form.Item
            name="approval_note"
            label={approveModal.action === 'approved' ? '승인 코멘트 (선택)' : '반려 사유'}
            rules={
              approveModal.action === 'rejected'
                ? [{ required: true, message: '반려 사유를 입력해주세요.' }]
                : []
            }
          >
            <TextArea rows={4} placeholder="코멘트를 입력하세요..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
