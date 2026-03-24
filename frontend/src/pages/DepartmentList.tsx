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
  Select,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  DownloadOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { Upload } from 'antd'
import type { UploadProps } from 'antd'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { departmentApi } from '../services/api'

const { Title } = Typography
const { Search } = Input

interface DepartmentTreeNode {
  id: number
  code: string
  name: string
  parent_name?: string
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

  // 불일치 부서명 조회
  interface MismatchItem {
    department: string
    count: number
  }

  const { data: mismatches, refetch: refetchMismatches } = useQuery<MismatchItem[]>({
    queryKey: ['departments-mismatches'],
    queryFn: () => departmentApi.getMismatches(),
  })

  const [fixTarget, setFixTarget] = useState<string | null>(null)
  const [fixNewName, setFixNewName] = useState('')

  const fixMismatchMutation = useMutation({
    mutationFn: ({ oldName, newName }: { oldName: string; newName: string }) =>
      departmentApi.fixMismatch(oldName, newName),
    onSuccess: (data) => {
      message.success(data.message)
      setFixTarget(null)
      setFixNewName('')
      refetchMismatches()
      queryClient.invalidateQueries({ queryKey: ['departments-tree'] })
      queryClient.invalidateQueries({ queryKey: ['departments-summary'] })
    },
    onError: () => {
      message.error('수정에 실패했습니다.')
    },
  })

  // 부서 마스터의 전체 이름 목록 (매칭용 드롭다운)
  const allDeptFullNames: { label: string; value: string }[] = (() => {
    const names: { label: string; value: string }[] = []
    const bureaus = treeData?.bureaus || []
    for (const bureau of bureaus) {
      names.push({ label: bureau.name, value: bureau.name })
      for (const child of bureau.children || []) {
        const fullName = `${bureau.name} ${child.name}`
        names.push({ label: fullName, value: fullName })
      }
    }
    return names
  })()

  const uploadMutation = useMutation({
    mutationFn: departmentApi.upload,
    onSuccess: (data) => {
      message.success(data.message || '업로드가 완료되었습니다.')
      queryClient.invalidateQueries({ queryKey: ['departments-tree'] })
      queryClient.invalidateQueries({ queryKey: ['departments-summary'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '업로드에 실패했습니다.')
    },
  })

  const handleDownloadTemplate = async () => {
    try {
      await departmentApi.downloadTemplate()
      message.success('템플릿이 다운로드되었습니다.')
    } catch {
      message.error('템플릿 다운로드에 실패했습니다.')
    }
  }

  const uploadProps: UploadProps = {
    accept: '.xlsx,.xls',
    showUploadList: false,
    beforeUpload: (file) => {
      uploadMutation.mutate(file)
      return false
    },
  }

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

  // Flatten tree data for table display
  const flattenTree = (nodes: DepartmentTreeNode[]): DepartmentTreeNode[] => {
    const result: DepartmentTreeNode[] = []
    nodes.forEach(node => {
      result.push(node)
      if (node.children && node.children.length > 0) {
        result.push(...node.children)
      }
    })
    return result
  }

  // Get all departments as flat list
  const allDepartments = [
    ...flattenTree(treeData?.bureaus || []),
    ...flattenTree(treeData?.zones || []),
  ].sort((a, b) => a.sort_order - b.sort_order)

  // Filter based on search
  const filteredDepartments = search
    ? allDepartments.filter(d => d.name.toLowerCase().includes(search.toLowerCase()))
    : allDepartments

  // Get parent departments for dropdown: top-level departments + unique parent_name values
  const parentDepartments = (() => {
    const topLevel = allDepartments.filter(d => !d.parent_name)
    // parent_name으로만 존재하는 국 단위 (행정국, 기획경제국 등) 추가
    const parentNames = new Set(allDepartments.map(d => d.parent_name).filter(Boolean))
    const topLevelNames = new Set(topLevel.map(d => d.name))
    const extraParents = [...parentNames]
      .filter(name => !topLevelNames.has(name!))
      .map(name => ({ id: 0, code: '', name: name!, parent_name: undefined, sort_order: 0, ordinance_count: 0, children: [] }))
    return [...topLevel, ...extraParents].sort((a, b) => a.name.localeCompare(b.name, 'ko'))
  })()

  // Department columns
  const columns = [
    {
      title: '직제순',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '부서명',
      key: 'department_name',
      render: (_: any, record: DepartmentTreeNode) => (
        <span style={{ fontWeight: !record.parent_name ? 'bold' : 'normal', whiteSpace: 'pre' }}>
          {record.parent_name ? `${record.parent_name} - ${record.name}` : record.name}
        </span>
      ),
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


  return (
    <div>
      <Title level={4}>부서 관리</Title>

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
          placeholder="부서명 검색"
          onSearch={setSearch}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 300 }}
          allowClear
        />
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadTemplate}
          >
            템플릿 다운로드
          </Button>
          <Upload {...uploadProps}>
            <Button
              icon={<UploadOutlined />}
              loading={uploadMutation.isPending}
            >
              일괄 업로드
            </Button>
          </Upload>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsModalOpen(true)}
          >
            부서 추가
          </Button>
        </Space>
      </Space>

      <Table
        columns={columns}
        dataSource={filteredDepartments}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        rowClassName={(record) =>
          !record.parent_name ? 'group-header-row' : ''
        }
      />

      {/* 불일치 부서명 */}
      {mismatches && mismatches.length > 0 && (
        <Card
          title={
            <Space>
              <WarningOutlined style={{ color: '#faad14' }} />
              <span>부서명 불일치 ({mismatches.length}건)</span>
            </Space>
          }
          size="small"
          style={{ marginTop: 24, marginBottom: 24 }}
        >
          <Table
            dataSource={mismatches}
            rowKey="department"
            pagination={false}
            size="small"
            columns={[
              {
                title: '조례 테이블 부서명',
                dataIndex: 'department',
                key: 'department',
              },
              {
                title: '조례 수',
                dataIndex: 'count',
                key: 'count',
                width: 80,
                align: 'center' as const,
              },
              {
                title: '변경할 부서명',
                key: 'fix',
                width: 300,
                render: (_: any, record: MismatchItem) =>
                  fixTarget === record.department ? (
                    <Select
                      showSearch
                      style={{ width: '100%' }}
                      placeholder="부서 선택"
                      value={fixNewName || undefined}
                      onChange={(val) => setFixNewName(val)}
                      options={allDeptFullNames}
                      filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                      }
                    />
                  ) : null,
              },
              {
                title: '작업',
                key: 'action',
                width: 150,
                render: (_: any, record: MismatchItem) =>
                  fixTarget === record.department ? (
                    <Space>
                      <Button
                        type="primary"
                        size="small"
                        disabled={!fixNewName}
                        loading={fixMismatchMutation.isPending}
                        onClick={() =>
                          fixMismatchMutation.mutate({
                            oldName: record.department,
                            newName: fixNewName,
                          })
                        }
                      >
                        적용
                      </Button>
                      <Button
                        size="small"
                        onClick={() => { setFixTarget(null); setFixNewName('') }}
                      >
                        취소
                      </Button>
                    </Space>
                  ) : (
                    <Button
                      size="small"
                      onClick={() => { setFixTarget(record.department); setFixNewName('') }}
                    >
                      수정
                    </Button>
                  ),
              },
            ]}
          />
        </Card>
      )}

      <Modal
        title={editingDepartment ? '부서 수정' : '부서 추가'}
        open={isModalOpen}
        onCancel={handleModalClose}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="sort_order"
            label="직제순"
            rules={[{ required: true, message: '직제순을 입력하세요' }]}
          >
            <Input type="number" placeholder="1, 2, 3..." />
          </Form.Item>
          <Form.Item
            name="name"
            label="부서명"
            rules={[{ required: true, message: '부서명을 입력하세요' }]}
          >
            <Input placeholder="부서명 입력" />
          </Form.Item>
          <Form.Item name="parent_name" label="상위부서명">
            <Select placeholder="상위부서 선택" allowClear showSearch>
              {parentDepartments.map((d) => (
                <Select.Option key={d.name} value={d.name}>
                  {d.name}
                </Select.Option>
              ))}
            </Select>
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
