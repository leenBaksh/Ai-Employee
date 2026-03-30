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

export interface ServiceConnection {
  id: string
  label: string
  icon: string
  status: string
  detail: string
  last_success: string | null
  last_error: string | null
  last_error_msg: string
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
  connections: ServiceConnection[]
  tasks: TaskItem[]
  approvals: TaskItem[]
  logs: LogEntry[]
  done_recent?: TaskItem[]
  generated_at?: string
}

interface DashboardContextType {
  data: DashboardData | null
  connected: boolean
}

// ── Context ───────────────────────────────────────────────────────────────────

const DashboardContext = createContext<DashboardContextType>({
  data: null,
  connected: false,
})

// ── Provider ──────────────────────────────────────────────────────────────────

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stats, health, connections, tasks, approvals, logs] = await Promise.all([
          fetch('/api/stats').then(r => r.json()),
          fetch('/api/health').then(r => r.json()),
          fetch('/api/connections').then(r => r.json()),
          fetch('/api/tasks?limit=10').then(r => r.json()),
          fetch('/api/approvals').then(r => r.json()),
          fetch('/api/logs?limit=10').then(r => r.json()),
        ])

        setData({
          stats, health, connections, tasks, approvals, logs,
          done_recent: [],
          generated_at: new Date().toISOString(),
        })
        setConnected(true)
      } catch (error) {
        console.error('Dashboard error:', error)
        setConnected(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 10000)

    return () => clearInterval(interval)
  }, [])

  return (
    <DashboardContext.Provider value={{ data, connected }}>
      {children}
    </DashboardContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDashboardContext() {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error('useDashboardContext must be used within DashboardProvider')
  }
  return context
}
