'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Stats {
  needs_action: number
  pending_approval: number
  done: number
  drafts: number
  scheduled: number
  in_progress_local: number
  in_progress_cloud: number
  sla_breaches: number
}

export interface TaskItem {
  filename: string
  age_seconds: number
  age_human: string
  type: string
}

export interface Agent {
  agent_id: string
  status: 'online' | 'offline' | 'never_seen' | 'error'
  timestamp: string | null
  role?: string
  needs_action_count?: number
  pending_approval_count?: number
  vault_path?: string
}

export interface LogEntry {
  timestamp: string
  action_type: string
  actor: string
  target: string
  result: string
}

export interface DashboardData {
  stats: Stats
  health: Agent[]
  tasks: TaskItem[]
  approvals: TaskItem[]
  logs: LogEntry[]
  done_recent: TaskItem[]
  generated_at: string
}

// ── Context ───────────────────────────────────────────────────────────────────

interface DashboardContextType {
  data: DashboardData | null
  connected: boolean
}

const DashboardContext = createContext<DashboardContextType>({
  data: null,
  connected: false,
})

// ── Provider ──────────────────────────────────────────────────────────────────

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let es: EventSource | null = null
    let pollTimer: ReturnType<typeof setInterval> | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    const fetchAll = async () => {
      try {
        const [stats, health, tasks, approvals, logs] = await Promise.all([
          fetch('/api/stats').then(r => r.json()),
          fetch('/api/health').then(r => r.json()),
          fetch('/api/tasks').then(r => r.json()),
          fetch('/api/approvals').then(r => r.json()),
          fetch('/api/logs').then(r => r.json()),
        ])
        setData({
          stats, health, tasks, approvals, logs,
          done_recent: [],
          generated_at: new Date().toISOString(),
        })
      } catch {
        // server may be starting up — silently retry
      }
    }

    const stopPolling = () => {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    }

    const startPolling = () => {
      if (pollTimer) return
      setConnected(false)
      fetchAll()
      pollTimer = setInterval(fetchAll, 5000)
    }

    const connect = () => {
      if (typeof window === 'undefined' || !window.EventSource) {
        startPolling()
        return
      }

      es = new EventSource('/api/stream')

      es.onopen = () => {
        setConnected(true)
        stopPolling()
        fetchAll()  // refresh immediately when SSE connects
      }

      es.onmessage = (event) => {
        try { setData(JSON.parse(event.data)) } catch { /* ignore */ }
      }

      es.onerror = () => {
        setConnected(false)
        es?.close()
        es = null
        startPolling()
        // Try reconnecting SSE after 30s
        if (!retryTimer) {
          retryTimer = setTimeout(() => {
            retryTimer = null
            stopPolling()
            connect()
          }, 30_000)
        }
      }
    }

    fetchAll()  // immediate load — don't wait for SSE to deliver first event
    connect()

    return () => {
      es?.close()
      stopPolling()
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [])

  return (
    <DashboardContext.Provider value={{ data, connected }}>
      {children}
    </DashboardContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDashboardContext() {
  return useContext(DashboardContext)
}
