import axios from 'axios'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DetectionMethodType,
  DetectionResultsResponse,
  RevisionNeededListResponse,
  RevisionReasonResponse,
} from '../types/api'
import { LoginRequest, TokenResponse, User } from '../types/auth'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

const isDevBypass = import.meta.env.VITE_DEV_BYPASS_AUTH === 'true'

// JWT Token Interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('law_matcher_token')
    // simple_ 토큰은 개발용 가짜 세션이므로 Authorization 헤더를 붙이지 않는다.
    if (token && !token.startsWith('simple_')) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response Interceptor for handling 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('law_matcher_token')
      const isSimpleToken = !!token && token.startsWith('simple_')

      // 개발 우회 모드/가짜 세션에서는 401로 전체 세션을 강제로 날리지 않는다.
      if (!isDevBypass && !isSimpleToken) {
        localStorage.removeItem('law_matcher_token')
        localStorage.removeItem('law_matcher_user')

        // Only redirect if not already on login page
        if (!window.location.pathname.startsWith('/login') &&
            !window.location.pathname.startsWith('/landing')) {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post('/auth/login', data)
    return response.data
  },

  me: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    const { data } = await api.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data
  },
}

// Ordinance API
export const ordinanceApi = {
  getList: async (params: {
    page?: number
    size?: number
    category?: string
    department?: string
    search?: string
    no_parent_law_filter?: string  // "no_mapping" | "confirmed_none"
    needs_revision_filter?: string  // "needs_revision" | "no_revision"
    revision_type?: string  // 제개정구분 필터
    exclude_other_law_revision?: boolean  // 타법개정 제외
    review_result_filter?: string  // 검토결과 필터
    status?: string  // "ACTIVE" | "ABOLISHED"
  }) => {
    const { data } = await api.get('/ordinances', { params })
    return data
  },

  exportExcel: async (params?: {
    category?: string
    department?: string
    search?: string
    no_parent_law_filter?: string
    needs_revision_filter?: string
    revision_type?: string
    exclude_other_law_revision?: boolean
  }) => {
    const { data } = await api.get('/ordinances/export', {
      params,
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    const filename = `자치법규목록_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/ordinances/${id}`)
    return data
  },

  getParentLaws: async (id: number) => {
    const { data } = await api.get(`/ordinances/${id}/parent-laws`)
    return data
  },

  createParentLaw: async (ordinanceId: number, parentLaw: {
    law_id?: string
    law_type: string
    law_name: string
    proclaimed_date?: string
    enforced_date?: string
    related_articles?: string
  }) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/parent-laws`, parentLaw)
    return data
  },

  updateParentLaw: async (parentLawId: number, updateData: {
    law_type?: string
    law_name?: string
    proclaimed_date?: string
    enforced_date?: string
    related_articles?: string
  }) => {
    const { data } = await api.put(`/ordinances/parent-laws/${parentLawId}`, updateData)
    return data
  },

  deleteParentLaw: async (parentLawId: number) => {
    const { data } = await api.delete(`/ordinances/parent-laws/${parentLawId}`)
    return data
  },

  setNoParentLaw: async (ordinanceId: number) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/no-parent-law`)
    return data
  },

  unsetNoParentLaw: async (ordinanceId: number) => {
    const { data } = await api.delete(`/ordinances/${ordinanceId}/no-parent-law`)
    return data
  },

  // 검토이력 API
  getReviews: async (ordinanceId: number) => {
    const { data } = await api.get(`/ordinances/${ordinanceId}/reviews`)
    return data
  },

  createReview: async (ordinanceId: number, reviewData: {
    reviewer_type: string  // "DEPARTMENT" | "GENERAL"
    reviewer_name?: string
    reviewer_department?: string
    review_content: string
    review_result?: string  // 개정필요/개정불필요
  }) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/reviews`, reviewData)
    return data
  },

  updateReview: async (reviewId: number, updateData: {
    reviewer_name?: string
    reviewer_department?: string
    review_content?: string
    review_result?: string
  }) => {
    const { data } = await api.put(`/ordinances/reviews/${reviewId}`, updateData)
    return data
  },

  deleteReview: async (reviewId: number) => {
    const { data } = await api.delete(`/ordinances/reviews/${reviewId}`)
    return data
  },

  approveReview: async (reviewId: number, approvalData: {
    approval_status: string  // "approved" | "rejected"
    approval_note?: string
  }) => {
    const { data } = await api.post(`/ordinances/reviews/${reviewId}/approve`, approvalData)
    return data
  },

  getAllReviews: async (params: {
    page?: number
    size?: number
    approval_status?: string   // pending | approved | rejected
    review_result?: string     // 개정필요 | 개정불필요
    reviewer_type?: string     // DEPARTMENT | GENERAL
  }) => {
    const { data } = await api.get('/ordinances/reviews-all', { params })
    return data
  },

  syncFromMoleg: async (params?: { org?: string; sborg?: string; password?: string }) => {
    const headers = params?.password ? { 'X-Admin-Password': params.password } : {}
    const { data } = await api.post('/ordinances/sync', params || {}, { headers })
    return data
  },

  getDepartments: async () => {
    const { data } = await api.get('/ordinances/departments')
    return data
  },

  getRevisionTypes: async () => {
    const { data } = await api.get('/ordinances/revision-types')
    return data
  },

  // 근거 조문 매핑 관리
  getMappedArticles: async (ordinanceId: number) => {
    const { data } = await api.get(`/ordinances/${ordinanceId}/mapped-articles`)
    return data
  },

  getAvailableArticles: async (ordinanceId: number) => {
    const { data } = await api.get(`/ordinances/${ordinanceId}/available-articles`)
    return data
  },

  setMappedArticles: async (ordinanceId: number, articleIds: number[], mappingReason?: string) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/mapped-articles/bulk`, {
      article_ids: articleIds,
      mapping_reason: mappingReason || '근거 조문',
    })
    return data
  },

  // 검토 시작: revision_status "검토대기"→"검토중"
  startReview: async (ordinanceId: number) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/start-review`)
    return data
  },

  // 개정확정 해제: revision_status "개정확정"→null (관리자 전용)
  clearRevisionStatus: async (ordinanceId: number) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/clear-revision`)
    return data
  },

  // 개정 판별 결과 조회
  getDetectionResults: async (ordinanceId: number) => {
    const { data } = await api.get(`/ordinances/${ordinanceId}/detection-results`)
    return data
  },

  // 개정 판별 실행 (3가지 방식)
  runDetection: async (ordinanceId: number, methods?: DetectionMethodType[]) => {
    const payload = methods && methods.length > 0 ? { methods } : {}
    const { data } = await api.post(`/ordinances/${ordinanceId}/detect`, payload)
    return data
  },
}

// Sync API
export const syncApi = {
  syncLaws: async (lawIds?: string[]) => {
    const { data } = await api.post('/sync/laws', { law_ids: lawIds })
    return data
  },

  getStatus: async (taskId?: string) => {
    const { data } = await api.get('/sync/status', {
      params: taskId ? { task_id: taskId } : {},
    })
    return data
  },
}

// Amendment API
export const amendmentApi = {
  getList: async (params: {
    page?: number
    size?: number
    law_id?: string
    processed?: boolean
  }) => {
    const { data } = await api.get('/amendments', { params })
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/amendments/${id}`)
    return data
  },

  analyze: async (id: number) => {
    const { data } = await api.post(`/amendments/${id}/analyze`)
    return data
  },
}

// Review API
export const reviewApi = {
  getList: async (params: {
    page?: number
    size?: number
    need_revision?: boolean
    status?: string
    urgency?: string
  }) => {
    const { data } = await api.get('/reviews', { params })
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/reviews/${id}`)
    return data
  },

  update: async (id: number, updateData: any) => {
    const { data } = await api.patch(`/reviews/${id}`, updateData)
    return data
  },

  getReport: async () => {
    const { data } = await api.get('/reviews/report')
    return data
  },
}

// Department API
export const departmentApi = {
  getList: async (params: {
    page?: number
    size?: number
    search?: string
  }) => {
    const { data } = await api.get('/departments', { params })
    return data
  },

  getAll: async () => {
    const { data } = await api.get('/departments/all')
    return data
  },

  getSummary: async () => {
    const { data } = await api.get('/departments/summary')
    return data
  },

  getTree: async () => {
    const { data } = await api.get('/departments/tree')
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/departments/${id}`)
    return data
  },

  getOrdinances: async (id: number, params: { page?: number; size?: number }) => {
    const { data } = await api.get(`/departments/${id}/ordinances`, { params })
    return data
  },

  create: async (departmentData: {
    code?: string
    name: string
    parent_name?: string
    sort_order?: number
  }) => {
    const { data } = await api.post('/departments', departmentData)
    return data
  },

  update: async (id: number, updateData: {
    name?: string
    parent_name?: string
    sort_order?: number
  }) => {
    const { data } = await api.patch(`/departments/${id}`, updateData)
    return data
  },

  delete: async (id: number) => {
    const { data } = await api.delete(`/departments/${id}`)
    return data
  },

  getInputStatistics: async () => {
    const { data } = await api.get('/departments/input-statistics')
    return data
  },

  downloadTemplate: async () => {
    const response = await api.get('/departments/template/download', {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '부서_업로드_템플릿.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post('/departments/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },
}

// Dashboard API
export const dashboardApi = {
  getSummary: async () => {
    const { data } = await api.get('/dashboard/summary')
    return data
  },

  getRecentAmendments: async (limit: number = 10) => {
    const { data } = await api.get('/dashboard/recent-amendments', {
      params: { limit },
    })
    return data
  },

  getPendingReviews: async (limit: number = 10) => {
    const { data } = await api.get('/dashboard/pending-reviews', {
      params: { limit },
    })
    return data
  },

  getLatestSyncStats: async () => {
    const { data } = await api.get('/dashboard/latest-sync-stats')
    return data
  },

  getOrdinanceRevisionTree: async () => {
    const { data } = await api.get('/dashboard/ordinance-revision-tree')
    return data
  },

  getRevisionNeeded: async (params?: {
    limit?: number
    status?: 'NEEDS_REVISION' | 'UNDER_REVIEW' | 'COMPLETED'
    department?: string
  }): Promise<RevisionNeededListResponse> => {
    const { data } = await api.get('/dashboard/revision-needed', {
      params,
    })
    return data
  },
}

// Maintenance API
export const maintenanceApi = {
  getStatus: async (): Promise<{ enabled: boolean; message: string }> => {
    const { data } = await axios.get('/api/v1/admin/maintenance')
    return data
  },

  toggle: async (enabled: boolean, message?: string) => {
    const { data } = await api.post('/admin/maintenance', { enabled, message })
    return data
  },
}

// AI Analysis API (006-llm-review-assistant)
export const aiApi = {
  analyze: async (ordinanceId: number, lawId: number) => {
    const { data } = await api.post(`/ordinances/${ordinanceId}/ai-analyze`, { law_id: lawId })
    return data
  },

  getResults: async (ordinanceId: number, lawId?: number) => {
    const params = lawId ? { law_id: lawId } : {}
    const { data } = await api.get(`/ordinances/${ordinanceId}/ai-results`, { params })
    return data
  },
}

// Admin API (LLM 프로바이더 관리)
export const adminApi = {
  getLlmProviders: async () => {
    const { data } = await api.get('/admin/llm-providers')
    return data
  },

  updateLlmProvider: async (id: number, updateData: {
    model_name?: string
    is_active?: boolean
    rate_limit_per_minute?: number
  }) => {
    const { data } = await api.patch(`/admin/llm-providers/${id}`, updateData)
    return data
  },

  getAiAnalytics: async (params?: { start_date?: string; end_date?: string }) => {
    const { data } = await api.get('/admin/ai-analytics', { params })
    return data
  },
}

export default api


// Law Search API
export const lawSearchApi = {
  searchByName: async (lawName: string) => {
    const { data } = await api.post('/laws/search', { law_name: lawName })
    return data
  },

  updateAllLawInfo: async () => {
    const { data } = await api.post('/laws/update-all-info')
    return data
  },

  // SSE 스트리밍으로 법령 동기화
  syncLawsStream: () => {
    return new EventSource('/api/v1/laws/sync-stream')
  },
}

// Laws API (법령 목록 관리)
export const lawsApi = {
  getList: async (params: {
    page?: number
    size?: number
    search?: string
    law_type?: string
    dept_name?: string
  }) => {
    const { data } = await api.get('/laws', { params })
    return data
  },

  getAll: async (params?: {
    search?: string
    law_type?: string
    dept_name?: string
  }) => {
    const size = 100
    const countRes = await lawsApi.getCount(params)
    const total = countRes?.count || 0
    const pages = Math.max(1, Math.ceil(total / size))

    const requests = Array.from({ length: pages }, (_, idx) =>
      lawsApi.getList({
        page: idx + 1,
        size,
        ...params,
      })
    )
    const results = await Promise.all(requests)
    return results.flat()
  },

  getCount: async (params?: { search?: string; law_type?: string; dept_name?: string }) => {
    const { data } = await api.get('/laws/count', { params })
    return data
  },

  getTypes: async () => {
    const { data } = await api.get('/laws/types')
    return data
  },

  getDepartments: async () => {
    const { data } = await api.get('/laws/departments')
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/laws/${id}`)
    return data
  },

  getRevisionReason: async (lawId: number): Promise<RevisionReasonResponse | null> => {
    const response = await api.get(`/laws/${lawId}/revision-reason`, {
      validateStatus: (status) => (status >= 200 && status < 300) || status === 204,
    })
    if (response.status === 204) {
      return null
    }
    return response.data
  },

  getOrdinances: async (id: number) => {
    const { data } = await api.get(`/laws/${id}/ordinances`)
    return data
  },

  delete: async (id: number) => {
    const { data } = await api.delete(`/laws/${id}`)
    return data
  },

  deleteOrdinanceMapping: async (mappingId: number) => {
    const { data } = await api.delete(`/ordinances/law-mappings/${mappingId}`)
    return data
  },

  bulkDelete: async (lawIds: number[]) => {
    const { data } = await api.post('/laws/bulk-delete', { law_ids: lawIds })
    return data
  },
}

export function useRevisionReason(lawId?: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['revision-reason', lawId],
    queryFn: () => lawsApi.getRevisionReason(lawId as number),
    enabled: !!lawId && enabled,
    retry: false,
  })
}

export function useDetectionResults(ordinanceId?: number, enabled: boolean = true) {
  return useQuery({
    queryKey: ['detection-results', ordinanceId],
    queryFn: () => ordinanceApi.getDetectionResults(ordinanceId as number),
    enabled: !!ordinanceId && enabled,
    retry: false,
  })
}

export function useRunDetection(ordinanceId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (methods?: DetectionMethodType[]) => ordinanceApi.runDetection(ordinanceId, methods),
    onSuccess: (data) => {
      queryClient.setQueryData(['detection-results', ordinanceId], data)
      queryClient.invalidateQueries({ queryKey: ['detection-results', ordinanceId] })
    },
  })
}

// Ordinance Management API (추가 기능)
export const ordinanceManagementApi = {
  create: async (ordinanceData: {
    name: string
    category: string
    department?: string
    enacted_date?: string
    enforced_date?: string
  }) => {
    const { data } = await api.post('/ordinances/create', ordinanceData)
    return data
  },

  searchFromApi: async (query: string, org?: string, sborg?: string) => {
    const { data } = await api.post('/ordinances/search-api', {
      query,
      org: org || '6110000',
      sborg: sborg || '3220000',
    })
    return data
  },

  registerFromApi: async (ordinanceData: {
    serial_no: string
    name: string
    ordinance_id: string
    enacted_date?: string
    promulgation_no?: string
    revision_type?: string
    org_name?: string
    category?: string
    enforced_date?: string
    detail_link?: string
    field_name?: string
    department?: string
  }) => {
    const { data } = await api.post('/ordinances/register-from-api', ordinanceData)
    return data
  },

  updateAllInfo: async () => {
    const { data } = await api.post('/ordinances/update-all-info')
    return data
  },
}

// Law Changes API (법령 변경 감지 로그)
export const lawChangesApi = {
  getList: async (params: {
    page?: number
    size?: number
    api_status?: string  // success, no_response, not_found
    dept_name?: string
    sync_batch_id?: string
    sync_date?: string  // YYYY-MM-DD 형식
    search?: string
    changed_field?: string  // 변경내용 필드 필터
    revision_type?: string  // 제개정구분 필터
  }) => {
    const { data } = await api.get('/law-changes', { params })
    return data
  },

  getRevisionTypes: async () => {
    const { data } = await api.get('/law-changes/revision-types')
    return data
  },

  getSyncDates: async () => {
    const { data } = await api.get('/law-changes/sync-dates')
    return data
  },

  getStats: async (params?: { sync_date?: string }) => {
    const { data } = await api.get('/law-changes/stats', { params })
    return data
  },

  getDepartments: async () => {
    const { data } = await api.get('/law-changes/departments')
    return data
  },

  getSyncBatches: async () => {
    const { data } = await api.get('/law-changes/sync-batches')
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/law-changes/${id}`)
    return data
  },

  getHistory: async (lawId: number, params?: { page?: number; size?: number }) => {
    const { data } = await api.get(`/law-changes/history/${lawId}`, { params })
    return data
  },

  getHistorySummary: async () => {
    const { data } = await api.get('/law-changes/history-summary')
    return data
  },

  exportExcel: async (params: {
    api_status?: string
    dept_name?: string
    sync_date?: string
    search?: string
  }) => {
    const response = await api.get('/law-changes/export', {
      params,
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const filename = `법령변경이력_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

// Articles API (조문 관리)
export const articleApi = {
  // 조문 목록 조회
  getList: async (params: {
    page?: number
    size?: number
    law_id?: number
    search?: string
    has_ordinance?: boolean
    changed_since?: string  // YYYY-MM-DD
  }) => {
    const { data } = await api.get('/articles', { params })
    return data
  },

  // 조문 상세 조회
  getById: async (id: number) => {
    const { data } = await api.get(`/articles/${id}`)
    return data
  },

  // 조문과 연계된 조례 목록 조회
  getOrdinances: async (id: number) => {
    const { data } = await api.get(`/articles/${id}/ordinances`)
    return data
  },

  // 조문-조례 연계 추가
  createMapping: async (
    articleId: number,
    mappingData: {
      ordinance_id: number
      mapping_reason?: string
      related_article_nos?: string
    }
  ) => {
    const { data } = await api.post(`/articles/${articleId}/mappings`, mappingData)
    return data
  },

  // 조문-조례 연계 삭제
  deleteMapping: async (articleId: number, mappingId: number) => {
    const { data } = await api.delete(`/articles/${articleId}/mappings/${mappingId}`)
    return data
  },

  // 조문 변경 이력 조회
  getHistory: async (id: number) => {
    const { data } = await api.get(`/articles/${id}/history`)
    return data
  },

  // 조문 동기화 (관리자 전용)
  sync: async (request?: {
    law_ids?: number[]
    force?: boolean
  }) => {
    const { data } = await api.post('/articles/sync', request || {})
    return data
  },

  // 조문 개수 조회
  getCount: async (params?: {
    law_id?: number
    has_ordinance?: boolean
    changed_since?: string
  }) => {
    const response = await api.get('/articles', {
      params: { ...params, page: 1, size: 1 }
    })
    return response.data.total
  },

  // ========================================
  // Phase 4: 추가 API
  // ========================================

  // 대량 매핑
  createBulkMappings: async (request: {
    mappings: Array<{ article_id: number; ordinance_id: number }>
    notes?: string
  }) => {
    const { data } = await api.post('/articles/mappings/bulk', request)
    return data
  },

  // 개정 검토 필요 조례 목록
  getRevisionNeededOrdinances: async (params?: {
    page?: number
    size?: number
    days?: number
    department?: string
  }) => {
    const { data } = await api.get('/articles/revision-needed', { params })
    return data
  },

  // 자동 매핑 추천
  getAutoRecommendations: async (params?: {
    law_id?: number
    ordinance_id?: number
    min_score?: number
    limit?: number
  }) => {
    const { data } = await api.get('/articles/auto-recommendations', { params })
    return data
  },
}
