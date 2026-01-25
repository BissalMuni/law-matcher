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
