import { useEffect, useRef, useState } from 'react'
import { Modal, Form, Input, Select, Button, Alert, Space } from 'antd'
import AiLabel from './AiLabel'
import type { LlmAnalysisResult } from '../../types/api'

const { TextArea } = Input

interface AiDraftModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: {
    review_content: string
    review_result: string
    is_ai_generated: boolean
    ai_modified: boolean
    ai_analysis_id: number | null
  }) => void
  /** AI 분석 결과 (초안 자동 채움용) */
  aiResult: LlmAnalysisResult | null
  loading?: boolean
}

/**
 * 검토의견 작성 모달 — AI 초안 자동 채움
 * AI 생성 여부/수정 여부를 메타데이터로 기록
 */
export default function AiDraftModal({
  open,
  onClose,
  onSubmit,
  aiResult,
  loading,
}: AiDraftModalProps) {
  const [form] = Form.useForm()
  const originalDraftRef = useRef<string>('')
  const originalResultRef = useRef<string>('')
  const [isAiBased, setIsAiBased] = useState(false)

  // AI 초안 자동 채움
  useEffect(() => {
    if (open && aiResult?.status === 'success') {
      const draft = aiResult.review_draft_text || ''
      const result = aiResult.review_draft_result || ''
      form.setFieldsValue({
        review_content: draft,
        review_result: result,
      })
      originalDraftRef.current = draft
      originalResultRef.current = result
      setIsAiBased(true)
    } else if (open) {
      form.resetFields()
      originalDraftRef.current = ''
      originalResultRef.current = ''
      setIsAiBased(false)
    }
  }, [open, aiResult, form])

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const contentModified = values.review_content !== originalDraftRef.current
    const resultModified = values.review_result !== originalResultRef.current
    const wasModified = contentModified || resultModified

    onSubmit({
      review_content: values.review_content,
      review_result: values.review_result,
      is_ai_generated: isAiBased,
      ai_modified: isAiBased ? wasModified : false,
      ai_analysis_id: isAiBased ? aiResult?.id ?? null : null,
    })
  }

  return (
    <Modal
      title="검토의견 작성"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          취소
        </Button>,
        <Button key="submit" type="primary" onClick={handleSubmit} loading={loading}>
          제출
        </Button>,
      ]}
      width={640}
    >
      {isAiBased && (
        <Alert
          message={
            <Space>
              <AiLabel />
              <span>AI가 생성한 초안입니다. 내용을 검토한 후 수정/보완하여 제출해 주세요.</span>
            </Space>
          }
          type="info"
          showIcon={false}
          style={{ marginBottom: 16 }}
        />
      )}
      <Form form={form} layout="vertical">
        <Form.Item
          name="review_result"
          label="검토 결과"
          rules={[{ required: true, message: '검토 결과를 선택하세요' }]}
        >
          <Select placeholder="선택">
            <Select.Option value="개정필요">개정필요</Select.Option>
            <Select.Option value="개정불필요">개정불필요</Select.Option>
            <Select.Option value="검토중">검토중</Select.Option>
            <Select.Option value="보류">보류</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item
          name="review_content"
          label="검토의견"
          rules={[{ required: true, message: '검토의견을 입력하세요' }]}
        >
          <TextArea rows={12} placeholder="검토의견을 입력하세요" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
