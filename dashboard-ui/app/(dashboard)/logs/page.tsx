'use client'

import { useState, useMemo } from 'react'
import { useDashboardContext } from '@/context/DashboardContext'

// ── Helpers ───────────────────────────────────────────────────────────────────

const RESULT_OPTIONS = [
  'All',
  'success',
  'error',
  'warning',
  'breach_detected',
  'notified',
  'in_progress',
  'approved',
  'rejected',
]

function resultClass(result: string) {
  const r = (result ?? '').toLowerCase()
  if (r === 'success')         return 'text-green-400'
  if (r === 'error')           return 'text-red-400'
  if (r === 'warning')         return 'text-amber-400'
  if (r === 'breach_detected') return 'text-red-400'
  if (r === 'notified')        return 'text-cyan-400'
  if (r === 'in_progress')     return 'text-cyan-400'
  if (r === 'approved')        return 'text-green-400'
  if (r === 'rejected')        return 'text-red-400'
  return 'text-slate-400'
}

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch { return '--:--:--' }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const { data } = useDashboardContext()
  const [search,       setSearch]       = useState('')
  const [resultFilter, setResultFilter] = useState('All')

  const logs = data?.logs ?? []

  const filtered = useMemo(() => {
    let out = logs
    if (search.trim()) {
      const kw = search.toLowerCase()
      out = out.filter(e =>
        (e.action_type ?? '').toLowerCase().includes(kw) ||
        (e.target      ?? '').toLowerCase().includes(kw) ||
        (e.result      ?? '').toLowerCase().includes(kw) ||
        (e.actor       ?? '').toLowerCase().includes(kw)
      )
    }
    if (resultFilter !== 'All') {
      out = out.filter(e => e.result === resultFilter)
    }
    return out
  }, [logs, search, resultFilter])

  return (
    <div className="p-6">

      {/* Header + controls */}
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <h1 className="text-lg font-bold text-white">Activity Logs</h1>

        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="text"
            placeholder="Search action, target, result…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg
              px-3 py-1.5 w-64 focus:outline-none focus:border-cyan-600
              placeholder-slate-600 transition-colors"
          />

          <select
            value={resultFilter}
            onChange={e => setResultFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg
              px-3 py-1.5 focus:outline-none focus:border-cyan-600 transition-colors"
          >
            {RESULT_OPTIONS.map(r => (
              <option key={r} value={r}>
                {r === 'All' ? 'All Results' : r}
              </option>
            ))}
          </select>

          <span className="text-slate-500 text-xs whitespace-nowrap">
            Showing {filtered.length} of {logs.length}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-600">
            {logs.length === 0 ? 'No log entries yet' : 'No entries match the current filter'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-800/40">
                  <th className="text-left px-4 py-2.5 text-slate-500 font-semibold uppercase tracking-wider w-28">Time</th>
                  <th className="text-left px-4 py-2.5 text-slate-500 font-semibold uppercase tracking-wider">Action Type</th>
                  <th className="text-left px-4 py-2.5 text-slate-500 font-semibold uppercase tracking-wider w-28">Actor</th>
                  <th className="text-left px-4 py-2.5 text-slate-500 font-semibold uppercase tracking-wider">Target</th>
                  <th className="text-left px-4 py-2.5 text-slate-500 font-semibold uppercase tracking-wider w-36">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {filtered.map((e, i) => (
                  <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-2 text-slate-500">{formatTime(e.timestamp)}</td>
                    <td className="px-4 py-2 text-slate-200">{e.action_type}</td>
                    <td className="px-4 py-2 text-slate-400">{e.actor}</td>
                    <td className="px-4 py-2 text-slate-300 max-w-xs truncate" title={e.target}>
                      {e.target}
                    </td>
                    <td className={`px-4 py-2 font-semibold ${resultClass(e.result)}`}>
                      {e.result}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
