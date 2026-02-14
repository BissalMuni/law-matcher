import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Table,
  Input,
  Select,
  Space,
  Typography,
  Button,
  Tag,
  DatePicker,
  message,
  Modal,
} from 'antd'
import {
  SearchOutlined,
  SyncOutlined,
  FileSearchOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { articleApi, lawsApi } from '../services/api'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Title } = Typography
const { Option } = Select

interface ArticleItem {
  id: number
  law_id: number
  law_name: string
  law_type: string
  article_no: string
  article_title: string
  article_content: string
  ordinance_count: number
  change_count: number
  last_changed_date?: string
  has_recent_change: boolean
  last_synced_at?: string
}

interface ArticleListResponse {
  items: ArticleItem[]
  total: number
  page: number
  size: number
  pages: number
}

export default function ArticleList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  // State
  const [page, setPage] = useState(() => {
    const p = searchParams.get('page')
    return p ? parseInt(p, 10) : 1
  })
  const [search, setSearch] = useState(() => searchParams.get('search') || '')
  const [lawId, setLawId] = useState<number | undefined>(() => {
    const id = searchParams.get('lawId')
    return id ? parseInt(id, 10) : undefined
  })
  const [hasOrdinance, setHasOrdinance] = useState<boolean | undefined>(undefined)
  const [changedSince, setChangedSince] = useState<string | undefined>(undefined)

  // Update URL when filters change
  useEffect(() => {
    const params: Record<string, string> = {}
    if (page > 1) params.page = page.toString()
    if (search) params.search = search
    if (lawId) params.lawId = lawId.toString()
    setSearchParams(params)
  }, [page, search, lawId, setSearchParams])

  // 법령 목록 조회 (법령 선택 드롭다운용)
  const { data: lawsData } = useQuery({
    queryKey: ['laws-list'],
    queryFn: () => lawsApi.getAll(),
  })

  // 조문 목록 조회
  const { data, isLoading, refetch } = useQuery<ArticleListResponse>({
    queryKey: ['articles', page, search, lawId, hasOrdinance, changedSince],
    queryFn: () =>
      articleApi.getList({
        page,
        size: 20,
        law_id: lawId,
        search: search || undefined,
        has_ordinance: hasOrdinance,
        changed_since: changedSince,
      }),
  })

  // 동기화 Mutation
  const syncMutation = useMutation({
    mutationFn: (lawIds?: number[]) => articleApi.sync({ law_ids: lawIds }),
    onSuccess: (response) => {
      message.success(response.message || '조문 동기화가 완료되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['articles'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail?.message || '동기화 중 오류가 발생했습니다.')
    },
  })

  // 전체 동기화
  const handleSyncAll = () => {
    Modal.confirm({
      title: '전체 조문 동기화',
      content: '모든 법령의 조문을 동기화하시겠습니까? 시간이 오래 걸릴 수 있습니다.',
      okText: '동기화',
      cancelText: '취소',
      onOk: () => {
        syncMutation.mutate()
      },
    })
  }

  // 선택된 법령 동기화
  const handleSyncSelected = () => {
    if (!lawId) {
      message.warning('동기화할 법령을 선택해주세요.')
      return
    }

    Modal.confirm({
      title: '조문 동기화',
      content: '선택된 법령의 조문을 동기화하시겠습니까?',
      okText: '동기화',
      cancelText: '취소',
      onOk: () => {
        syncMutation.mutate([lawId])
      },
    })
  }

  // 검색 핸들러
  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  // 필터 초기화
  const handleReset = () => {
    setSearch('')
    setLawId(undefined)
    setHasOrdinance(undefined)
    setChangedSince(undefined)
    setPage(1)
  }

  // 테이블 컬럼 정의
  const columns: ColumnsType<ArticleItem> = [
    {
      title: '법령명',
      dataIndex: 'law_name',
      key: 'law_name',
      width: 250,
      render: (text, record) => (
        <div>
          <div>{text}</div>
          <Tag color="blue" style={{ fontSize: 11 }}>
            {record.law_type}
          </Tag>
        </div>
      ),
    },
    {
      title: '조문번호',
      dataIndex: 'article_no',
      key: 'article_no',
      width: 100,
    },
    {
      title: '조문제목',
      dataIndex: 'article_title',
      key: 'article_title',
      width: 200,
    },
    {
      title: '연계 조례',
      dataIndex: 'ordinance_count',
      key: 'ordinance_count',
      width: 100,
      align: 'center',
      render: (count: number) => (
        <Tag color={count > 0 ? 'green' : 'default'}>{count}건</Tag>
      ),
    },
    {
      title: '변경 이력',
      dataIndex: 'change_count',
      key: 'change_count',
      width: 100,
      align: 'center',
      render: (count: number) => <span>{count}건</span>,
    },
    {
      title: '최근 변경',
      dataIndex: 'last_changed_date',
      key: 'last_changed_date',
      width: 120,
      render: (date: string | undefined, record) => {
        if (!date) return '-'
        return (
          <div>
            <div>{date}</div>
            {record.has_recent_change && (
              <Tag color="red" style={{ fontSize: 11 }}>
                최근 변경
              </Tag>
            )}
          </div>
        )
      },
    },
  ]

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={3}>
            <FileSearchOutlined /> 조문 조회
          </Title>
          <Space>
            <Button
              type="primary"
              icon={<SyncOutlined spin={syncMutation.isPending} />}
              onClick={handleSyncSelected}
              loading={syncMutation.isPending}
              disabled={!lawId}
            >
              선택 법령 동기화
            </Button>
            <Button
              icon={<SyncOutlined spin={syncMutation.isPending} />}
              onClick={handleSyncAll}
              loading={syncMutation.isPending}
            >
              전체 동기화
            </Button>
          </Space>
        </div>

        {/* Filters */}
        <Space wrap>
          <Select
            placeholder="법령 선택"
            value={lawId}
            onChange={(value) => {
              setLawId(value)
              setPage(1)
            }}
            style={{ width: 300 }}
            allowClear
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            options={lawsData?.map((law: any) => ({
              value: law.id,
              label: `${law.law_name} (${law.law_type})`,
            }))}
          />

          <Input
            placeholder="조문번호 또는 제목 검색"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={(e) => handleSearch((e.target as HTMLInputElement).value)}
            style={{ width: 250 }}
            prefix={<SearchOutlined />}
            allowClear
          />

          <Select
            placeholder="연계 조례"
            value={hasOrdinance}
            onChange={(value) => {
              setHasOrdinance(value)
              setPage(1)
            }}
            style={{ width: 150 }}
            allowClear
          >
            <Option value={true}>연계 있음</Option>
            <Option value={false}>연계 없음</Option>
          </Select>

          <DatePicker
            placeholder="변경일 이후"
            value={changedSince ? dayjs(changedSince) : null}
            onChange={(date) => {
              setChangedSince(date ? date.format('YYYY-MM-DD') : undefined)
              setPage(1)
            }}
            style={{ width: 150 }}
          />

          <Button onClick={handleReset}>초기화</Button>
        </Space>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: 20,
            total: data?.total || 0,
            onChange: (newPage) => setPage(newPage),
            showSizeChanger: false,
            showTotal: (total) => `전체 ${total}건`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/articles/${record.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Space>
    </div>
  )
}
