'use client'

import { useState, useEffect } from 'react'

interface UserProfile {
  name: string
  email: string
  avatar?: string
  role: string
}

export default function UserProfile() {
  const [user, setUser] = useState<UserProfile>({
    name: 'Admin User',
    email: 'admin@company.com',
    role: 'Administrator'
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch user profile from API
    fetch('/api/user/profile')
      .then(r => r.json())
      .then(data => setUser(data))
      .catch(() => {
        // Use environment variable or default
        setUser({
          name: process.env.NEXT_PUBLIC_USER_NAME || 'Admin User',
          email: process.env.NEXT_PUBLIC_USER_EMAIL || 'admin@company.com',
          role: process.env.NEXT_PUBLIC_USER_ROLE || 'Administrator'
        })
      })
      .finally(() => setLoading(false))
  }, [])

  const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  return (
    <div className="p-4 border-t border-slate-800">
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center text-sm font-bold text-white shadow-lg">
          {initials}
        </div>
        
        {/* User Info */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-slate-700 rounded w-24"></div>
              <div className="h-3 bg-slate-700 rounded w-32"></div>
            </div>
          ) : (
            <>
              <div className="text-sm font-semibold text-slate-200 truncate">
                {user.name}
              </div>
              <div className="text-xs text-slate-500 truncate" title={user.email}>
                {user.email}
              </div>
              <div className="text-xs text-purple-400 mt-0.5">
                {user.role}
              </div>
            </>
          )}
        </div>

        {/* Dropdown Menu */}
        <button className="text-slate-400 hover:text-slate-200 transition p-1">
          <span className="text-lg">⋮</span>
        </button>
      </div>

      {/* Quick Stats */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-cyan-400">30</div>
          <div className="text-xs text-slate-500">Tasks</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-green-400">5</div>
          <div className="text-xs text-slate-500">Done</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-amber-400">2</div>
          <div className="text-xs text-slate-500">Pending</div>
        </div>
      </div>
    </div>
  )
}
