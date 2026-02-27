'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useDashboardContext } from '@/context/DashboardContext'

interface NavItem {
  href: string
  label: string
  icon: string
  badgeKey?: 'needs_action' | 'pending_approval'
}

const NAV: NavItem[] = [
  { href: '/',           label: 'Overview',   icon: '⚡' },
  { href: '/tasks',      label: 'Tasks',       icon: '📥', badgeKey: 'needs_action' },
  { href: '/approvals',  label: 'Approvals',   icon: '⏱',  badgeKey: 'pending_approval' },
  { href: '/logs',       label: 'Logs',        icon: '📋' },
  { href: '/done',       label: 'Done',        icon: '✅' },
  { href: '/health',     label: 'Health',      icon: '💚' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { data } = useDashboardContext()

  const badge = (key: 'needs_action' | 'pending_approval') =>
    (data?.stats?.[key] ?? 0) > 0 ? data!.stats[key] : null

  return (
    <aside className="w-48 bg-slate-950 border-r border-slate-800 flex-shrink-0 flex flex-col">
      <nav className="flex-1 py-3 space-y-0.5">
        {NAV.map(item => {
          const isActive = pathname === item.href
          const count = item.badgeKey ? badge(item.badgeKey) : null

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between mx-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                ${isActive
                  ? 'bg-cyan-950/50 text-cyan-300 border-l-2 border-cyan-500 pl-2.5'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/60 border-l-2 border-transparent'
                }`}
            >
              <span className="flex items-center gap-2.5">
                <span className="text-base leading-none">{item.icon}</span>
                {item.label}
              </span>

              {count !== null && (
                <span
                  className={`text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center
                    ${isActive
                      ? 'bg-cyan-800 text-cyan-200'
                      : 'bg-slate-800 text-slate-400'
                    }`}
                >
                  {count}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800">
        <div className="text-slate-600 text-xs text-center">AI Employee v0.4</div>
      </div>
    </aside>
  )
}
