import type { Metadata } from 'next'
import './globals.css'
import { DashboardProvider } from '@/context/DashboardContext'

export const metadata: Metadata = {
  title: 'AI Employee — Live Dashboard',
  description: 'Platinum Tier — AI Employee Vault Live Dashboard',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <DashboardProvider>
          {children}
        </DashboardProvider>
      </body>
    </html>
  )
}
