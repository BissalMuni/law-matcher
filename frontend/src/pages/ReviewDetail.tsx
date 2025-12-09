import { useParams, useNavigate } from 'react-router-dom'
import {
  Descriptions,
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Table,
  Form,
  Input,
  Select,
  Spin,
  message,
} from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reviewApi } from '../services/api'
import dayjs from 'dayjs'

const { Title } = Typography
const { TextArea } = Input

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [form] = Form.useForm()

  const { data: review, isLoading } = useQuery({
    queryKey: ['review', id],
    queryFn: () => reviewApi.getById(Number(id)),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (values: any) => reviewApi.update(Number(id), values),
    onSuccess: () => {
      message.success('저장되었습니다')
      queryClient.invalidateQueries({ queryKey: ['review', id] })
    },
  })

  const urgencyColor: Record<string, string> = {
    HIGH: 'red',
    MEDIUM: 'orange',
    LOW: 'blue',
  }

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

      <Title level={4}>개정 검토 상세</Title>

      <Card title="검토 정보" style={{ marginBottom: 16 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="자치법규">
            {review?.ordinance_name || `조례 #${review?.ordinance_id}`}
          </Descriptions.Item>
          <Descriptions.Item label="상위법령">
            {review?.law_name || `법령 #${review?.amendment_id}`}
          </Descriptions.Item>
          <Descriptions.Item label="개정 필요">
            <Tag color={review?.need_revision ? 'red' : 'green'}>
              {review?.need_revision ? '필요' : '불필요'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="긴급도">
            {review?.revision_urgency ? (
              <Tag color={urgencyColor[review.revision_urgency]}>
                {review.revision_urgency}
              </Tag>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="생성일">
            {dayjs(review?.created_at).format('YYYY-MM-DD HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="검토자">{review?.reviewed_by || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {review?.affected_articles && review.affected_articles.length > 0 && (
        <Card title="영향받는 조문" style={{ marginBottom: 16 }}>
          <Table
            dataSource={review.affected_articles}
            rowKey="article_no"
            size="small"
            pagination={false}
            columns={[
              { title: '조문', dataIndex: 'article_no', key: 'article_no', width: 100 },
              { title: '영향유형', dataIndex: 'impact_type', key: 'impact_type', width: 150 },
            ]}
          />
        </Card>
      )}

      <Card title="검토 내용">
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            status: review?.status,
            reviewed_by: review?.reviewed_by,
            reason: review?.reason,
            recommendation: review?.recommendation,
          }}
          onFinish={updateMutation.mutate}
        >
          <Form.Item name="status" label="상태">
            <Select
              options={[
                { value: 'PENDING', label: 'PENDING' },
                { value: 'REVIEWED', label: 'REVIEWED' },
                { value: 'COMPLETED', label: 'COMPLETED' },
              ]}
            />
          </Form.Item>
          <Form.Item name="reviewed_by" label="검토자">
            <Input />
          </Form.Item>
          <Form.Item name="reason" label="개정 필요 사유">
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item name="recommendation" label="권고 사항">
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={updateMutation.isPending}
            >
              저장
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
