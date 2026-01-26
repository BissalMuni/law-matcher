import axios from 'axios'
import { RevisionNeededListResponse } from '../types/api'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Ordinance API
export const ordinanceApi = {
  getList: async (params: {
    page?: number
    size?: number
    category?: string
    department?: string
    search?: string
    no_parent_law_filter?: string  // "no_mapping" | "confirmed_none"
  }) => {
    const { data } = await api.get('/ordinances', { params })
    return data
  },

  getById: async (id: number) => {
    const { data } = await api.get(`/ordinances/${id}`)
    return data
  },

  getArticles: async (id: number) => {
    const { data } = await api.get(`/ordinances/${id}/articles`)
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

  syncFromMoleg: async (params?: { org?: string; sborg?: string; password?: string }) => {
    const headers = params?.password ? { 'X-Admin-Password': params.password } : {}
    const { data } = await api.post('/ordinances/sync', params || {}, { headers })
    return data
  },

  getDepartments: async () => {
    const { data } = await api.get('/ordinances/departments')
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
  }) => {
    const { data } = await api.get('/law-changes', { params })
    return data
  },

  // 동기화 날짜 목록 조회 (드롭다운용)
  getSyncDates: async () => {
    const { data } = await api.get('/law-changes/sync-dates')
    return data
  },

  getStats: async () => {
    const { data } = await api.get('/law-changes/stats')
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
