import axios from 'axios'

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
    law_id: string
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

  syncFromMoleg: async (params?: { org?: string; sborg?: string }) => {
    const { data } = await api.post('/ordinances/sync', params || {})
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
}

export default api
