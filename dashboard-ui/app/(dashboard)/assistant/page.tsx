'use client'

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  role: 'user' | 'assistant'
  content: string
}

// ── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[70%] bg-cyan-900/60 border border-cyan-700/50 text-cyan-100 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex gap-2.5 max-w-[80%]">
        <div className="w-7 h-7 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
          🤖
        </div>
        <div className="bg-slate-800 border border-slate-700 text-slate-100 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    </div>
  )
}

// ── Typing Indicator ──────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-sm flex-shrink-0">
          🤖
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  )
}

// ── Welcome State ─────────────────────────────────────────────────────────────

function WelcomeState() {
  const suggestions = [
    'What tasks need attention?',
    'Any pending approvals?',
    'Show me recent activity',
    'Are there any SLA breaches?',
  ]

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center px-6 pb-8">
      <div className="text-6xl mb-4">🤖</div>
      <h2 className="text-white font-bold text-xl mb-2">AI Employee Assistant</h2>
      <p className="text-slate-400 text-sm mb-8 max-w-sm">
        Ask me anything about your AI Employee system — tasks, approvals, emails, health, or business activity.
      </p>
      <div className="grid grid-cols-2 gap-2 max-w-sm w-full">
        {suggestions.map(s => (
          <button
            key={s}
            data-suggestion={s}
            className="bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 text-slate-300 text-xs rounded-xl px-3 py-2.5 text-left transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  async function sendMessage(text: string) {
    if (!text.trim() || streaming) return
    setError(null)

    const userMsg: Message = { role: 'user', content: text.trim() }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setStreaming(true)

    // Placeholder for streaming response
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const res = await fetch('/api/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }))
        throw new Error(err.error ?? `HTTP ${res.status}`)
      }

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        accumulated += dec.decode(value, { stream: true })
        // Update the last assistant message with accumulated text
        setMessages(prev => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: accumulated }
          return copy
        })
      }

      // Ensure final decode flush
      const tail = dec.decode()
      if (tail) {
        accumulated += tail
        setMessages(prev => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: accumulated }
          return copy
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      // Remove the empty assistant placeholder
      setMessages(prev => prev.filter((_, i) => !(i === prev.length - 1 && prev[i].content === ''))
      )
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    sendMessage(input)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  // Handle suggestion button clicks via event delegation
  function handleWelcomeClick(e: React.MouseEvent<HTMLDivElement>) {
    const btn = (e.target as HTMLElement).closest('[data-suggestion]') as HTMLElement | null
    if (btn?.dataset.suggestion) {
      sendMessage(btn.dataset.suggestion)
    }
  }

  const showWelcome = messages.length === 0 && !streaming

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold text-white">Assistant</h1>
          <span className="text-xs bg-cyan-950 text-cyan-400 border border-cyan-800 px-2 py-0.5 rounded-full">
            via OpenRouter
          </span>
        </div>
        <p className="text-slate-500 text-xs mt-0.5">Vault-aware AI assistant</p>
      </div>

      {/* Message area */}
      <div
        className="flex-1 overflow-y-auto px-6 py-4"
        onClick={showWelcome ? handleWelcomeClick : undefined}
      >
        {showWelcome ? (
          <WelcomeState />
        ) : (
          <>
            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            {streaming && messages[messages.length - 1]?.content === '' && (
              <TypingIndicator />
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mb-2 bg-red-950/50 border border-red-800 text-red-300 text-xs px-4 py-2.5 rounded-xl flex items-center justify-between">
          <span>Error: {error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-3">✕</button>
        </div>
      )}

      {/* Input area */}
      <div className="flex-shrink-0 px-6 pb-6 pt-2">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <div className="flex-1 bg-slate-800 border border-slate-700 focus-within:border-cyan-600 rounded-xl transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about tasks, approvals, health… (Enter to send, Shift+Enter for newline)"
              rows={1}
              disabled={streaming}
              className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm px-4 py-3 resize-none outline-none max-h-32 overflow-y-auto disabled:opacity-50"
              style={{ height: 'auto' }}
              onInput={e => {
                const el = e.currentTarget
                el.style.height = 'auto'
                el.style.height = `${el.scrollHeight}px`
              }}
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || streaming}
            className="flex-shrink-0 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
          >
            {streaming ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span className="sr-only">Sending</span>
              </span>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            )}
          </button>
        </form>
        <p className="text-slate-600 text-xs mt-1.5 text-center">
          Responses use live vault data · History resets on page reload
        </p>
      </div>
    </div>
  )
}
