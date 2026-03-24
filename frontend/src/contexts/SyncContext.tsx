/**
 * SyncContext - 법령 동기화 상태를 앱 전역에서 관리
 *
 * 백그라운드 Celery 태스크 + Redis 진행 상황 폴링 방식
 * 탭 전환, 브라우저 닫기와 무관하게 서버에서 끝까지 실행됨
 */
import { createContext, useContext, useRef, useState, useCallback, useEffect, type ReactNode } from 'react'
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
  flaggedOrdinances: number
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
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [syncing, setSyncing] = useState(false)
  const [progress, setProgress] = useState<SyncProgress | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [changedLaws, setChangedLaws] = useState<ChangedLaw[]>([])

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const handleComplete = useCallback((data: any) => {
    setSyncing(false)
    stopPolling()
    setChangedLaws(data.changed_laws || [])
    setSyncResult({
      total: data.total || 0,
      updated: data.updated || 0,
      failed: data.failed || 0,
      changedCount: data.changed_count || 0,
      changedLaws: data.changed_laws || [],
      flaggedOrdinances: data.flagged_ordinances || 0,
      articleSyncedLaws: data.article_synced_laws || 0,
      articleSyncedArticles: data.article_synced_articles || 0,
      articleCreated: data.article_created || 0,
      articleUpdated: data.article_updated || 0,
      articleDeleted: data.article_deleted || 0,
      articleChangesDetected: data.article_changes_detected || 0,
      articleSyncFailed: data.article_sync_failed || 0,
    })
    setLogs((prev) => [...prev, data.message || '동기화 완료'])
    queryClient.invalidateQueries({ queryKey: ['amendments'] })
    queryClient.invalidateQueries({ queryKey: ['law-changes'] })
    queryClient.invalidateQueries({ queryKey: ['law-changes-stats'] })
    queryClient.invalidateQueries({ queryKey: ['law-changes-sync-dates'] })
  }, [queryClient, stopPolling])

  const startPolling = useCallback(() => {
    stopPolling()

    pollingRef.current = setInterval(async () => {
      try {
        const data = await lawSearchApi.getSyncProgress()

        if (data.status === 'RUNNING') {
          setProgress({
            type: 'progress',
            current: data.current,
            total: data.total,
            law_name: data.law_name,
            status: data.step || 'requesting',
            message: data.message,
          })
          // changed_laws 실시간 반영
          if (data.changed_laws?.length) {
            setChangedLaws(data.changed_laws)
          }
        } else if (data.status === 'COMPLETED') {
          handleComplete(data)
        } else if (data.status === 'FAILED') {
          setSyncing(false)
          stopPolling()
          setLogs((prev) => [...prev, `[오류] ${data.message || '동기화 실패'}`])
        } else if (data.status === 'IDLE') {
          // 아직 시작 전이면 무시
        }
      } catch (e) {
        console.error('Polling error:', e)
      }
    }, 2000) // 2초 간격 폴링
  }, [stopPolling, handleComplete])

  const startSync = useCallback(async () => {
    if (syncing) return

    setSyncing(true)
    setProgress(null)
    setLogs([])
    setSyncResult(null)
    setChangedLaws([])

    try {
      await lawSearchApi.startSync()
      setLogs(['동기화가 시작되었습니다.'])
      startPolling()
    } catch (e: any) {
      if (e?.response?.status === 409) {
        // 이미 실행 중 — 폴링 시작
        setLogs(['이미 동기화가 진행 중입니다. 진행 상황을 조회합니다.'])
        startPolling()
      } else {
        setSyncing(false)
        setLogs([`[오류] 동기화 시작 실패: ${e?.response?.data?.detail || e.message}`])
      }
    }
  }, [syncing, startPolling])

  const stopSync = useCallback(() => {
    stopPolling()
    setSyncing(false)
  }, [stopPolling])

  const clearResult = useCallback(async () => {
    setChangedLaws([])
    setSyncResult(null)
    setLogs([])
    setProgress(null)
    try {
      await lawSearchApi.clearSyncProgress()
    } catch (e) {
      // ignore
    }
  }, [])

  // 마운트 시 이미 실행 중인 동기화가 있는지 확인
  useEffect(() => {
    const checkExisting = async () => {
      try {
        const data = await lawSearchApi.getSyncProgress()
        if (data.status === 'RUNNING') {
          setSyncing(true)
          setProgress({
            type: 'progress',
            current: data.current,
            total: data.total,
            law_name: data.law_name,
            status: data.step || 'requesting',
          })
          setLogs(['기존 동기화 진행 중 — 진행 상황을 조회합니다.'])
          startPolling()
        }
      } catch (e) {
        // ignore
      }
    }
    checkExisting()
    return () => stopPolling()
  }, [startPolling, stopPolling])

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
