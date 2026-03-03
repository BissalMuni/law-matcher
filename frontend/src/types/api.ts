export interface RevisionNeededItem {
  ordinance_id: number
  ordinance_name: string
  ordinance_revision_date: string | null
  law_id: number
  law_name: string
  law_type: string
  law_proclaimed_date: string | null
  days_diff: number
  revision_status: 'NEEDS_REVISION' | 'UNDER_REVIEW' | 'COMPLETED'
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

export type DetectionMethodType =
  | 'proclaimed_date'
  | 'article_change'
  | 'revision_reason'

export interface RevisionReasonResponse {
  law_id: number
  law_mst: string
  revision_reason: string | null
  amendment_content: string | null
  extracted_articles: string[]
  fetched_at: string
}

export interface DetectionResult {
  method: DetectionMethodType
  needs_revision: boolean
  detail: Record<string, unknown>
  detected_at: string
}

export interface DetectionResultsResponse {
  ordinance_id: number
  ordinance_name: string
  results: DetectionResult[]
  notification?: {
    message: string
    changed_methods: string[]
    created_at: string
  } | null
}

export interface DetectionSummaryItem {
  method: DetectionMethodType
  needs_revision: boolean
  label: string
}
