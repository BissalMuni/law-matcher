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

export interface RevisionTypeCount {
  revision_type: string
  count: number
}

export interface OrdinanceRevisionTree {
  total_count: number
  no_revision_count: number
  needs_revision_count: number
  by_revision_type: RevisionTypeCount[]
}

export interface LatestSyncStats {
  sync_date: string | null
  total_laws: number
  by_revision_type: RevisionTypeCount[]
}

export interface DepartmentInputStats {
  id: number
  name: string
  total_ordinances: number
  ordinances_with_laws: number
  ordinances_without_laws: number
  progress_rate: number
}

export interface DepartmentInputStatsResponse {
  total_ordinances: number
  total_with_laws: number
  total_without_laws: number
  overall_progress_rate: number
  departments: DepartmentInputStats[]
}

export interface LawChangeStatsResponse {
  total: number
  by_api_status: Record<string, number>
  by_dept: Array<{ dept_name: string; total: number }>
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

// === Batch Processing ===

export interface BatchJob {
  id: number
  name: string
  current_step: string
  step1_status: string
  step2_status: string
  step3_status: string
  step4_status: string
  step5_status: string
  step2_progress: number
  step2_total: number
  step3_progress: number
  step3_total: number
  step4_progress: number
  step4_total: number
  filter_params: Record<string, any> | null
  summary: Record<string, any> | null
  created_at: string
}

export interface BatchJobItem {
  id: number
  batch_job_id: number
  ordinance_id: number
  ordinance_name: string
  ordinance_department: string | null
  ordinance_category: string | null
  step1_result: string
  step1_reason: string | null
  step2_result: string | null
  step2_reason: string | null
  step2_detail: Record<string, any> | null
  step3_result: string | null
  step3_reason: string | null
  step4_result: string | null
  step4_reason: string | null
  step4_ai_summary: string | null
  step4_ai_result: string | null
  final_result: string | null
  manually_excluded: boolean
}

export interface BatchStepCounts {
  total: number
  step1: Record<string, number>
  step2: Record<string, number>
  step3: Record<string, number>
  step4: Record<string, number>
  final: Record<string, number>
}

export interface BatchStepProgress {
  progress: number
  total: number
  ordinance_name: string
  result: string
  done?: boolean
  error?: string
}
