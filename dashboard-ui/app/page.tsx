'use client'

import { useDashboardContext } from '@/context/DashboardContext'
import StatCard from '@/components/StatCard'
import TypeDot from '@/components/TypeDot'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch { return '--:--' }
}

function formatAgo(iso: string) {
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60)    return `${Math.round(diff)}s ago`
    if (diff < 3600)  return `${Math.round(diff / 60)}m ago`
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
    return `${Math.round(diff / 86400)}d ago`
  } catch { return '?' }
}

function ageClass(s: number) {
  if (s > 86400) return 'text-red-400'
  if (s > 3600)  return 'text-amber-400'
  return 'text-slate-400'
}

function resultClass(result: string) {
  const r = (result ?? '').toLowerCase()
  if (r === 'success')         return 'text-green-400'
  if (r === 'error')           return 'text-red-400'
  if (r === 'warning')         return 'text-amber-400'
  if (r === 'breach_detected') return 'text-red-400'
  if (r === 'notified')        return 'text-cyan-400'
  if (r === 'in_progress')     return 'text-cyan-400'
  return 'text-slate-500'
}

// ── Agent health badge ────────────────────────────────────────────────────────

function agentBorderClass(status: string) {
  if (status === 'online')  return 'border-green-800/60'
  if (status === 'offline') return 'border-red-800/60'
  return 'border-slate-800'
}

function agentDotClass(status: string) {
  if (status === 'online')  return 'bg-green-400 animate-pulse'
  if (status === 'offline') return 'bg-red-500'
  return 'bg-slate-600'
}

function agentTextClass(status: string) {
  if (status === 'online')  return 'text-green-400'
  if (status === 'offline') return 'text-red-400'
  return 'text-slate-500'
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const { data } = useDashboardContext()
  const stats    = data?.stats
  const health   = data?.health   ?? []
  const tasks    = (data?.tasks   ?? []).slice(0, 5)
  const logs     = (data?.logs    ?? []).slice(0, 10)
  const approvals = data?.approvals ?? []

  return (
    <div className="p-6 space-y-5">

      {/* ── Agent health bar ── */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-slate-500 text-xs uppercase tracking-widest font-semibold">
          Agents
        </span>
        {health.length === 0 ? (
          <span className="text-slate-600 text-sm">Connecting…</span>
        ) : health.map(a => (
          <div
            key={a.agent_id}
            className={`flex items-center gap-2 bg-slate-900 border rounded-lg px-3 py-1.5 text-xs
              ${agentBorderClass(a.status)}`}
          >
            <span className={`w-2 h-2 rounded-full flex-shrink-0 ${agentDotClass(a.status)}`} />
            <span className="font-semibold text-slate-200">{a.agent_id}</span>
            <span className={`font-medium ${agentTextClass(a.status)}`}>
              {a.status.toUpperCase()}
            </span>
            {a.timestamp && (
              <span className="text-slate-500">• {formatAgo(a.timestamp)}</span>
            )}
          </div>
        ))}
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon="📥" value={stats?.needs_action     ?? '—'} label="Needs Action" />
        <StatCard icon="⏱"  value={stats?.pending_approval ?? '—'} label="Pending Approval" color="purple" />
        <StatCard icon="✅" value={stats?.done             ?? '—'} label="Done"          color="green" />
        <StatCard
          icon="🚨"
          value={stats?.sla_breaches ?? '—'}
          label="SLA Breaches"
          color="red"
          alert={(stats?.sla_breaches ?? 0) > 0}
        />
        <StatCard icon="📝" value={stats?.drafts ?? '—'} label="Drafts"      color="cyan" />
        <StatCard
          icon="⚙️"
          value={(stats?.in_progress_local ?? 0) + (stats?.in_progress_cloud ?? 0)}
          label="In Progress"
          color="amber"
        />
      </div>

      {/* ── Two-column: tasks + logs ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Mini task list */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="bg-slate-800/40 border-b border-slate-800 px-4 py-2.5 flex justify-between items-center">
            <span className="text-cyan-400 text-xs font-semibold uppercase tracking-widest">
              Task Queue
            </span>
            <span className="text-slate-500 text-xs">{data?.tasks?.length ?? 0} items</span>
          </div>
          <div className="divide-y divide-slate-800/50 max-h-64 overflow-y-auto">
            {tasks.length === 0 ? (
              <div className="p-8 text-center text-slate-600 text-sm">No pending tasks ✅</div>
            ) : tasks.map(t => (
              <div
                key={t.filename}
                className="flex items-center justify-between px-4 py-2.5 hover:bg-slate-800/30 transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <TypeDot type={t.type} />
                  <span className="font-mono text-xs text-slate-300 truncate">{t.filename}</span>
                </div>
                <span className={`text-xs flex-shrink-0 ml-2 ${ageClass(t.age_seconds)}`}>
                  {t.age_human}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Mini activity log */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="bg-slate-800/40 border-b border-slate-800 px-4 py-2.5 flex justify-between items-center">
            <span className="text-cyan-400 text-xs font-semibold uppercase tracking-widest">
              Recent Activity
            </span>
            <span className="text-slate-500 text-xs">{data?.logs?.length ?? 0} entries</span>
          </div>
          <div className="divide-y divide-slate-800/50 max-h-64 overflow-y-auto">
            {logs.length === 0 ? (
              <div className="p-8 text-center text-slate-600 text-sm">No log entries</div>
            ) : logs.map((e, i) => (
              <div key={i} className="flex items-center gap-2 px-4 py-2 font-mono text-xs">
                <span className="text-slate-500 flex-shrink-0 w-11">{formatTime(e.timestamp)}</span>
                <span className="text-slate-400 flex-1 truncate">{e.action_type}</span>
                <span className={`flex-shrink-0 ${resultClass(e.result)}`}>{e.result}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Mini approvals ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="bg-slate-800/40 border-b border-slate-800 px-4 py-2.5 flex justify-between items-center">
          <span className="text-cyan-400 text-xs font-semibold uppercase tracking-widest">
            Pending Approvals
          </span>
          <span className="text-slate-500 text-xs">{approvals.length} items</span>
        </div>
        <div className="divide-y divide-slate-800/50 max-h-48 overflow-y-auto">
          {approvals.length === 0 ? (
            <div className="p-6 text-center text-slate-600 text-sm">
              No items pending approval ✅
            </div>
          ) : approvals.map(a => (
            <div
              key={a.filename}
              className="flex items-center justify-between px-4 py-2.5 hover:bg-slate-800/30"
            >
              <span className="font-mono text-sm text-cyan-400 truncate">⏱ {a.filename}</span>
              <span className={`text-xs flex-shrink-0 ml-2 ${ageClass(a.age_seconds)}`}>
                {a.age_human}
              </span>
            </div>
          ))}
        </div>
      </div>

      {data?.generated_at && (
        <p className="text-right text-slate-600 text-xs">
          Last updated: {new Date(data.generated_at).toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
