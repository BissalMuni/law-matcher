/**
 * SyncContext - 법령 동기화 상태를 앱 전역에서 관리
 *
 * 탭(페이지) 전환 시에도 SSE 연결과 동기화 상태가 유지됨
 */
import { createContext, useContext, useRef, useState, useCallback, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { lawSearchApi } from '../services/api'

export interface SyncProgress {
  type: string
  current?: number
  total?: number
  law_name?: string
  status?: string
  result?: string
  message?: string
  reconnecting?: boolean
}

export interface ChangedLaw {
  id: number
  law_id: number
  law_name: string
  law_type: string
  proclaimed_date: string | null
  enforced_date: string | null
  revision_type: string | null
  dept_name: string | null
  changes: Record<string, { old: string | null; new: string | null }>
  api_status?: 'success' | 'no_response' | 'not_found'
  api_message?: string
  article_sync?: {
    synced_articles: number
    created: number
    updated: number
    deleted: number
    changes_detected: number
  }
}

export interface SyncResult {
  total: number
  updated: number
  failed: number
  changedCount: number
  changedLaws: ChangedLaw[]
  articleSyncedLaws: number
  articleSyncedArticles: number
  articleCreated: number
  articleUpdated: number
  articleDeleted: number
  articleChangesDetected: number
  articleSyncFailed: number
}

interface SyncContextValue {
  syncing: boolean
  progress: SyncProgress | null
  logs: string[]
  syncResult: SyncResult | null
  changedLaws: ChangedLaw[]
  startSync: () => void
  stopSync: () => void
  clearResult: () => void
}

const SyncContext = createContext<SyncContextValue | null>(null)

export function SyncProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const eventSourceRef = useRef<EventSource | null>(null)

  const [syncing, setSyncing] = useState(false)
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [changedLaws, setChangedLaws] = useState<ChangedLaw[]>([])

  const startSync = useCallback(() => {
    // 이미 동기화 중이면 무시
    if (eventSourceRef.current) return

    setSyncing(true)
    setProgress(null)
    setLogs([])
    setSyncResult(null)
    setChangedLaws([])

    const eventSource = lawSearchApi.syncLawsStream()
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        switch (data.type) {
          case 'start':
            setLogs((prev) => [...prev, data.message])
            break

          case 'progress':
            setProgress({
              type: data.type,
              current: data.current,
              total: data.total,
              law_name: data.law_name,
              status: data.status,
              result: data.result,
            })
            if (data.status === 'compared') {
              setLogs((prev) => {
                const newLogs = [...prev, data.message]
                return newLogs.slice(-50)
              })
            }
            break

          case 'changed':
            setChangedLaws((prev) => [...prev, data.law])
            setLogs((prev) => [...prev.slice(-49), `[변경] ${data.law.law_name}`])
            break

          case 'error':
            setLogs((prev) => [...prev, `[오류] ${data.message}`])
            break

          case 'complete':
            setSyncing(false)
            setSyncResult({
              total: data.total,
              updated: data.updated,
              failed: data.failed,
              changedCount: data.changed_count,
              changedLaws: data.changed_laws,
              articleSyncedLaws: data.article_synced_laws || 0,
              articleSyncedArticles: data.article_synced_articles || 0,
              articleCreated: data.article_created || 0,
              articleUpdated: data.article_updated || 0,
              articleDeleted: data.article_deleted || 0,
              articleChangesDetected: data.article_changes_detected || 0,
              articleSyncFailed: data.article_sync_failed || 0,
            })
            setLogs((prev) => [...prev, data.message])
            eventSource.close()
            eventSourceRef.current = null
            // 데이터 새로고침
            queryClient.invalidateQueries({ queryKey: ['amendments'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
            queryClient.invalidateQueries({ queryKey: ['law-changes-sync-dates'] })
            break
        }
      } catch (e) {
        console.error('SSE parse error:', e)
      }
    }

    eventSource.onerror = () => {
      setSyncing(false)
      setLogs((prev) => [
        ...prev,
        '[오류] 동기화 스트림 연결이 종료되었습니다.',
      ])
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [queryClient])

  const stopSync = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setSyncing(false)
  }, [])

  const clearResult = useCallback(() => {
    setChangedLaws([])
    setSyncResult(null)
    setLogs([])
    setProgress(null)
  }, [])

  return (
    <SyncContext.Provider
      value={{ syncing, progress, logs, syncResult, changedLaws, startSync, stopSync, clearResult }}
    >
      {children}
    </SyncContext.Provider>
  )
}

export function useSync() {
  const ctx = useContext(SyncContext)
  if (!ctx) throw new Error('useSync must be used within SyncProvider')
  return ctx
}
