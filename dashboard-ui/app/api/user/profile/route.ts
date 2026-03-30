import { NextResponse } from 'next/server'

export async function GET() {
  // In production, fetch from your auth system
  // For now, use environment variables or defaults
  return NextResponse.json({
    name: process.env.NEXT_PUBLIC_USER_NAME || 'Admin User',
    email: process.env.NEXT_PUBLIC_USER_EMAIL || 'admin@company.com',
    role: process.env.NEXT_PUBLIC_USER_ROLE || 'Administrator',
    avatar: null,
    preferences: {
      theme: 'dark',
      notifications: true,
      language: 'en'
    },
    stats: {
      tasks_completed: 147,
      approvals_given: 23,
      messages_sent: 89
    }
  })
}
