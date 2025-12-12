import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Input, Select, Space, Typography, Button, message, Upload, Tree, Row, Col, Card, Modal, Form } from 'antd'
import { SyncOutlined, SearchOutlined, UploadOutlined, ApartmentOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi } from '../services/api'
import type { UploadProps, TreeDataNode } from 'antd'

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
  const [search, setSearch] = useState(() => searchParams.get('search') || '')
  const [category, setCategory] = useState<string | undefined>(() => searchParams.get('category') || undefined)
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>(() => searchParams.get('department') || undefined)
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [treeCollapsed, setTreeCollapsed] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>(['all'])
  const [passwordModalOpen, setPasswordModalOpen] = useState(false)
  const [passwordAction, setPasswordAction] = useState<'sync' | 'upload' | null>(null)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [form] = Form.useForm()

  // 소관부서 목록 조회
  const { data: departments } = useQuery({
    queryKey: ['ordinance-departments'],
    queryFn: () => ordinanceApi.getDepartments(),
  })

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['ordinances', page, search, category, selectedDepartment],
    queryFn: () =>
      ordinanceApi.getList({
        page,
        size: 20,
        search: search || undefined,
        category,
        department: selectedDepartment,
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
    if (search) params.set('search', search)
    if (category) params.set('category', category)
    if (selectedDepartment) params.set('department', selectedDepartment)
    setSearchParams(params, { replace: true })
  }, [page, search, category, selectedDepartment, setSearchParams])

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

  // 트리 데이터 생성
  const treeData: TreeDataNode[] = [
    {
      title: `전체 (${departments?.reduce((sum: number, d: DepartmentItem) => sum + d.count, 0) || 0})`,
      key: 'all',
      icon: <ApartmentOutlined />,
      children: departments?.map((dept: DepartmentItem) => ({
        title: `${dept.name} (${dept.count})`,
        key: dept.name,
      })) || [],
    },
  ]

  const onTreeSelect = (selectedKeys: React.Key[]) => {
    const key = selectedKeys[0] as string
    if (key === 'all') {
      // "전체" 클릭 시 트리 확장/축소 토글
      setExpandedKeys(prev =>
        prev.includes('all') ? [] : ['all']
      )
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

  const columns = [
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
      title: '제개정',
      dataIndex: 'revision_type',
      key: 'revision_type',
      width: 100,
    },
    {
      title: '공포일',
      dataIndex: 'enacted_date',
      key: 'enacted_date',
      width: 110,
    },
    {
      title: '시행일',
      dataIndex: 'enforced_date',
      key: 'enforced_date',
      width: 110,
    },
    {
      title: '소관부서',
      dataIndex: 'department',
      key: 'department',
      width: 150,
    },
  ]

  return (
    <div>
      <Title level={4}>자치법규 목록</Title>

      <Row gutter={16}>
        <Col style={{ width: treeCollapsed ? 105 : 'calc((100% - 48px) * 5 / 24)', transition: 'width 0.3s ease', flexShrink: 0 }}>
          <Card
            size="small"
            title={
              <div
                onClick={() => setTreeCollapsed(!treeCollapsed)}
                style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 4 }}
              >
                {treeCollapsed ? <RightOutlined /> : <LeftOutlined />}
                소관부서
              </div>
            }
            style={{ height: 'calc(100vh - 220px)', overflow: 'auto' }}
            styles={{ body: { display: treeCollapsed ? 'none' : 'block' } }}
          >
            <Tree
              showIcon
              expandedKeys={expandedKeys}
              onExpand={onTreeExpand}
              treeData={treeData}
              onSelect={onTreeSelect}
              selectedKeys={selectedDepartment ? [selectedDepartment] : ['all']}
            />
          </Card>
        </Col>
        <Col style={{ flex: 1, transition: 'all 0.3s ease' }}>
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
              <Button icon={<UploadOutlined />}>소관부서 엑셀 업로드</Button>
            </Upload>
            <a
              href="https://elis.go.kr/locgovalr/locgovSeAlrList"
              target="_blank"
              rel="noopener noreferrer"
            >
              소관부서별 자치법규 목록
            </a>
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
              pageSize: 20,
              onChange: setPage,
              showTotal: (total) => `총 ${total}건`,
            }}
          />
        </Col>
      </Row>

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
    </div>
  )
}
