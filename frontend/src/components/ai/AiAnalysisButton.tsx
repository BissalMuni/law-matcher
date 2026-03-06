import { useState } from 'react'
import { Button, message, Tooltip } from 'antd'
import { ExperimentOutlined, LoadingOutlined } from '@ant-design/icons'
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
 * FR-012: 완료 시 비활성화
 */
export default function AiAnalysisButton({
  ordinanceId,
  lawId,
  hasExistingResult,
  hasFailedResult,
  onSuccess,
}: AiAnalysisButtonProps) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => aiApi.analyze(ordinanceId, lawId),
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

  // 이미 성공한 결과가 있으면 비활성화
  const isDisabled = hasExistingResult

  const getTooltip = () => {
    if (hasExistingResult) return 'AI 분석이 이미 완료되었습니다'
    if (hasFailedResult) return '이전 분석 실패 — 재시도 가능 (1회)'
    return 'AI가 개정내용 요약과 검토의견 초안을 생성합니다'
  }

  return (
    <Tooltip title={getTooltip()}>
      <Button
        type={hasExistingResult ? 'default' : 'primary'}
        icon={mutation.isPending ? <LoadingOutlined /> : <ExperimentOutlined />}
        onClick={() => mutation.mutate()}
        loading={mutation.isPending}
        disabled={isDisabled || mutation.isPending}
      >
        {mutation.isPending ? 'AI 분석 중...' : hasExistingResult ? 'AI 분석 완료' : 'AI 분석'}
      </Button>
    </Tooltip>
  )
}
