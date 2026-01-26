import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Table, Input, Select, Space, Typography, Button, Tree, Row, Col, Card, Modal, List } from 'antd'
import { SearchOutlined, ApartmentOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { lawsApi } from '../services/api'
import type { TreeDataNode } from 'antd'

const { Title } = Typography

interface DepartmentItem {
  name: string
  count: number
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
}

interface OrdinanceMapping {
  mapping_id: number
  ordinance_id: number
  ordinance_name: string
  ordinance_category: string
  related_articles?: string
}

export default function LawList() {
  const [searchParams, setSearchParams] = useSearchParams()

  // URL 쿼리 파라미터에서 초기값 읽기
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [search, setSearch] = useState(() => searchParams.get('search') || '')
  const [lawType, setLawType] = useState<string | undefined>(() => searchParams.get('lawType') || undefined)
  const [selectedDepartment, setSelectedDepartment] = useState<string | undefined>(() => searchParams.get('dept') || undefined)
  const [initialLoaded, setInitialLoaded] = useState(false)
  const [treeCollapsed, setTreeCollapsed] = useState(false)
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>(['all'])

  // 연계 자치법규 모달
  const [ordinanceModalOpen, setOrdinanceModalOpen] = useState(false)
  const [selectedLaw, setSelectedLaw] = useState<LawItem | null>(null)

  // 소관부처 목록 조회
  const { data: departments } = useQuery({
    queryKey: ['law-departments'],
    queryFn: () => lawsApi.getDepartments(),
  })

  // 법령 유형 목록 조회
  const { data: lawTypes } = useQuery({
    queryKey: ['law-types'],
    queryFn: () => lawsApi.getTypes(),
  })

  // 법령 목록 조회
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['laws', page, search, lawType, selectedDepartment],
    queryFn: () =>
      lawsApi.getList({
        page,
        size: 20,
        search: search || undefined,
        law_type: lawType,
        dept_name: selectedDepartment,
      }),
    enabled: initialLoaded,
  })

  // 법령 개수 조회
  const { data: countData } = useQuery({
    queryKey: ['laws-count', search, lawType, selectedDepartment],
    queryFn: () =>
      lawsApi.getCount({
        search: search || undefined,
        law_type: lawType,
        dept_name: selectedDepartment,
      }),
    enabled: initialLoaded,
  })

  // 연계 자치법규 조회
  const { data: ordinances, isLoading: ordinancesLoading } = useQuery({
    queryKey: ['law-ordinances', selectedLaw?.id],
    queryFn: () => lawsApi.getOrdinances(selectedLaw!.id),
    enabled: !!selectedLaw,
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
    if (lawType) params.set('lawType', lawType)
    if (selectedDepartment) params.set('dept', selectedDepartment)
    setSearchParams(params, { replace: true })
  }, [page, search, lawType, selectedDepartment, setSearchParams])

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
      title: '소관부처',
      dataIndex: 'dept_name',
      key: 'dept_name',
      width: 150,
    },
  ]

  return (
    <div>
      <Title level={4}>상위법령 목록</Title>

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
                담당부서
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
              placeholder="법령구분"
              style={{ width: 120 }}
              allowClear
              value={lawType}
              onChange={setLawType}
              options={lawTypes?.map((t: { type: string; count: number }) => ({
                value: t.type,
                label: `${t.type} (${t.count})`,
              })) || []}
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
        </Col>
      </Row>

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
            <List.Item>
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
