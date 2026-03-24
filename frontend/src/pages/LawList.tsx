import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Table, Input, Select, Space, Typography, Button, Tree, Card, Modal, List, Popconfirm, message } from 'antd'
import { SearchOutlined, ApartmentOutlined, DeleteOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { lawsApi, departmentApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { TreeDataNode } from 'antd'

const { Title } = Typography

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

interface LawItem {
  id: number
  law_serial_no: number
  law_id: number
  law_name: string
  law_abbr?: string
  law_type: string
  proclaimed_date?: string
  enforced_date?: string
  revision_type?: string
  dept_name?: string
  ordinance_count?: number
}

interface OrdinanceMapping {
  mapping_id: number
  ordinance_id: number
  ordinance_name: string
  ordinance_category: string
  related_articles?: string
}

export default function LawList() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()
  const isAdmin = user?.user_type === 'ADMIN'

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [search, setSearch] = useState(() => searchParams.get('search') || '')
  const [revisionType, setRevisionType] = useState<string | undefined>(() => searchParams.get('revisionType') || undefined)
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>(() => searchParams.get('dept') || undefined)
  const [hasOrdinance, setHasOrdinance] = useState<boolean | undefined>(() => {
    const v = searchParams.get('hasOrdinance')
    return v === 'true' ? true : v === 'false' ? false : undefined
  })
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>(['__all__'])
  const [sidebarWidth, setSidebarWidth] = useState(220)
  const isResizing = useRef(false)

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
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [sidebarWidth])

  // 연계 자치법규 모달
  const [ordinanceModalOpen, setOrdinanceModalOpen] = useState(false)
  const [selectedLaw, setSelectedLaw] = useState<LawItem | null>(null)

  // 소관부서 트리 조회
  const { data: departmentTree } = useQuery<DepartmentTreeResponse>({
    queryKey: ['department-tree'],
    queryFn: () => departmentApi.getTree(),
  })

  // 전체 법령 수 조회 (트리 루트용)
  const { data: totalLawCount } = useQuery({
    queryKey: ['laws-total-count'],
    queryFn: () => lawsApi.getCount({}),
  })

  // 트리 데이터 변환 (부서 마스터 ID 기준)
  const treeData: TreeDataNode[] = useMemo(() => {
    if (!departmentTree?.bureaus) return []

    const buildChildren = (nodes: DepartmentTreeNode[]): TreeDataNode[] => {
      return nodes.map(node => ({
        title: `${node.name} (${node.ordinance_count})`,
        key: String(node.id),
        children: node.children.length > 0 ? buildChildren(node.children) : undefined,
      }))
    }

    const totalCount = totalLawCount?.count || 0

    return [
      {
        title: `전체 (${totalCount})`,
        key: '__all__',
        icon: <ApartmentOutlined />,
        children: buildChildren(departmentTree.bureaus),
      },
    ]
  }, [departmentTree, totalLawCount])

  // 제개정구분 목록 조회
  const { data: revisionTypes } = useQuery({
    queryKey: ['law-revision-types'],
    queryFn: () => lawsApi.getRevisionTypes(),
  })

  // 법령 목록 조회
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['laws', page, search, revisionType, selectedDepartment, hasOrdinance],
    queryFn: () =>
      lawsApi.getList({
        page,
        size: 20,
        search: search || undefined,
        revision_type: revisionType,
        department_id: selectedDepartment,
        has_ordinance: hasOrdinance,
      }),
    enabled: initialLoaded,
  })

  // 법령 개수 조회
  const { data: countData } = useQuery({
    queryKey: ['laws-count', search, revisionType, selectedDepartment, hasOrdinance],
    queryFn: () =>
      lawsApi.getCount({
        search: search || undefined,
        revision_type: revisionType,
        department_id: selectedDepartment,
        has_ordinance: hasOrdinance,
      }),
    enabled: initialLoaded,
  })

  // 연계 자치법규 조회
  const { data: ordinances, isLoading: ordinancesLoading } = useQuery({
    queryKey: ['law-ordinances', selectedLaw?.id],
    queryFn: () => lawsApi.getOrdinances(selectedLaw!.id),
    enabled: !!selectedLaw,
  })

  // 연계 매핑 삭제
  const deleteMappingMutation = useMutation({
    mutationFn: (mappingId: number) => lawsApi.deleteOrdinanceMapping(mappingId),
    onSuccess: () => {
      message.success('연계가 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['law-ordinances', selectedLaw?.id] })
      queryClient.invalidateQueries({ queryKey: ['laws'] })
    },
    onError: () => {
      message.error('삭제에 실패했습니다.')
    },
  })

  // 상위법령 삭제 (관리자 전용)
  const deleteLawMutation = useMutation({
    mutationFn: (lawId: number) => lawsApi.delete(lawId),
    onSuccess: () => {
      message.success('상위법령이 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['laws'] })
      queryClient.invalidateQueries({ queryKey: ['laws-count'] })
    },
    onError: (error: any) => {
      message.error(error?.response?.data?.detail || '상위법령 삭제에 실패했습니다.')
    },
  })

  // 최초 로딩 시 DB에서 불러오기
  useEffect(() => {
    setInitialLoaded(true)
  }, [])

  // 필터 상태 변경 시 URL 쿼리 파라미터 업데이트
  useEffect(() => {
    const params = new URLSearchParams()
    if (page > 1) params.set('page', String(page))
    if (search) params.set('search', search)
    if (revisionType) params.set('revisionType', revisionType)
    if (selectedDepartment) params.set('dept', selectedDepartment)
    if (hasOrdinance !== undefined) params.set('hasOrdinance', String(hasOrdinance))
    setSearchParams(params, { replace: true })
  }, [page, search, revisionType, selectedDepartment, hasOrdinance, setSearchParams])

  const onTreeSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string
    if (key === '__all__') {
      setSelectedDepartment(undefined)
    } else if (!key) {
      setSelectedDepartment(undefined)
    } else {
      setSelectedDepartment(key)
    }
    setPage(1)
  }

  const onTreeExpand = (keys: React.Key[]) => {
    setExpandedKeys(keys)
  }

  const handleShowOrdinances = (record: LawItem) => {
    setSelectedLaw(record)
    setOrdinanceModalOpen(true)
  }

  const columns = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      width: 350,
      ellipsis: true,
      render: (text: string, record: LawItem) => (
        <a onClick={() => handleShowOrdinances(record)}>{text}</a>
      ),
    },
    {
      title: '법령구분',
      dataIndex: 'law_type',
      key: 'law_type',
      width: 100,
    },
    {
      title: '제개정',
      dataIndex: 'revision_type',
      key: 'revision_type',
      width: 100,
    },
    {
      title: '공포일',
      dataIndex: 'proclaimed_date',
      key: 'proclaimed_date',
      width: 110,
    },
    {
      title: '시행일',
      dataIndex: 'enforced_date',
      key: 'enforced_date',
      width: 110,
    },
    {
      title: '자치법규',
      dataIndex: 'ordinance_count',
      key: 'ordinance_count',
      width: 100,
      align: 'center' as const,
      render: (count: number, record: LawItem) => (
        <a onClick={() => handleShowOrdinances(record)}>{count || 0}</a>
      ),
    },
    ...(isAdmin ? [{
      title: '작업',
      key: 'actions',
      width: 90,
      align: 'center' as const,
      render: (_: unknown, record: LawItem) => (
        <Popconfirm
          title="상위법령 삭제"
          description={`'${record.law_name}'을(를) 삭제하시겠습니까?`}
          okText="삭제"
          cancelText="취소"
          onConfirm={() => deleteLawMutation.mutate(record.id)}
        >
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            loading={deleteLawMutation.isPending}
          />
        </Popconfirm>
      ),
    }] : []),
  ]

  return (
    <div>
      <Title level={4}>상위법령 목록</Title>

      <div style={{ display: 'flex', gap: 16 }}>
        {/* 담당부서 사이드 네비 */}
        <div style={{ width: sidebarWidth, flexShrink: 0, position: 'relative' }}>
          <Card
            size="small"
            title="담당부서"
            style={{ position: 'sticky', top: 16 }}
            styles={{ body: { maxHeight: 'calc(100vh - 200px)', overflow: 'auto' } }}
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
          {/* 리사이즈 핸들 */}
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

        {/* 메인 콘텐츠 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Space style={{ marginBottom: 16 }} wrap>
            <Input
              placeholder="법령명 검색"
              defaultValue={search}
              onPressEnter={(e) => setSearch((e.target as HTMLInputElement).value)}
              onChange={(e) => !e.target.value && setSearch('')}
              style={{ width: 300 }}
              allowClear
              suffix={
                <SearchOutlined
                  style={{ cursor: 'pointer', color: '#1890ff' }}
                  onClick={() => {
                    const input = document.querySelector('input[placeholder="법령명 검색"]') as HTMLInputElement
                    if (input) setSearch(input.value)
                  }}
                />
              }
            />
            <Select
              placeholder="제개정구분"
              style={{ width: 150 }}
              allowClear
              value={revisionType}
              onChange={(value) => { setRevisionType(value); setPage(1) }}
              options={revisionTypes?.map((t: { type: string; count: number }) => ({
                value: t.type,
                label: `${t.type} (${t.count})`,
              })) || []}
            />
            <Select
              placeholder="자치법규 연결"
              style={{ width: 160 }}
              allowClear
              value={hasOrdinance}
              onChange={(value) => { setHasOrdinance(value); setPage(1) }}
              options={[
                { value: true, label: '연결 있음' },
                { value: false, label: '미연결' },
              ]}
            />
            <Button
              icon={<SearchOutlined />}
              onClick={() => refetch()}
              loading={isLoading}
            >
              조회
            </Button>
          </Space>

          <Table
            columns={columns}
            dataSource={data || []}
            rowKey="id"
            loading={isLoading}
            scroll={{ x: 900 }}
            pagination={{
              current: page,
              total: countData?.count || 0,
              pageSize: 20,
              onChange: setPage,
              showTotal: (total) => `총 ${total}건`,
            }}
          />
        </div>
      </div>

      <Modal
        title={`연계 자치법규 - ${selectedLaw?.law_name || ''}`}
        open={ordinanceModalOpen}
        onCancel={() => {
          setOrdinanceModalOpen(false)
          setSelectedLaw(null)
        }}
        footer={null}
        width={700}
      >
        <List
          loading={ordinancesLoading}
          dataSource={ordinances || []}
          locale={{ emptyText: '연계된 자치법규가 없습니다' }}
          renderItem={(item: OrdinanceMapping) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="delete"
                  title="연계 삭제"
                  description="이 자치법규 연계를 삭제하시겠습니까?"
                  onConfirm={() => deleteMappingMutation.mutate(item.mapping_id)}
                  okText="삭제"
                  cancelText="취소"
                >
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    loading={deleteMappingMutation.isPending}
                  />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={
                  <a href={`/ordinances/${item.ordinance_id}`} target="_blank" rel="noopener noreferrer">
                    {item.ordinance_name}
                  </a>
                }
                description={
                  <Space>
                    <span>{item.ordinance_category}</span>
                    {item.related_articles && <span>| 관련조문: {item.related_articles}</span>}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  )
}
