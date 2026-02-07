import { useState } from 'react'
import {
  Table,
  Input,
  Space,
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Modal,
  Form,
  message,
  Popconfirm,
  Tabs,
  Select,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { departmentApi } from '../services/api'

const { Title } = Typography
const { Search } = Input

interface DepartmentTreeNode {
  id: number
  code: string
  name: string
  department_type?: string
  manager_name?: string
  phone?: string
  sort_order: number
  ordinance_count: number
  children: DepartmentTreeNode[]
}

interface DepartmentTreeResponse {
  bureaus: DepartmentTreeNode[]
  zones: DepartmentTreeNode[]
}

export default function DepartmentList() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingDepartment, setEditingDepartment] = useState<DepartmentTreeNode | null>(null)
  const [activeTab, setActiveTab] = useState('bureaus')
  const [form] = Form.useForm()

  const { data: treeData, isLoading } = useQuery<DepartmentTreeResponse>({
    queryKey: ['departments-tree'],
    queryFn: () => departmentApi.getTree(),
  })

  const { data: summary } = useQuery({
    queryKey: ['departments-summary'],
    queryFn: () => departmentApi.getSummary(),
  })

  const createMutation = useMutation({
    mutationFn: departmentApi.create,
    onSuccess: () => {
      message.success('부서가 추가되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['departments-tree'] })
      queryClient.invalidateQueries({ queryKey: ['departments-summary'] })
      handleModalClose()
    },
    onError: () => {
      message.error('부서 추가에 실패했습니다.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      departmentApi.update(id, data),
    onSuccess: () => {
      message.success('부서 정보가 수정되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['departments-tree'] })
      handleModalClose()
    },
    onError: () => {
      message.error('부서 수정에 실패했습니다.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: departmentApi.delete,
    onSuccess: () => {
      message.success('부서가 삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['departments-tree'] })
      queryClient.invalidateQueries({ queryKey: ['departments-summary'] })
    },
    onError: () => {
      message.error('부서 삭제에 실패했습니다.')
    },
  })

  const handleModalClose = () => {
    setIsModalOpen(false)
    setEditingDepartment(null)
    form.resetFields()
  }

  const handleEdit = (department: DepartmentTreeNode) => {
    setEditingDepartment(department)
    form.setFieldsValue(department)
    setIsModalOpen(true)
  }

  const handleSubmit = async (values: any) => {
    if (editingDepartment) {
      updateMutation.mutate({ id: editingDepartment.id, data: values })
    } else {
      createMutation.mutate(values)
    }
  }

  const totalOrdinances = summary?.reduce(
    (sum: number, d: any) => sum + (d.ordinance_count || 0),
    0
  ) || 0

  const totalPendingReviews = summary?.reduce(
    (sum: number, d: any) => sum + (d.pending_review_count || 0),
    0
  ) || 0

  // Filter tree based on search
  const filterTree = (nodes: DepartmentTreeNode[]): DepartmentTreeNode[] => {
    if (!search) return nodes

    return nodes.map(node => {
      const matchesSearch = node.name.toLowerCase().includes(search.toLowerCase()) ||
                           (node.manager_name && node.manager_name.toLowerCase().includes(search.toLowerCase()))
      const filteredChildren = node.children.filter(child =>
        child.name.toLowerCase().includes(search.toLowerCase()) ||
        (child.manager_name && child.manager_name.toLowerCase().includes(search.toLowerCase()))
      )

      if (matchesSearch || filteredChildren.length > 0) {
        return { ...node, children: filteredChildren }
      }
      return null
    }).filter(Boolean) as DepartmentTreeNode[]
  }

  const filteredBureaus = filterTree(treeData?.bureaus || [])
  const filteredZones = filterTree(treeData?.zones || [])

  // Get parent departments for dropdown
  const parentBureaus = treeData?.bureaus || []
  const parentZones = treeData?.zones || []

  // Bureau/Department columns
  let bureauRowIndex = 0
  const bureauColumns = [
    {
      title: '연번',
      key: 'index',
      width: 80,
      align: 'center' as const,
      render: (_: any, record: DepartmentTreeNode) => {
        if (record.department_type === 'bureau') return ''
        bureauRowIndex++
        return bureauRowIndex
      },
    },
    {
      title: '부서명',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: DepartmentTreeNode) => (
        <span style={{ fontWeight: record.department_type === 'bureau' ? 'bold' : 'normal' }}>
          {text}
        </span>
      ),
    },
    {
      title: '서무주임',
      dataIndex: 'manager_name',
      key: 'manager_name',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '연락처',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '소관법규',
      dataIndex: 'ordinance_count',
      key: 'ordinance_count',
      width: 100,
      align: 'center' as const,
      render: (count: number) => count || 0,
    },
    {
      title: '작업',
      key: 'action',
      width: 120,
      render: (_: any, record: DepartmentTreeNode) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="부서 삭제"
            description="이 부서를 삭제하시겠습니까?"
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

  // Zone/Neighborhood columns
  let zoneRowIndex = 0
  const zoneColumns = [
    {
      title: '연번',
      key: 'index',
      width: 80,
      align: 'center' as const,
      render: (_: any, record: DepartmentTreeNode) => {
        if (record.department_type === 'zone') return ''
        zoneRowIndex++
        return zoneRowIndex
      },
    },
    {
      title: '동명',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: DepartmentTreeNode) => (
        <span style={{ fontWeight: record.department_type === 'zone' ? 'bold' : 'normal' }}>
          {text}
        </span>
      ),
    },
    {
      title: '서무주임',
      dataIndex: 'manager_name',
      key: 'manager_name',
      width: 120,
      render: (text: string) => text || '-',
    },
    {
      title: '연락처',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
      render: (text: string) => text || '-',
    },
    {
      title: '작업',
      key: 'action',
      width: 120,
      render: (_: any, record: DepartmentTreeNode) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="동 삭제"
            description="이 동을 삭제하시겠습니까?"
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

  // Reset row counters when rendering
  bureauRowIndex = 0
  zoneRowIndex = 0

  return (
    <div>
      <Title level={4}>부서(동) 서무주임 현황</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="전체 부서"
              value={summary?.length || 0}
              suffix="개"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="소관 자치법규"
              value={totalOrdinances}
              prefix={<FileTextOutlined />}
              suffix="건"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="검토 대기"
              value={totalPendingReviews}
              prefix={<ExclamationCircleOutlined />}
              suffix="건"
              valueStyle={{ color: totalPendingReviews > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Search
          placeholder="부서명 또는 서무주임 검색"
          onSearch={setSearch}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
        >
          부서 추가
        </Button>
      </Space>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'bureaus',
            label: '국/과',
            children: (
              <Table
                columns={bureauColumns}
                dataSource={filteredBureaus}
                rowKey="id"
                loading={isLoading}
                pagination={false}
                expandable={{
                  defaultExpandAllRows: true,
                }}
                rowClassName={(record) =>
                  record.department_type === 'bureau' ? 'group-header-row' : ''
                }
              />
            ),
          },
          {
            key: 'zones',
            label: '권역/동',
            children: (
              <Table
                columns={zoneColumns}
                dataSource={filteredZones}
                rowKey="id"
                loading={isLoading}
                pagination={false}
                expandable={{
                  defaultExpandAllRows: true,
                }}
                rowClassName={(record) =>
                  record.department_type === 'zone' ? 'group-header-row' : ''
                }
              />
            ),
          },
        ]}
      />

      <Modal
        title={editingDepartment ? '부서 수정' : '부서 추가'}
        open={isModalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="code"
            label="부서코드"
            rules={[{ required: true, message: '부서코드를 입력하세요' }]}
          >
            <Input disabled={!!editingDepartment} />
          </Form.Item>
          <Form.Item
            name="name"
            label="부서명"
            rules={[{ required: true, message: '부서명을 입력하세요' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="parent_code" label="상위부서">
            <Select placeholder="상위부서 선택" allowClear>
              <Select.OptGroup label="국/단/소">
                {parentBureaus.map((b) => (
                  <Select.Option key={b.code} value={b.code}>
                    {b.name}
                  </Select.Option>
                ))}
              </Select.OptGroup>
              <Select.OptGroup label="권역">
                {parentZones.map((z) => (
                  <Select.Option key={z.code} value={z.code}>
                    {z.name}
                  </Select.Option>
                ))}
              </Select.OptGroup>
            </Select>
          </Form.Item>
          <Form.Item name="department_type" label="부서유형">
            <Select placeholder="부서유형 선택">
              <Select.Option value="bureau">국/단/소</Select.Option>
              <Select.Option value="department">과</Select.Option>
              <Select.Option value="zone">권역</Select.Option>
              <Select.Option value="neighborhood">동</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="manager_name" label="서무주임 성명">
            <Input placeholder="성명 입력" />
          </Form.Item>
          <Form.Item name="phone" label="연락처">
            <Input placeholder="연락처 입력" />
          </Form.Item>
          <Form.Item name="sort_order" label="정렬순서">
            <Input type="number" placeholder="10, 20, 30..." />
          </Form.Item>
        </Form>
      </Modal>

      <style>{`
        .group-header-row {
          background-color: #fafafa;
          font-weight: bold;
        }
        .group-header-row:hover {
          background-color: #f0f0f0 !important;
        }
      `}</style>
    </div>
  )
}
