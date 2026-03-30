'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface HeaderProps {
  title: string
  subtitle?: string
}

export default function Header({ title, subtitle }: HeaderProps) {
  const router = useRouter()
  const [currentTime, setCurrentTime] = useState<Date | null>(null)
  const [notifications, setNotifications] = useState(3)

  useEffect(() => {
    setCurrentTime(new Date())
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const handleSignOut = () => {
    router.push('/logout')
  }

  return (
    <header className="sticky top-0 z-20 bg-slate-900/80 backdrop-blur border-b border-slate-800">
      <div className="px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">{title}</h1>
          {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
        </div>

        <div className="flex items-center gap-4">
          {/* Time Display */}
          {currentTime && (
            <div className="text-right hidden md:block">
              <div className="text-sm font-mono text-cyan-400">{currentTime.toLocaleTimeString()}</div>
              <div className="text-xs text-slate-500">{currentTime.toLocaleDateString()}</div>
            </div>
          )}

          {/* Notifications */}
          <button className="relative p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition">
            <span className="text-xl">🔔</span>
            {notifications > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">{notifications}</span>
            )}
          </button>

          {/* Settings */}
          <button className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition">
            <span className="text-xl">⚙️</span>
          </button>

          {/* Sign Out Button */}
          <button 
            onClick={handleSignOut}
            className="flex items-center gap-2 px-4 py-2 bg-red-950/50 hover:bg-red-900/50 text-red-400 hover:text-red-300 rounded-lg transition border border-red-800/30"
          >
            <span className="text-lg">🚪</span>
            <span className="text-sm font-medium hidden lg:inline">Sign Out</span>
          </button>

          {/* User Avatar */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-sm font-bold cursor-pointer hover:ring-2 hover:ring-cyan-500 transition">AD</div>
        </div>
      </div>
    </header>
  )
}
