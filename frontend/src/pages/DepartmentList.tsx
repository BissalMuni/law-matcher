import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

interface Department {
  id: number
  code: string
  name: string
  parent_code?: string
  phone?: string
  ordinance_count?: number
  pending_review_count?: number
}

export default function DepartmentList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null)
  const [form] = Form.useForm()

  const { data, isLoading } = useQuery({
    queryKey: ['departments', page, search],
    queryFn: () =>
      departmentApi.getList({
        page,
        size: 20,
        search: search || undefined,
      }),
  })

  const { data: summary } = useQuery({
    queryKey: ['departments-summary'],
    queryFn: () => departmentApi.getSummary(),
  })

  const createMutation = useMutation({
    mutationFn: departmentApi.create,
    onSuccess: () => {
      message.success('부서가 추가되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['departments'] })
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
      queryClient.invalidateQueries({ queryKey: ['departments'] })
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
      queryClient.invalidateQueries({ queryKey: ['departments'] })
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

  const handleEdit = (department: Department) => {
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
    (sum: number, d: Department) => sum + (d.ordinance_count || 0),
    0
  ) || 0

  const totalPendingReviews = summary?.reduce(
    (sum: number, d: Department) => sum + (d.pending_review_count || 0),
    0
  ) || 0

  const columns = [
    {
      title: '부서코드',
      dataIndex: 'code',
      key: 'code',
      width: 120,
    },
    {
      title: '부서명',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Department) => (
        <a onClick={() => navigate(`/departments/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '연락처',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
    },
    {
      title: '소관 자치법규',
      dataIndex: 'ordinance_count',
      key: 'ordinance_count',
      width: 120,
      align: 'center' as const,
      render: (count: number) => count || 0,
    },
    {
      title: '작업',
      key: 'action',
      width: 120,
      render: (_: any, record: Department) => (
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

  return (
    <div>
      <Title level={4}>부서별관리</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="전체 부서"
              value={data?.total || 0}
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
          placeholder="부서명 검색"
          onSearch={setSearch}
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

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          total: data?.total || 0,
          pageSize: 20,
          onChange: setPage,
          showTotal: (total) => `총 ${total}건`,
        }}
      />

      <Modal
        title={editingDepartment ? '부서 수정' : '부서 추가'}
        open={isModalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
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
          <Form.Item name="parent_code" label="상위부서코드">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="연락처">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
