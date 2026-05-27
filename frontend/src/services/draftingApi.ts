/**
 * 입안심사(drafting) API 클라이언트 — law-ebansimsa 통합 (Phase 4)
 *
 * law-matcher의 /api/v1/drafting/* 엔드포인트를 호출한다.
 * 토큰 처리는 기존 services/api.ts 와 동일 규칙(law_matcher_token, simple_ 제외).
 */
import axios from 'axios'

const draftingClient = axios.create({
  baseURL: '/api/v1/drafting',
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
})

draftingClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('law_matcher_token')
  if (token && !token.startsWith('simple_')) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---------- 타입 ----------

export type ProjectKind = 'enact' | 'amend_partial' | 'amend_full'

export interface SourceOrdinance {
  id: number
  name: string
  category: string | null
  org_name: string | null
  parent_law_count: number
  has_text: boolean
}

export interface ParentLaw {
  law_id: number
  law_name: string
  law_type: string
  proclaimed_date: string | null
  related_articles: string | null
}

export interface PreviewSection {
  article_no: number
  article_label: string
  title: string
  body: string
  sort_order: number
}

export interface SourcePreview {
  found: boolean
  ordinance: {
    id: number
    name: string
    category: string | null
    org_name: string | null
    detail_link: string | null
  }
  sections: PreviewSection[]
  parent_laws: ParentLaw[]
  section_count: number
}

export interface DraftingProject {
  id: number
  kind: ProjectKind
  title: string
  municipality: string
  ordinance_id: number | null
  source_url: string | null
  status: string
  progress: number
  created_at: string
  updated_at: string
}

export interface DraftingStage {
  id: number
  key: string
  label: string
  sort_order: number
  required: boolean
  status: string
  stale_reason: string | null
  wiki_ref: string | null
  parent_id: number | null
  confirmed_at: string | null
}

export interface DraftingSection {
  id: number
  project_id: number
  stage_id: number
  article_no: number
  article_label: string | null
  title: string
  body: string
  original_body: string | null
  change_type: string | null
  sort_order: number
}

export interface ProjectDetail extends DraftingProject {
  stages: DraftingStage[]
  sections: DraftingSection[]
  parent_laws: ParentLaw[]
}

export interface CriterionCell {
  criterion_id: string
  source: 'ebansimsa' | 'jungbigijun'
  title?: string | null
}

export interface ValidationCellResult {
  article_id: string
  criterion_id: string
  source: string
  verdict: 'pass' | 'fail' | 'na' | 'pending'
  severity: 'hint' | 'violation'
  reason?: string | null
  suggestion?: string | null
  dismissed_reason?: string | null
}

export interface DraftingMessage {
  id: number
  stage_id: number
  role: string
  content: string
  citations?: string[] | null
  attachments?: unknown
  applied: boolean
  created_at: string
}

// ---------- API ----------

export const draftingApi = {
  // 등록 조례 소스
  listSourceOrdinances: async (query?: string, limit = 30): Promise<SourceOrdinance[]> => {
    const res = await draftingClient.get('/source-ordinances', { params: { query, limit } })
    return res.data.ordinances
  },
  previewSource: async (ordinanceId: number): Promise<SourcePreview> => {
    const res = await draftingClient.get(`/source-ordinances/${ordinanceId}/preview`)
    return res.data
  },
  getParentLaws: async (ordinanceId: number): Promise<ParentLaw[]> => {
    const res = await draftingClient.get(`/source-ordinances/${ordinanceId}/parent-laws`)
    return res.data.parent_laws
  },

  // 프로젝트
  createProject: async (body: {
    kind: ProjectKind
    title: string
    municipality: string
    ordinance_id?: number | null
    source_url?: string | null
  }): Promise<DraftingProject> => {
    const res = await draftingClient.post('/projects', body)
    return res.data
  },
  listProjects: async (): Promise<DraftingProject[]> => {
    const res = await draftingClient.get('/projects')
    return res.data
  },
  getProject: async (id: number): Promise<ProjectDetail> => {
    const res = await draftingClient.get(`/projects/${id}`)
    return res.data
  },
  deleteProject: async (id: number): Promise<void> => {
    await draftingClient.delete(`/projects/${id}`)
  },

  // 단계
  updateStage: async (
    stageId: number,
    body: { status: string; stale_reason?: string | null },
  ): Promise<DraftingStage> => {
    const res = await draftingClient.patch(`/stages/${stageId}`, body)
    return res.data
  },

  // 조문
  listSections: async (projectId: number): Promise<DraftingSection[]> => {
    const res = await draftingClient.get(`/projects/${projectId}/sections`)
    return res.data
  },
  upsertSection: async (body: Partial<DraftingSection> & {
    project_id: number
    stage_id: number
  }): Promise<DraftingSection> => {
    const res = await draftingClient.post('/sections', body)
    return res.data
  },
  deleteSection: async (sectionId: number): Promise<void> => {
    await draftingClient.delete(`/sections/${sectionId}`)
  },

  // 메시지
  listMessages: async (stageId: number): Promise<DraftingMessage[]> => {
    const res = await draftingClient.get(`/stages/${stageId}/messages`)
    return res.data
  },
  addMessage: async (
    stageId: number,
    body: { role: string; content: string; citations?: string[]; applied?: boolean },
  ): Promise<DraftingMessage> => {
    const res = await draftingClient.post(`/stages/${stageId}/messages`, body)
    return res.data
  },

  // 기준 카탈로그
  listCriteria: async (): Promise<CriterionCell[]> => {
    const res = await draftingClient.get('/criteria')
    return res.data.criteria
  },

  // 검증
  validatePrecise: async (body: {
    articles: { article_id: string; title: string; text: string }[]
    criteria: CriterionCell[]
  }): Promise<{
    results: ValidationCellResult[]
    total_cells: number
    filled_cells: number
    complete: boolean
  }> => {
    const res = await draftingClient.post('/validate/precise', body)
    return res.data
  },
  mapCriteria: async (body: {
    article: { article_id: string; title: string; text: string }
    criteria: CriterionCell[]
  }): Promise<CriterionCell[]> => {
    const res = await draftingClient.post('/validate/map-criteria', body)
    return res.data.criteria
  },
  saveValidations: async (
    sectionId: number,
    results: {
      criterion_id: string
      source: string
      verdict: string
      severity?: string | null
      reason?: string | null
      suggestion?: string | null
      dismissed_reason?: string | null
    }[],
    replace = true,
  ): Promise<void> => {
    await draftingClient.post(`/sections/${sectionId}/validations`, { results, replace })
  },

  // 내보내기 (DOCX/PDF) — blob
  exportDocument: async (body: {
    project_title: string
    municipality: string
    sections: { article_label: string; title: string; body: string; order: number }[]
    format: 'docx' | 'pdf'
  }): Promise<Blob> => {
    const res = await draftingClient.post('/export', body, { responseType: 'blob' })
    return res.data
  },
}

// ---------- AI 작성 스트리밍 (SSE, POST) ----------

export interface DraftStreamHandlers {
  onCitations?: (citations: string[]) => void
  onDelta?: (text: string) => void
  onDone?: () => void
  onError?: (err: unknown) => void
}

export async function streamDraft(
  body: {
    stage_key: string
    intent: string
    wiki_refs?: { criterion_id: string; content?: string }[]
    references?: { title: string; content?: string; municipality?: string }[]
    parent_laws?: string[]
  },
  handlers: DraftStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('law_matcher_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token && !token.startsWith('simple_')) headers.Authorization = `Bearer ${token}`

  try {
    const res = await fetch('/api/v1/drafting/draft/generate', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal,
    })
    if (!res.ok || !res.body) throw new Error(`draft generate failed: ${res.status}`)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() ?? ''
      for (const evt of events) {
        const line = evt.replace(/^data:\s?/, '').trim()
        if (!line) continue
        if (line === '[DONE]') {
          handlers.onDone?.()
          return
        }
        try {
          const parsed = JSON.parse(line)
          if (parsed.type === 'citations') handlers.onCitations?.(parsed.citations ?? [])
          else if (parsed.type === 'delta') handlers.onDelta?.(parsed.text ?? '')
        } catch {
          // 부분 청크 — 무시
        }
      }
    }
    handlers.onDone?.()
  } catch (err) {
    handlers.onError?.(err)
  }
}
