'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function LogoutPage() {
  const router = useRouter()
  const [countdown, setCountdown] = useState(5)
  const [loggingOut, setLoggingOut] = useState(false)

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          handleLogout()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const handleLogout = async () => {
    if (loggingOut) return
    setLoggingOut(true)
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
      router.push('/login')
    } catch {
      router.push('/login')
    }
  }

  const handleCancel = () => router.back()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center text-3xl font-bold text-white shadow-2xl">👋</div>
          <h1 className="text-3xl font-bold text-white mb-2">Sign Out</h1>
          <p className="text-slate-400">Ending your session</p>
        </div>

        <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800 p-8 shadow-2xl">
          <div className="text-center mb-8">
            <div className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-red-400 to-orange-400 mb-4 animate-pulse">{countdown}</div>
            <p className="text-slate-300">{countdown > 0 ? 'Redirecting to login...' : 'Signing out...'}</p>
          </div>

          <div className="w-full bg-slate-800 rounded-full h-2 mb-8 overflow-hidden">
            <div className="bg-gradient-to-r from-red-500 to-orange-500 h-2 rounded-full transition-all duration-1000 ease-linear" style={{ width: `${(countdown / 5) * 100}%` }} />
          </div>

          <div className="space-y-3">
            <button onClick={handleLogout} disabled={loggingOut} className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-semibold py-3 px-6 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50">
              {loggingOut ? (<><div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" /><span>Signing out...</span></>) : (<><span>🚪</span><span>Sign Out Now</span></>)}
            </button>
            <button onClick={handleCancel} disabled={loggingOut} className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-3 px-6 rounded-xl transition-all disabled:opacity-50">Cancel</button>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-800 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Session Status</span><span className="text-green-400">● Active</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Security</span><span className="text-cyan-400">Encrypted</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Auto-logout</span><span className="text-amber-400">{countdown}s</span></div>
          </div>
        </div>
      </div>
    </div>
  )
}
