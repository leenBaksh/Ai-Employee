'use client'

import { useState, useEffect } from 'react'
import { useDashboardContext, TaskItem } from '@/context/DashboardContext'
import TypeDot from '@/components/TypeDot'

export default function DonePage() {
  const { data } = useDashboardContext()
  const [items,   setItems]   = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)

  // Full fetch when page loads
  useEffect(() => {
    fetch('/api/done')
      .then(r => r.json())
      .then((d: TaskItem[]) => { setItems(d); setLoading(false) })
      .catch(() => {
        // Fall back to SSE done_recent if available
        if (data?.done_recent?.length) setItems(data.done_recent)
        setLoading(false)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // When SSE fires a new payload, update if the full list hasn't loaded yet
  useEffect(() => {
    if (!loading && items.length === 0 && data?.done_recent?.length) {
      setItems(data.done_recent)
    }
  }, [data?.done_recent, loading, items.length])

  return (
    <div className="p-6">

      <div className="flex items-center gap-3 mb-5">
        <h1 className="text-lg font-bold text-white">Done Archive</h1>
        {!loading && (
          <span className="bg-slate-800 text-slate-300 text-xs font-bold px-2 py-0.5 rounded-full">
            {items.length} items
          </span>
        )}
      </div>

      {loading ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
          Loading…
        </div>
      ) : items.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-600">
          No completed items yet
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
                <th className="text-left px-4 py-2.5 text-slate-500 font-semibold text-xs uppercase tracking-wider w-32">
                  Completed
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {items.map(item => (
                <tr key={item.filename} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-center">
                    <TypeDot type={item.type} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-slate-300 text-xs">{item.filename}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-slate-500 text-xs">{item.age_human} ago</span>
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
