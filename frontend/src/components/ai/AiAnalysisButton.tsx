import { Button, message, Popconfirm, Tooltip } from 'antd'
import { ExperimentOutlined, LoadingOutlined, ReloadOutlined } from '@ant-design/icons'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { aiApi } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'

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
 * FR-012: 완료 시 비활성화 (관리자는 재분석 가능)
 */
export default function AiAnalysisButton({
  ordinanceId,
  lawId,
  hasExistingResult,
  hasFailedResult,
  onSuccess,
}: AiAnalysisButtonProps) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.user_type === 'ADMIN'

  const mutation = useMutation({
    mutationFn: (force: boolean = false) => aiApi.analyze(ordinanceId, lawId, force),
    onSuccess: () => {
      message.success('AI 분석이 완료되었습니다')
      queryClient.invalidateQueries({ queryKey: ['ai-results', ordinanceId] })
      onSuccess?.()
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail
      const errorMsg = typeof detail === 'object' ? detail.detail : detail
      message.error(errorMsg || 'AI 분석을 수행할 수 없습니다. 직접 검토해 주세요')
    },
  })

  // 관리자는 항상 실행 가능, 일반 사용자는 성공 결과 있으면 비활성화
  const isDisabled = !isAdmin && hasExistingResult

  const getTooltip = () => {
    if (hasExistingResult && isAdmin) return 'AI 분석 완료 — 재분석 가능'
    if (hasExistingResult) return 'AI 분석이 이미 완료되었습니다'
    if (hasFailedResult) return '이전 분석 실패 — 재시도 가능'
    return 'AI가 개정내용 요약과 검토의견 초안을 생성합니다'
  }

  // 관리자가 이미 완료된 분석을 재실행할 때는 확인 팝업
  if (hasExistingResult && isAdmin) {
    return (
      <Popconfirm
        title="AI 재분석"
        description="기존 분석 결과를 삭제하고 다시 분석합니다."
        onConfirm={() => mutation.mutate(true)}
        okText="재분석"
        cancelText="취소"
      >
        <Tooltip title={getTooltip()}>
          <Button
            icon={mutation.isPending ? <LoadingOutlined /> : <ReloadOutlined />}
            loading={mutation.isPending}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'AI 분석 중...' : 'AI 재분석'}
          </Button>
        </Tooltip>
      </Popconfirm>
    )
  }

  return (
    <Tooltip title={getTooltip()}>
      <Button
        type={hasExistingResult ? 'default' : 'primary'}
        icon={mutation.isPending ? <LoadingOutlined /> : <ExperimentOutlined />}
        onClick={() => mutation.mutate(false)}
        loading={mutation.isPending}
        disabled={isDisabled || mutation.isPending}
      >
        {mutation.isPending ? 'AI 분석 중...' : hasExistingResult ? 'AI 분석 완료' : 'AI 분석'}
      </Button>
    </Tooltip>
  )
}
