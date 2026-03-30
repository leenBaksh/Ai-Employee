'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface NavItem {
  href: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { href: '/dashboard', label: 'Overview', icon: '📊' },
  { href: '/dashboard/whatsapp', label: 'WhatsApp', icon: '📱' },
  { href: '/dashboard/gmail', label: 'Gmail', icon: '📧' },
  { href: '/dashboard/linkedin', label: 'LinkedIn', icon: '💼' },
  { href: '/dashboard/tasks', label: 'Tasks', icon: '📋' },
  { href: '/dashboard/approvals', label: 'Approvals', icon: '🔐' },
  { href: '/dashboard/done', label: 'Done', icon: '✅' },
  { href: '/dashboard/logs', label: 'Logs', icon: '📝' },
  { href: '/dashboard/health', label: 'Health', icon: '🏥' },
  { href: '/dashboard/automation', label: 'Automation', icon: '⚡' },
  { href: '/dashboard/settings', label: 'Settings', icon: '⚙️' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-900 border-r border-slate-800 overflow-y-auto custom-scrollbar">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xl font-bold text-white">
            AI
          </div>
          <div>
            <h1 className="font-bold text-slate-100 whitespace-nowrap">AI Employee</h1>
            <p className="text-xs text-slate-400">Platinum</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2 flex-shrink-0">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? 'bg-cyan-950/50 text-cyan-400 border border-cyan-800/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Status */}
      <div className="p-4 border-t border-slate-800 bg-slate-900 flex-shrink-0 mt-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-slate-300 whitespace-nowrap">System Online</span>
        </div>
      </div>
    </aside>
  )
}
