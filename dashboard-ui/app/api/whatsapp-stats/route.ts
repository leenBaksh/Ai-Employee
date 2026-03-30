import { NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

export async function GET() {
  try {
    const vaultPath = process.env.VAULT_PATH || path.join(process.cwd(), '..', 'AI_Employee_Vault')
    const needsActionPath = path.join(vaultPath, 'Needs_Action')
    
    let messages = 0, urgent = 0, group = 0, unread = 0
    
    try {
      const files = await fs.readdir(needsActionPath)
      for (const file of files.filter(f => f.startsWith('WHATSAPP_'))) {
        messages++
        const content = await fs.readFile(path.join(needsActionPath, file), 'utf-8')
        if (content.includes('priority: high')) urgent++
        if (content.includes('chat_type: group')) group++
        if (content.includes('read_status: unread')) unread++
      }
    } catch {}
    
    let calls = 0
    try {
      const callLog = await fs.readFile(path.join(vaultPath, 'WhatsApp_Call_Log.md'), 'utf-8')
      calls = (callLog.match(/## /g) || []).length
    } catch {}
    
    return NextResponse.json({ messages, urgent, group, unread, calls, autoReply: true, dailyReport: true, webhookPort: 8089 })
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch WhatsApp stats' }, { status: 500 })
  }
}
