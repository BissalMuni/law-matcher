import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Statistic, Table, Progress, Typography, Space, Alert, Spin, Radio, Button, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { departmentApi } from '../services/api'
import type { ColumnsType } from 'antd/es/table'

const { Title } = Typography

interface DepartmentStats {
  id: number
  name: string
  total_ordinances: number
  ordinances_with_laws: number
  ordinances_without_laws: number
  progress_rate: number
}

interface InputStatsResponse {
  total_ordinances: number
  total_with_laws: number
  total_without_laws: number
  overall_progress_rate: number
  departments: DepartmentStats[]
}

type FilterType = 'all' | 'with_laws' | 'without_laws'

export default function Statistics() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<FilterType>('all')

  const { data, isLoading, error } = useQuery<InputStatsResponse>({
    queryKey: ['departments', 'input-statistics'],
    queryFn: departmentApi.getInputStatistics,
  })

  // Filter departments based on selected filter
  const filteredDepartments = data?.departments?.filter((dept) => {
    if (filter === 'with_laws') {
      return dept.ordinances_without_laws === 0 && dept.total_ordinances > 0
    } else if (filter === 'without_laws') {
      return dept.ordinances_without_laws > 0
    }
    return true // 'all'
  }) || []

  const handleExportUninput = async () => {
    try {
      const response = await fetch('/api/v1/departments/export/uninput-ordinances')
      if (!response.ok) {
        throw new Error('다운로드 실패')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = '미입력_자치법규_목록.xlsx'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success('엑셀 파일이 다운로드되었습니다')
    } catch (error) {
      message.error('다운로드 중 오류가 발생했습니다')
    }
  }

  const columns: ColumnsType<DepartmentStats> = [
    {
      title: '부서명',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      fixed: 'left',
    },
    {
      title: '자치법규',
      dataIndex: 'total_ordinances',
      key: 'total_ordinances',
      align: 'center',
      width: 100,
    },
    {
      title: '상위법령',
      dataIndex: 'ordinances_with_laws',
      key: 'ordinances_with_laws',
      align: 'center',
      width: 100,
    },
    {
      title: '미입력',
      dataIndex: 'ordinances_without_laws',
      key: 'ordinances_without_laws',
      align: 'center',
      width: 100,
    },
    {
      title: '진행률',
      dataIndex: 'progress_rate',
      key: 'progress_rate',
      align: 'center',
      width: 300,
      render: (rate: number) => (
        <Space style={{ width: '100%' }}>
          <Progress
            percent={rate}
            size="small"
            style={{ width: 200 }}
            strokeColor={
              rate >= 80
                ? '#52c41a'
                : rate >= 50
                ? '#1890ff'
                : rate >= 30
                ? '#faad14'
                : '#f5222d'
            }
          />
          <span>{rate}%</span>
        </Space>
      ),
    },
  ]

  if (error) {
    return (
      <div>
        <Title level={4}>통계정보</Title>
        <Alert
          message="오류 발생"
          description={`데이터를 불러오는 중 오류가 발생했습니다: ${error}`}
          type="error"
          showIcon
          style={{ marginTop: 16 }}
        />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>데이터를 불러오는 중...</p>
      </div>
    )
  }

  return (
    <div>
      <Title level={4}>통계정보</Title>

      <Card
        style={{
          marginTop: 16,
          marginBottom: 24,
          background: '#f0f5ff',
          borderColor: '#adc6ff',
        }}
      >
        <Statistic
          title={
            <span style={{ fontSize: 16, fontWeight: 'bold' }}>
              전체 진행률
            </span>
          }
          value={`${data?.overall_progress_rate || 0}%`}
          suffix={`(${data?.total_with_laws || 0}/${data?.total_ordinances || 0})`}
          valueStyle={{ fontSize: 32, fontWeight: 'bold', color: '#1890ff' }}
        />
      </Card>

      <Card
        title="부서별 상위법령 입력 현황"
        size="small"
        extra={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExportUninput}
              size="small"
            >
              미입력 목록 다운로드
            </Button>
            <Radio.Group
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              buttonStyle="solid"
              size="small"
            >
              <Radio.Button value="all">전체</Radio.Button>
              <Radio.Button value="with_laws">입력완료</Radio.Button>
              <Radio.Button value="without_laws">미입력</Radio.Button>
            </Radio.Group>
          </Space>
        }
      >
        {!data?.departments || data.departments.length === 0 ? (
          <Alert
            message="데이터 없음"
            description="부서 데이터가 없습니다. 부서와 자치법규 데이터를 먼저 등록해주세요."
            type="info"
            showIcon
          />
        ) : filteredDepartments.length === 0 ? (
          <Alert
            message="검색 결과 없음"
            description={`선택한 필터(${filter === 'with_laws' ? '입력완료' : '미입력'})에 해당하는 부서가 없습니다.`}
            type="info"
            showIcon
          />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredDepartments}
            rowKey="id"
            loading={isLoading}
            pagination={false}
            scroll={{ x: 800 }}
            size="small"
            bordered
            onRow={(record) => ({
              onClick: () => {
                navigate(`/ordinances?department=${encodeURIComponent(record.name)}`)
              },
              style: { cursor: 'pointer' }
            })}
          />
        )}
      </Card>
    </div>
  )
}
