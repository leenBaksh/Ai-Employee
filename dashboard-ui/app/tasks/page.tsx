'use client'

import { useDashboardContext } from '@/context/DashboardContext'
import TypeDot from '@/components/TypeDot'

function ageClass(s: number) {
  if (s > 86400) return 'text-red-400'
  if (s > 3600)  return 'text-amber-400'
  return 'text-green-400'
}

export default function TasksPage() {
  const { data } = useDashboardContext()
  const tasks = data?.tasks ?? []

  return (
    <div className="p-6">

      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <h1 className="text-lg font-bold text-white">Task Queue — Needs Action</h1>
        {tasks.length > 0 && (
          <span className="bg-slate-800 text-slate-200 text-xs font-bold px-2 py-0.5 rounded-full">
            {tasks.length}
          </span>
        )}
      </div>

      {/* Empty state */}
      {tasks.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-16 text-center">
          <div className="text-5xl mb-4">✅</div>
          <div className="text-green-400 font-semibold text-xl">Inbox Clear</div>
          <div className="text-slate-500 text-sm mt-1">No pending tasks</div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-800/40">
                <th className="text-left px-4 py-2.5 text-slate-500 font-semibold text-xs uppercase tracking-wider w-8" />
                <th className="text-left px-4 py-2.5 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  Filename
                </th>
                <th className="text-left px-4 py-2.5 text-slate-500 font-semibold text-xs uppercase tracking-wider w-28">
                  Type
                </th>
                <th className="text-left px-4 py-2.5 text-slate-500 font-semibold text-xs uppercase tracking-wider w-24">
                  Age
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {tasks.map(t => (
                <tr key={t.filename} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-center">
                    <TypeDot type={t.type} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-slate-200 text-xs">{t.filename}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-slate-400 text-xs">{t.type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-mono text-xs ${ageClass(t.age_seconds)}`}>
                      {t.age_human}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
