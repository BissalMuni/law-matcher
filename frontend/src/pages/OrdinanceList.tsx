import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Input, Select, Space, Typography, Button, message, Upload, Card, Modal, Form, Spin, List, Tabs, DatePicker, Checkbox, Menu } from 'antd'
import { SyncOutlined, SearchOutlined, UploadOutlined, PlusOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi, ordinanceManagementApi } from '../services/api'
import type { UploadProps } from 'antd'

interface OrdinanceSearchResultItem {
  serial_no: string
  name: string
  ordinance_id: string
  enacted_date?: string
  promulgation_no?: string
  revision_type?: string
  org_name?: string
  category?: string
  enforced_date?: string
  detail_link?: string
  field_name?: string
}

const { Title } = Typography

interface DepartmentItem {
  name: string
  count: number
}

export default function OrdinanceList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [pageSize, setPageSize] = useState(() => {
    const s = searchParams.get('size')
    return s ? parseInt(s, 10) : 20
  })
  const [search, setSearch] = useState(() => searchParams.get('search') || '')
  const [category, setCategory] = useState<string | undefined>(() => searchParams.get('category') || undefined)
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>(() => searchParams.get('department') || undefined)
  const [noParentLawFilter, setNoParentLawFilter] = useState<string | undefined>(() => searchParams.get('noParentLaw') || undefined)
  const [needsRevisionFilter, setNeedsRevisionFilter] = useState<string | undefined>(() => searchParams.get('needsRevision') || undefined)
  const [revisionType, setRevisionType] = useState<string | undefined>(() => searchParams.get('revisionType') || undefined)
  const [excludeOtherLawRevision, setExcludeOtherLawRevision] = useState(() => searchParams.get('excludeOtherLaw') === 'true')
  const [reviewResultFilter, setReviewResultFilter] = useState<string | undefined>(() => searchParams.get('reviewResult') || undefined)
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [passwordModalOpen, setPasswordModalOpen] = useState(false)
  const [passwordAction, setPasswordAction] = useState<'sync' | 'upload' | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [form] = Form.useForm()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createModalTab, setCreateModalTab] = useState('api')
  const [apiSearchQuery, setApiSearchQuery] = useState('')
  const [apiSearchResults, setApiSearchResults] = useState<OrdinanceSearchResultItem[]>([])
  const [apiSearchLoading, setApiSearchLoading] = useState(false)
  const [selectedOrdinance, setSelectedOrdinance] = useState<OrdinanceSearchResultItem | null>(null)
  const [departmentInput, setDepartmentInput] = useState('')
  const [manualForm] = Form.useForm()
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

  // 소관부서 목록 조회
  const { data: departments } = useQuery({
    queryKey: ['ordinance-departments'],
    queryFn: () => ordinanceApi.getDepartments(),
  })

  // 제개정구분 목록 조회
  const { data: revisionTypes } = useQuery({
    queryKey: ['ordinance-revision-types'],
    queryFn: () => ordinanceApi.getRevisionTypes(),
  })

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['ordinances', page, pageSize, search, category, selectedDepartment, noParentLawFilter, needsRevisionFilter, revisionType, excludeOtherLawRevision, reviewResultFilter],
    queryFn: () =>
      ordinanceApi.getList({
        page,
        size: pageSize,
        search: search || undefined,
        category,
        department: selectedDepartment,
        no_parent_law_filter: noParentLawFilter,
        needs_revision_filter: needsRevisionFilter,
        revision_type: revisionType,
        exclude_other_law_revision: excludeOtherLawRevision || undefined,
        review_result_filter: reviewResultFilter,
      }),
    enabled: initialLoaded,
  })

  // 최초 로딩 시 DB에서 불러오기
  useEffect(() => {
    setInitialLoaded(true)
  }, [])

  // 필터 상태 변경 시 URL 쿼리 파라미터 업데이트
  useEffect(() => {
    const params = new URLSearchParams()
    if (page > 1) params.set('page', String(page))
    if (pageSize !== 20) params.set('size', String(pageSize))
    if (search) params.set('search', search)
    if (category) params.set('category', category)
    if (selectedDepartment) params.set('department', selectedDepartment)
    if (noParentLawFilter) params.set('noParentLaw', noParentLawFilter)
    if (needsRevisionFilter) params.set('needsRevision', needsRevisionFilter)
    if (revisionType) params.set('revisionType', revisionType)
    if (excludeOtherLawRevision) params.set('excludeOtherLaw', 'true')
    if (reviewResultFilter) params.set('reviewResult', reviewResultFilter)
    setSearchParams(params, { replace: true })
  }, [page, pageSize, search, category, selectedDepartment, noParentLawFilter, needsRevisionFilter, revisionType, excludeOtherLawRevision, reviewResultFilter, setSearchParams])

  // 법제처 API 동기화
  const syncMutation = useMutation({
    mutationFn: (password: string) => ordinanceApi.syncFromMoleg({ password }),
    onSuccess: (result) => {
      message.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['ordinances'] })
      queryClient.invalidateQueries({ queryKey: ['ordinance-departments'] })
      setPasswordModalOpen(false)
      form.resetFields()
    },
    onError: (error: any) => {
      if (error.response?.status === 403) {
        message.error('관리자 비밀번호가 올바르지 않습니다.')
      } else {
        message.error('법제처 동기화 실패')
      }
    },
  })

  const handlePasswordSubmit = (values: { password: string }) => {
    if (passwordAction === 'sync') {
      syncMutation.mutate(values.password)
    } else if (passwordAction === 'upload' && uploadFile) {
      handleUploadWithPassword(uploadFile, values.password)
    }
  }

  const handleUploadWithPassword = async (file: File, password: string) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/v1/ordinances/upload', {
        method: 'POST',
        headers: {
          'X-Admin-Password': password,
        },
        body: formData,
      })

      if (response.ok) {
        const result = await response.json()
        message.success(`${result.updated}건 소관부서 정보 업데이트 완료`)
        queryClient.invalidateQueries({ queryKey: ['ordinances'] })
        queryClient.invalidateQueries({ queryKey: ['ordinance-departments'] })
        setPasswordModalOpen(false)
        form.resetFields()
        setUploadFile(null)
      } else if (response.status === 403) {
        message.error('관리자 비밀번호가 올바르지 않습니다.')
      } else {
        message.error('엑셀 업로드 실패')
      }
    } catch (error) {
      message.error('엑셀 업로드 실패')
    }
  }

  // 엑셀 업로드
  const uploadProps: UploadProps = {
    name: 'file',
    accept: '.xlsx,.xls',
    showUploadList: false,
    beforeUpload: (file) => {
      setUploadFile(file)
      setPasswordAction('upload')
      setPasswordModalOpen(true)
      return false // 자동 업로드 방지
    },
  }

  // 자치법규 등록 (API 검색 결과로)
  const registerMutation = useMutation({
    mutationFn: ordinanceManagementApi.registerFromApi,
    onSuccess: (result) => {
      message.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['ordinances'] })
      queryClient.invalidateQueries({ queryKey: ['ordinance-departments'] })
      handleCloseCreateModal()
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '자치법규 등록 실패')
    },
  })

  // 자치법규 수기 등록
  const createMutation = useMutation({
    mutationFn: ordinanceManagementApi.create,
    onSuccess: (result) => {
      message.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['ordinances'] })
      queryClient.invalidateQueries({ queryKey: ['ordinance-departments'] })
      handleCloseCreateModal()
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '자치법규 등록 실패')
    },
  })

  // 자치법규 정보 일괄 업데이트
  const updateOrdinanceInfoMutation = useMutation({
    mutationFn: ordinanceManagementApi.updateAllInfo,
    onSuccess: (result) => {
      message.success(result.message)
      queryClient.invalidateQueries({ queryKey: ['ordinances'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '자치법규 정보 업데이트 실패')
    },
  })

  // 법제처 API에서 자치법규 검색
  const handleApiSearch = async () => {
    if (!apiSearchQuery.trim()) {
      message.warning('검색어를 입력하세요')
      return
    }
    setApiSearchLoading(true)
    setSelectedOrdinance(null)
    try {
      const result = await ordinanceManagementApi.searchFromApi(apiSearchQuery)
      if (result.success) {
        setApiSearchResults(result.items)
        if (result.items.length === 0) {
          message.info('검색 결과가 없습니다')
        }
      } else {
        message.error(result.message)
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '검색 실패')
    } finally {
      setApiSearchLoading(false)
    }
  }

  // 검색 결과에서 선택
  const handleSelectOrdinance = (item: OrdinanceSearchResultItem) => {
    setSelectedOrdinance(item)
  }

  // 선택한 자치법규 등록
  const handleRegisterOrdinance = () => {
    if (!selectedOrdinance) {
      message.warning('등록할 자치법규를 선택하세요')
      return
    }
    registerMutation.mutate({
      ...selectedOrdinance,
      department: departmentInput || undefined,
    })
  }

  // 모달 닫기
  const handleCloseCreateModal = () => {
    setCreateModalOpen(false)
    setCreateModalTab('api')
    setApiSearchQuery('')
    setApiSearchResults([])
    setSelectedOrdinance(null)
    setDepartmentInput('')
    manualForm.resetFields()
  }

  // 수기 등록 제출
  const handleManualSubmit = (values: any) => {
    createMutation.mutate({
      name: values.name,
      category: values.category || '조례',
      department: values.department,
      enacted_date: values.enacted_date?.format('YYYY-MM-DD'),
      enforced_date: values.enforced_date?.format('YYYY-MM-DD'),
    })
  }

  const columns = [
    {
      title: '담당부서',
      dataIndex: 'department',
      key: 'department',
      width: 150,
    },
    {
      title: '자치법규명',
      dataIndex: 'name',
      key: 'name',
      width: 400,
      ellipsis: true,
      render: (text: string, record: any) => (
        <a onClick={() => navigate(`/ordinances/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '종류',
      dataIndex: 'category',
      key: 'category',
      width: 100,
    },
    {
      title: '상위법령(개수)',
      dataIndex: 'parent_law_count',
      key: 'parent_law_count',
      width: 120,
      align: 'center' as const,
      render: (count: number, record: any) => {
        if (record.no_parent_law) {
          return <span style={{ color: '#999' }}>없음(확인)</span>
        }
        return count || 0
      },
    },
    {
      title: '개정여부',
      dataIndex: 'needs_revision',
      key: 'needs_revision',
      width: 80,
      align: 'center' as const,
      render: (value: number | null) => {
        if (value === null || value === undefined) return '-'
        return (
          <span style={{ color: value === 1 ? '#f5222d' : '#52c41a', fontSize: 48 }}>
            ●
          </span>
        )
      },
    },
    {
      title: '검토의견',
      dataIndex: 'latest_review_result',
      key: 'latest_review_result',
      width: 100,
      align: 'center' as const,
      render: (value: string | null, record: any) => {
        if (!value) return '-'
        const colorMap: Record<string, string> = {
          '개정필요': '#f5222d',
          '개정불필요': '#52c41a',
          '검토중': '#faad14',
          '보류': '#999',
        }
        return (
          <a
            onClick={() => navigate(`/ordinances/${record.id}`)}
            style={{ color: colorMap[value] || '#333' }}
          >
            {value}
          </a>
        )
      },
    },
  ]

  return (
    <div>
      <Title level={4}>자치법규 목록</Title>

      <div style={{ display: 'flex', gap: 16 }}>
        {/* 소관부서 사이드 네비 */}
        <div style={{ width: sidebarWidth, flexShrink: 0, position: 'relative' }}>
          <Card
            size="small"
            title="담당부서"
            style={{ position: 'sticky', top: 16 }}
            bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflow: 'auto', padding: 0 }}
          >
            <Menu
              mode="inline"
              selectedKeys={selectedDepartment ? [selectedDepartment] : ['__all__']}
              onClick={({ key }) => {
                if (key === '__all__') {
                  setSelectedDepartment(undefined)
                  setPage(1)
                } else {
                  setSelectedDepartment(key)
                  setPage(1)
                }
              }}
              items={[
                {
                  key: '__all__',
                  label: `전체 (${departments?.reduce((sum: number, d: DepartmentItem) => sum + d.count, 0) || 0})`,
                },
                ...(departments?.map((dept: DepartmentItem) => ({
                  key: dept.name,
                  label: `${dept.name} (${dept.count})`,
                })) || []),
              ]}
              style={{ border: 'none' }}
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
          placeholder="자치법규명 검색"
          defaultValue={search}
          onPressEnter={(e) => setSearch((e.target as HTMLInputElement).value)}
          onChange={(e) => !e.target.value && setSearch('')}
          style={{ width: 300 }}
          allowClear
          suffix={
            <SearchOutlined
              style={{ cursor: 'pointer', color: '#1890ff' }}
              onClick={() => {
                const input = document.querySelector('input[placeholder="자치법규명 검색"]') as HTMLInputElement
                if (input) setSearch(input.value)
              }}
            />
          }
        />
        <Select
          placeholder="분류"
          style={{ width: 120 }}
          allowClear
          value={category}
          onChange={setCategory}
          options={[
            { value: '조례', label: '조례' },
            { value: '규칙', label: '규칙' },
          ]}
        />
        <Select
          placeholder="상위법령"
          style={{ width: 160 }}
          allowClear
          value={noParentLawFilter}
          onChange={(value) => {
            setNoParentLawFilter(value)
            setPage(1)
          }}
          options={[
            { value: 'connected', label: '연결' },
            { value: 'confirmed_none', label: '없음 (상위법없음)' },
            { value: 'no_mapping', label: '미연결 (확인필요)' },
          ]}
        />
        <Select
          placeholder="개정대상"
          style={{ width: 140 }}
          allowClear
          value={needsRevisionFilter}
          onChange={(value) => {
            setNeedsRevisionFilter(value)
            setPage(1)
          }}
          options={[
            { value: 'needs_revision', label: '개정대상' },
            { value: 'no_revision', label: '대상아님' },
          ]}
        />
        <Select
          placeholder="제개정구분"
          style={{ width: 160 }}
          allowClear
          value={revisionType}
          onChange={(value) => {
            setRevisionType(value)
            setPage(1)
          }}
          options={revisionTypes?.map((rt: { revision_type: string; count: number }) => ({
            value: rt.revision_type,
            label: `${rt.revision_type} (${rt.count})`,
          })) || []}
        />
        <Checkbox
          checked={excludeOtherLawRevision}
          onChange={(e) => {
            setExcludeOtherLawRevision(e.target.checked)
            setPage(1)
          }}
        >
          타법개정 제외
        </Checkbox>
        <Select
          placeholder="검토결과"
          style={{ width: 140 }}
          allowClear
          value={reviewResultFilter}
          onChange={(value) => {
            setReviewResultFilter(value)
            setPage(1)
          }}
          options={[
            { value: '개정필요', label: '개정필요' },
            { value: '개정불필요', label: '개정불필요' },
            { value: '검토중', label: '검토중' },
            { value: '보류', label: '보류' },
            { value: '미검토', label: '미검토' },
          ]}
        />
        <Button
          icon={<SearchOutlined />}
          onClick={() => refetch()}
          loading={isLoading}
        >
          DB 조회
        </Button>
        <Button
          type="primary"
          icon={<SyncOutlined />}
          onClick={() => {
            setPasswordAction('sync')
            setPasswordModalOpen(true)
          }}
          loading={syncMutation.isPending}
        >
          법제처 동기화
        </Button>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>담당부서 엑셀 업로드</Button>
        </Upload>
        <a
          href="https://elis.go.kr/locgovalr/locgovSeAlrList"
          target="_blank"
          rel="noopener noreferrer"
        >
          소관부서별 자치법규 목록
        </a>
        <Button
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          신규
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => updateOrdinanceInfoMutation.mutate()}
          loading={updateOrdinanceInfoMutation.isPending}
        >
          업데이트
        </Button>
        <Button
          icon={<DownloadOutlined />}
          onClick={async () => {
            try {
              await ordinanceApi.exportExcel({
                category,
                department: selectedDepartment,
                search: search || undefined,
                no_parent_law_filter: noParentLawFilter,
                needs_revision_filter: needsRevisionFilter,
                revision_type: revisionType,
                exclude_other_law_revision: excludeOtherLawRevision || undefined,
              })
              message.success('엑셀 파일이 다운로드되었습니다.')
            } catch (error) {
              message.error('엑셀 다운로드 중 오류가 발생했습니다.')
            }
          }}
        >
          엑셀 다운로드
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1000 }}
        pagination={{
          current: page,
          total: data?.total || 0,
          pageSize: pageSize,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          onChange: (newPage, newSize) => {
            if (newSize !== pageSize) {
              setPageSize(newSize)
              setPage(1)
            } else {
              setPage(newPage)
            }
          },
          showTotal: (total) => `총 ${total}건`,
        }}
      />
        </div>
      </div>

      <Modal
        title="관리자 비밀번호 입력"
        open={passwordModalOpen}
        onCancel={() => {
          setPasswordModalOpen(false)
          form.resetFields()
          setUploadFile(null)
        }}
        onOk={() => form.submit()}
        confirmLoading={syncMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handlePasswordSubmit}>
          <Form.Item
            name="password"
            label="비밀번호"
            rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
          >
            <Input.Password placeholder="관리자 비밀번호" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="자치법규 신규 등록"
        open={createModalOpen}
        onCancel={handleCloseCreateModal}
        onOk={createModalTab === 'api' ? handleRegisterOrdinance : () => manualForm.submit()}
        okText="등록"
        okButtonProps={{
          disabled: createModalTab === 'api' ? !selectedOrdinance : false
        }}
        confirmLoading={registerMutation.isPending || createMutation.isPending}
        width={700}
      >
        <Tabs
          activeKey={createModalTab}
          onChange={setCreateModalTab}
          destroyInactiveTabPane={false}
          items={[
            {
              key: 'api',
              label: 'API 검색',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space.Compact style={{ width: '100%' }}>
                    <Input
                      placeholder="자치법규명 검색 (예: 청소년)"
                      value={apiSearchQuery}
                      onChange={(e) => setApiSearchQuery(e.target.value)}
                      onPressEnter={handleApiSearch}
                      style={{ flex: 1 }}
                    />
                    <Button
                      type="primary"
                      icon={<SearchOutlined />}
                      onClick={handleApiSearch}
                      loading={apiSearchLoading}
                    >
                      검색
                    </Button>
                  </Space.Compact>

                  {apiSearchLoading ? (
                    <div style={{ textAlign: 'center', padding: 20 }}>
                      <Spin />
                    </div>
                  ) : apiSearchResults.length > 0 ? (
                    <List
                      size="small"
                      bordered
                      dataSource={apiSearchResults}
                      style={{ maxHeight: 300, overflow: 'auto' }}
                      renderItem={(item) => (
                        <List.Item
                          onClick={() => handleSelectOrdinance(item)}
                          style={{
                            cursor: 'pointer',
                            background: selectedOrdinance?.ordinance_id === item.ordinance_id ? '#e6f7ff' : undefined,
                          }}
                        >
                          <List.Item.Meta
                            title={item.name}
                            description={
                              <Space size="small" wrap>
                                <span>{item.category}</span>
                                {item.revision_type && <span>| {item.revision_type}</span>}
                                {item.enacted_date && <span>| 공포: {item.enacted_date}</span>}
                                {item.enforced_date && <span>| 시행: {item.enforced_date}</span>}
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : apiSearchQuery && !apiSearchLoading ? (
                    <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                      검색 결과가 없습니다
                    </div>
                  ) : null}

                  {selectedOrdinance && (
                    <Card size="small" title="선택된 자치법규">
                      <p><strong>자치법규명:</strong> {selectedOrdinance.name}</p>
                      <p><strong>종류:</strong> {selectedOrdinance.category}</p>
                      <p><strong>공포일:</strong> {selectedOrdinance.enacted_date || '-'}</p>
                      <p><strong>시행일:</strong> {selectedOrdinance.enforced_date || '-'}</p>
                      <p><strong>제개정:</strong> {selectedOrdinance.revision_type || '-'}</p>
                      <Select
                        placeholder="소관부서 선택"
                        value={departmentInput || undefined}
                        onChange={(value) => setDepartmentInput(value || '')}
                        style={{ marginTop: 8, width: '100%' }}
                        allowClear
                        showSearch
                        optionFilterProp="label"
                        options={departments?.map((dept: DepartmentItem) => ({
                          value: dept.name,
                          label: dept.name,
                        })) || []}
                      />
                    </Card>
                  )}
                </Space>
              ),
            },
            {
              key: 'manual',
              label: '수기 등록',
              children: (
                <Form
                  form={manualForm}
                  layout="vertical"
                  onFinish={handleManualSubmit}
                  initialValues={{ category: '조례' }}
                >
                  <Form.Item
                    name="name"
                    label="자치법규명"
                    rules={[{ required: true, message: '자치법규명을 입력하세요' }]}
                  >
                    <Input placeholder="예: 서울특별시 관악구 청소년 조례" />
                  </Form.Item>
                  <Form.Item
                    name="category"
                    label="종류"
                    rules={[{ required: true, message: '종류를 선택하세요' }]}
                  >
                    <Select
                      options={[
                        { value: '조례', label: '조례' },
                        { value: '규칙', label: '규칙' },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item
                    name="department"
                    label="소관부서"
                  >
                    <Select
                      placeholder="소관부서 선택"
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      options={departments?.map((dept: DepartmentItem) => ({
                        value: dept.name,
                        label: dept.name,
                      })) || []}
                    />
                  </Form.Item>
                  <Form.Item
                    name="enacted_date"
                    label="공포일"
                  >
                    <DatePicker style={{ width: '100%' }} placeholder="공포일 선택" />
                  </Form.Item>
                  <Form.Item
                    name="enforced_date"
                    label="시행일"
                  >
                    <DatePicker style={{ width: '100%' }} placeholder="시행일 선택" />
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  )
}
