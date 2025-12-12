import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Descriptions,
  Table,
  Card,
  Button,
  Space,
  Typography,
  Spin,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Popconfirm,
} from 'antd'
import { ArrowLeftOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordinanceApi } from '../services/api'
import dayjs from 'dayjs'

const { Title } = Typography

interface ParentLaw {
  id: number
  law_id: string
  law_type: string
  law_name: string
  proclaimed_date?: string
  enforced_date?: string
  related_articles?: string
}

export default function OrdinanceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingParentLaw, setEditingParentLaw] = useState<ParentLaw | null>(null)
  const [form] = Form.useForm()

  const { data: ordinance, isLoading } = useQuery({
    queryKey: ['ordinance', id],
    queryFn: () => ordinanceApi.getById(Number(id)),
    enabled: !!id,
  })

  const { data: articles } = useQuery({
    queryKey: ['ordinance', id, 'articles'],
    queryFn: () => ordinanceApi.getArticles(Number(id)),
    enabled: !!id,
  })

  const { data: parentLaws } = useQuery({
    queryKey: ['ordinance', id, 'parent-laws'],
    queryFn: () => ordinanceApi.getParentLaws(Number(id)),
    enabled: !!id,
  })

  const createMutation = useMutation({
    mutationFn: (data: {
      law_id: string
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

  const handleModalClose = () => {
    setIsModalOpen(false)
    setEditingParentLaw(null)
    form.resetFields()
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

  const handleSubmit = (values: any) => {
    const data = {
      ...values,
      proclaimed_date: values.proclaimed_date?.format('YYYY-MM-DD'),
      enforced_date: values.enforced_date?.format('YYYY-MM-DD'),
    }
    if (editingParentLaw) {
      updateMutation.mutate({ parentLawId: editingParentLaw.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const parentLawColumns = [
    { title: '법령명', dataIndex: 'law_name', key: 'law_name' },
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

      <Card title="기본 정보" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="자치법규 코드">{ordinance?.code}</Descriptions.Item>
          <Descriptions.Item label="분류">{ordinance?.category}</Descriptions.Item>
          <Descriptions.Item label="소관부서">{ordinance?.department}</Descriptions.Item>
          <Descriptions.Item label="상태">{ordinance?.status}</Descriptions.Item>
          <Descriptions.Item label="제정일">{ordinance?.enacted_date}</Descriptions.Item>
          <Descriptions.Item label="시행일">{ordinance?.enforced_date}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title="상위법령"
        style={{ marginBottom: 16 }}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            추가
          </Button>
        }
      >
        <Table
          dataSource={parentLaws || []}
          rowKey="id"
          size="small"
          pagination={false}
          columns={parentLawColumns}
        />
      </Card>

      <Card title="조문">
        <Table
          dataSource={articles || []}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '조', dataIndex: 'article_no', key: 'article_no', width: 80 },
            { title: '항', dataIndex: 'paragraph_no', key: 'paragraph_no', width: 60 },
            { title: '내용', dataIndex: 'content', key: 'content' },
          ]}
        />
      </Card>

      <Modal
        title={editingParentLaw ? '상위법령 수정' : '상위법령 추가'}
        open={isModalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="law_id"
            label="법령 ID"
          >
            <Input disabled placeholder="예: 001656" />
          </Form.Item>
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
          <Form.Item name="proclaimed_date" label="공포일자">
            <DatePicker disabled style={{ width: '100%' }} placeholder="공포일자 선택" />
          </Form.Item>
          <Form.Item name="enforced_date" label="시행일자">
            <DatePicker disabled style={{ width: '100%' }} placeholder="시행일자 선택" />
          </Form.Item>
          <Form.Item name="related_articles" label="관련 조문">
            <Input placeholder="예: 제1조, 제2조" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
