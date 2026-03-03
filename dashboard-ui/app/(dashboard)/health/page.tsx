'use client'

import { useDashboardContext, Agent } from '@/context/DashboardContext'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatAgo(iso: string) {
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60)    return `${Math.round(diff)}s ago`
    if (diff < 3600)  return `${Math.round(diff / 60)}m ago`
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
    return `${Math.round(diff / 86400)}d ago`
  } catch { return 'unknown' }
}

function formatTimestamp(iso: string) {
  try { return new Date(iso).toLocaleString() }
  catch { return iso }
}

// ── Agent Card ────────────────────────────────────────────────────────────────

function AgentCard({ agent }: { agent: Agent }) {
  const isOnline  = agent.status === 'online'
  const isOffline = agent.status === 'offline'

  const borderClass = isOnline
    ? 'border-green-700/70'
    : isOffline
    ? 'border-red-700/70'
    : 'border-slate-700'

  const dotClass = isOnline
    ? 'bg-green-400 animate-pulse'
    : isOffline
    ? 'bg-red-500'
    : 'bg-slate-600'

  const badgeClass = isOnline
    ? 'bg-green-950 text-green-400 border-green-800'
    : isOffline
    ? 'bg-red-950 text-red-400 border-red-800'
    : 'bg-slate-800 text-slate-400 border-slate-700'

  const statusLabel =
    agent.status === 'never_seen' ? 'NEVER SEEN' : agent.status.toUpperCase()

  return (
    <div className={`bg-slate-900 border-2 rounded-2xl p-6 flex-1 min-w-72 max-w-lg ${borderClass}`}>

      {/* Card header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-white font-bold text-2xl">{agent.agent_id}</h2>
        <div className="flex items-center gap-2.5">
          <span className={`w-3 h-3 rounded-full ${dotClass}`} />
          <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${badgeClass}`}>
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-2.5 text-sm">
        {agent.role && (
          <Row label="Role" value={agent.role} mono />
        )}
        <Row
          label="Last Seen"
          value={agent.timestamp ? formatAgo(agent.timestamp) : 'Never'}
          mono
        />
        {agent.timestamp && (
          <Row
            label="Timestamp"
            value={formatTimestamp(agent.timestamp)}
            mono
            muted
          />
        )}
        {agent.vault_path && (
          <Row label="Vault" value={agent.vault_path} mono muted truncate />
        )}

        {/* Counters */}
        {(agent.needs_action_count !== undefined || agent.pending_approval_count !== undefined) && (
          <div className="border-t border-slate-800 pt-3 mt-3 flex gap-6">
            {agent.needs_action_count !== undefined && (
              <div>
                <div className="text-white font-extrabold text-2xl">
                  {agent.needs_action_count}
                </div>
                <div className="text-slate-500 text-xs uppercase tracking-wider mt-0.5">
                  Needs Action
                </div>
              </div>
            )}
            {agent.pending_approval_count !== undefined && (
              <div>
                <div className="text-cyan-400 font-extrabold text-2xl">
                  {agent.pending_approval_count}
                </div>
                <div className="text-slate-500 text-xs uppercase tracking-wider mt-0.5">
                  Pending Approval
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Row({
  label, value, mono, muted, truncate,
}: {
  label: string
  value: string
  mono?: boolean
  muted?: boolean
  truncate?: boolean
}) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-500 flex-shrink-0">{label}</span>
      <span
        className={`text-right ${mono ? 'font-mono text-xs' : ''} ${muted ? 'text-slate-400' : 'text-slate-200'}
          ${truncate ? 'truncate max-w-48' : ''}`}
        title={truncate ? value : undefined}
      >
        {value}
      </span>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

const PLACEHOLDER_AGENTS: Agent[] = [
  { agent_id: 'local-01', status: 'never_seen', timestamp: null },
]

export default function HealthPage() {
  const { data } = useDashboardContext()
  const agents = data?.health?.length ? data.health : PLACEHOLDER_AGENTS

  return (
    <div className="p-6">
      <h1 className="text-lg font-bold text-white mb-5">Agent Health</h1>

      <div className="flex flex-wrap gap-5">
        {agents.map(agent => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))}
      </div>
    </div>
  )
}
