import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Empty,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { draftingApi, DraftingProject } from '../../services/draftingApi'
import NewDraftingModal from './NewDraftingModal'

const { Title, Paragraph } = Typography

const KIND_LABEL: Record<string, { text: string; color: string }> = {
  enact: { text: '제정', color: 'green' },
  amend_partial: { text: '일부개정', color: 'blue' },
  amend_full: { text: '전부개정', color: 'purple' },
}

export default function DraftingList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)

  const { data: projects, isLoading } = useQuery({
    queryKey: ['drafting', 'projects'],
    queryFn: draftingApi.listProjects,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => draftingApi.deleteProject(id),
    onSuccess: () => {
      message.success('삭제되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['drafting', 'projects'] })
    },
    onError: () => message.error('삭제에 실패했습니다.'),
  })

  const columns: ColumnsType<DraftingProject> = [
    {
      title: '제명',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record) => (
        <a onClick={() => navigate(`/drafting/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '종류',
      dataIndex: 'kind',
      key: 'kind',
      width: 110,
      render: (kind: string) => {
        const k = KIND_LABEL[kind] ?? { text: kind, color: 'default' }
        return <Tag color={k.color}>{k.text}</Tag>
      },
    },
    { title: '지자체', dataIndex: 'municipality', key: 'municipality', width: 180 },
    {
      title: '진행률',
      dataIndex: 'progress',
      key: 'progress',
      width: 90,
      render: (p: number) => `${p}%`,
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s: string) => (
        <Tag color={s === 'locked' ? 'gold' : 'cyan'}>{s === 'locked' ? '잠금' : '작성중'}</Tag>
      ),
    },
    {
      title: '수정일',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (d: string) => dayjs(d).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/drafting/${record.id}`)}
          >
            열기
          </Button>
          <Popconfirm
            title="이 입안 프로젝트를 삭제할까요?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            입안심사
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 16 }}>
            등록된 조례와 상위법령을 활용해 조례 제정·개정안을 작성하고 입안심사 기준으로 검증합니다.
          </Paragraph>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          새 입안심사
        </Button>
      </div>

      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={projects ?? []}
          locale={{ emptyText: <Empty description="입안 프로젝트가 없습니다. '새 입안심사'로 시작하세요." /> }}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <NewDraftingModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(project) => {
          setModalOpen(false)
          queryClient.invalidateQueries({ queryKey: ['drafting', 'projects'] })
          navigate(`/drafting/${project.id}`)
        }}
      />
    </div>
  )
}
