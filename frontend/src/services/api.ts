import axios from 'axios'
import { RevisionNeededListResponse } from '../types/api'
import { LoginRequest, RegisterRequest, TokenResponse, User, PasswordChangeRequest } from '../types/auth'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// JWT Token Interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('law_matcher_token')
    if (token) {
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
      // Clear auth data and redirect to login
      localStorage.removeItem('law_matcher_token')
      localStorage.removeItem('law_matcher_user')

      // Only redirect if not already on login/register page
      if (!window.location.pathname.startsWith('/login') &&
          !window.location.pathname.startsWith('/register') &&
          !window.location.pathname.startsWith('/landing')) {
        window.location.href = '/login'
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

  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  me: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  changePassword: async (data: PasswordChangeRequest): Promise<User> => {
    const response = await api.post('/auth/change-password', data)
    return response.data
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
    review_result?: string  // 개정필요/개정불필요/검토중/보류
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

  getById: async (id: number) => {
    const { data } = await api.get(`/departments/${id}`)
    return data
  },

  getOrdinances: async (id: number, params: { page?: number; size?: number }) => {
    const { data } = await api.get(`/departments/${id}/ordinances`, { params })
    return data
  },

  create: async (departmentData: {
    code: string
    name: string
    parent_code?: string
    phone?: string
  }) => {
    const { data } = await api.post('/departments', departmentData)
    return data
  },

  update: async (id: number, updateData: {
    name?: string
    parent_code?: string
    phone?: string
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

// Law Changes API (법령 변경 이력 관리)
export const lawChangesApi = {
  getList: async (params: {
    page?: number
    size?: number
    status?: string  // pending, reviewing, approved, rejected
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

  // 제개정구분 목록 조회 (드롭다운용)
  getRevisionTypes: async () => {
    const { data } = await api.get('/law-changes/revision-types')
    return data
  },

  // 동기화 날짜 목록 조회 (드롭다운용)
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

  approve: async (id: number, request?: { process_note?: string; processed_by?: string }) => {
    const { data } = await api.post(`/law-changes/${id}/approve`, request || {})
    return data
  },

  reject: async (id: number, request: { process_note: string; processed_by?: string }) => {
    const { data } = await api.post(`/law-changes/${id}/reject`, request)
    return data
  },

  bulkApprove: async (ids: number[], request?: { process_note?: string; processed_by?: string }) => {
    const { data } = await api.post('/law-changes/bulk-approve', { ids, ...request })
    return data
  },

  bulkReject: async (ids: number[], request: { process_note: string; processed_by?: string }) => {
    const { data } = await api.post('/law-changes/bulk-reject', { ids, ...request })
    return data
  },

  // 특정 법령의 변경 연혁 조회
  getHistory: async (lawId: number, params?: { page?: number; size?: number }) => {
    const { data } = await api.get(`/law-changes/history/${lawId}`, { params })
    return data
  },

  // 법령별 변경 연혁 요약 조회
  getHistorySummary: async () => {
    const { data } = await api.get('/law-changes/history-summary')
    return data
  },

  // 엑셀 다운로드
  exportExcel: async (params: {
    status?: string
    api_status?: string
    dept_name?: string
    sync_date?: string
    search?: string
  }) => {
    const response = await api.get('/law-changes/export', {
      params,
      responseType: 'blob',
    })
    // 파일 다운로드 처리
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
