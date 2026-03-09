export type OrdinanceStatusType = 'ACTIVE' | 'ABOLISHED' | 'EXCLUDED'

export interface RevisionNeededItem {
  ordinance_id: number
  ordinance_name: string
  ordinance_revision_date: string | null
  law_id: number
  law_name: string
  law_type: string
  law_proclaimed_date: string | null
  days_diff: number
  revision_status: '검토대기' | '검토중' | '개정확정' | null
  department: string | null
}

export interface RevisionNeededListResponse {
  total: number
  needs_revision_count: number
  completed_count: number
  items: RevisionNeededItem[]
}

export interface DashboardSummary {
  total_ordinances: number
  total_parent_laws: number
  recent_amendments: number
  pending_reviews: number
  need_revision_count: number
  revision_needs_action_count: number
  revision_completed_count: number
}

// === 006-llm-review-assistant ===

export interface AffectedOrdinanceArticle {
  article_no: string
  article_title: string | null
  current_content_summary: string | null
  issue: string | null
  recommendation: string | null
}

export interface LlmAnalysisResult {
  id: number
  ordinance_id: number
  law_id: number
  law_name?: string
  law_proclaimed_date: string | null
  status: 'pending' | 'success' | 'failed'
  summary_text: string | null
  review_draft_text: string | null
  review_draft_result: string | null  // '개정필요' | '개정불필요'
  affected_articles_json: AffectedOrdinanceArticle[] | null
  provider_name: string
  model_name: string
  token_usage: { input_tokens: number; output_tokens: number } | null
  error_message: string | null
  created_at: string
}

export interface AiAnalyzeResponse extends LlmAnalysisResult {}

export interface AiResultsResponse {
  ordinance_id: number
  results: LlmAnalysisResult[]
}

export interface AvailableModel {
  id: string
  name: string
}

export interface LlmProvider {
  id: number
  provider_name: string
  display_name: string
  model_name: string
  api_key_env_name: string
  api_key_configured: boolean
  api_key_source: 'env' | 'db' | 'none'
  is_active: boolean
  rate_limit_per_minute: number
  available_models: AvailableModel[]
  updated_at: string | null
}

export interface LlmProviderListResponse {
  providers: LlmProvider[]
}

// === 005-revision-detection-tabs ===

export type DetectionMethodType = 'proclaimed_date' | 'revision_reason'

export interface RevisionReasonResponse {
  id: number
  law_id: number
  law_mst: string | null
  revision_reason: string | null
  amendment_content: string | null
  extracted_articles: string[]
  fetched_at: string
}

export interface DetectionResult {
  method: DetectionMethodType
  needs_revision: boolean
  detail: Record<string, any>
  detected_at: string
}

export interface DetectionResultsResponse {
  ordinance_id: number
  results: DetectionResult[]
}

export interface DetectionSummaryItem {
  law_id: number
  law_name: string
  method_a: DetectionResult | null
  method_c: DetectionResult | null
}

export interface AiAnalyticsData {
  period: { start: string; end: string }
  total_analyses: number
  success_count: number
  failed_count: number
  draft_adoption_rate: number
  draft_modified_rate: number
  draft_unused_rate: number
  average_token_usage: { input_tokens: number; output_tokens: number } | null
  by_provider: Record<string, { count: number; model: string }>
}
