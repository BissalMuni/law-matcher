import { Button, message, Popconfirm, Space, Tooltip } from 'antd'
import { DeleteOutlined, ExperimentOutlined, LoadingOutlined } from '@ant-design/icons'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { aiApi } from '../../services/api'

interface AiAnalysisButtonProps {
  ordinanceId: number
  lawId: number
  /** 이미 성공한 분석이 존재하는지 여부 */
  hasExistingResult: boolean
  /** 분석 실패 건이 존재하는지 (재시도 1회 허용) */
  hasFailedResult: boolean
  onSuccess?: () => void
}

/**
 * "AI 분석" 버튼 — 1회 클릭으로 통합 분석 실행
 * FR-011: 담당자 명시적 요청으로만 수행
 * FR-012: 완료 시 비활성화 (삭제 후 재분석 가능)
 */
export default function AiAnalysisButton({
  ordinanceId,
  lawId,
  hasExistingResult,
  hasFailedResult,
  onSuccess,
}: AiAnalysisButtonProps) {
  const queryClient = useQueryClient()

  const analyzeMutation = useMutation({
    mutationFn: () => aiApi.analyze(ordinanceId, lawId, false),
    onSuccess: (data: any) => {
      if (data?.status === 'failed') {
        message.error(data?.error_message || 'AI 분석에 실패했습니다. 직접 검토해 주세요')
      } else {
        message.success('AI 분석이 완료되었습니다')
      }
      queryClient.invalidateQueries({ queryKey: ['ai-results', String(ordinanceId)] })
      onSuccess?.()
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      const errorMsg = typeof detail === 'object' ? detail.detail : detail
      message.error(errorMsg || 'AI 분석을 수행할 수 없습니다. 직접 검토해 주세요')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => aiApi.deleteResults(ordinanceId, lawId),
    onSuccess: () => {
      message.success('기존 분석 결과가 삭제되었습니다')
      queryClient.invalidateQueries({ queryKey: ['ai-results', String(ordinanceId)] })
    },
    onError: () => {
      message.error('분석 결과 삭제에 실패했습니다')
    },
  })

  const isPending = analyzeMutation.isPending || deleteMutation.isPending

  if (hasExistingResult) {
    return (
      <Space size="small">
        <Tooltip title="AI 분석이 이미 완료되었습니다">
          <Button
            icon={<ExperimentOutlined />}
            disabled
          >
            AI 분석 완료
          </Button>
        </Tooltip>
        <Popconfirm
          title="AI 분석 삭제"
          description="기존 분석 결과를 삭제합니다. 재분석하려면 삭제 후 AI 분석 버튼을 다시 클릭하세요."
          onConfirm={() => deleteMutation.mutate()}
          okText="삭제"
          cancelText="취소"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="기존 분석 결과 삭제">
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={deleteMutation.isPending}
              disabled={isPending}
              size="small"
            />
          </Tooltip>
        </Popconfirm>
      </Space>
    )
  }

  return (
    <Tooltip title={hasFailedResult ? '이전 분석 실패 — 재시도 가능' : 'AI가 개정내용 요약과 검토의견 초안을 생성합니다'}>
      <Button
        type="primary"
        icon={isPending ? <LoadingOutlined /> : <ExperimentOutlined />}
        onClick={() => analyzeMutation.mutate()}
        loading={analyzeMutation.isPending}
        disabled={isPending}
      >
        {analyzeMutation.isPending ? 'AI 분석 중...' : 'AI 분석'}
      </Button>
    </Tooltip>
  )
}
