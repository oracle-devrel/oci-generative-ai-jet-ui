import { useEffect, useRef, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import {
  Send,
  Square,
  Loader2,
  ArrowUpRight,
  ArrowDownLeft,
  Database,
} from 'lucide-react'
import { Streamdown } from 'streamdown'

import { useAIChat } from '#/lib/ai-hook'
import type { ChatMessages } from '#/lib/ai-hook'

import './ai-chat.css'

function InitialLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <div className="text-center max-w-3xl mx-auto w-full">
        <h1 className="text-6xl font-bold mb-4 bg-linear-to-r from-orange-500 to-red-600 text-transparent bg-clip-text uppercase">
          <span className="text-white">TanStack</span> Chat
        </h1>
        <p className="text-gray-400 mb-6 w-2/3 mx-auto text-lg">
          You can ask me about anything, I might or might not have a good
          answer, but you can still ask.
        </p>
        {children}
      </div>
    </div>
  )
}

function ChattingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sticky bottom-0 left-0 right-0 bg-gray-900/80 backdrop-blur-sm border-t border-orange-500/10 z-10">
      <div className="w-full px-4 py-3">{children}</div>
    </div>
  )
}

function Messages({ messages }: { messages: ChatMessages }) {
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop =
        messagesContainerRef.current.scrollHeight
    }
  }, [messages])

  if (!messages.length) {
    return null
  }

  return (
    <div
      ref={messagesContainerRef}
      className="flex-1 overflow-y-auto pb-4 min-h-0"
    >
      <div className="max-w-3xl mx-auto w-full px-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`p-4 ${
              message.role === 'assistant'
                ? 'bg-linear-to-r from-orange-500/5 to-red-600/5'
                : 'bg-transparent'
            }`}
          >
            <div className="flex items-start gap-4 max-w-3xl mx-auto w-full">
              {message.role === 'assistant' ? (
                <div className="w-8 h-8 rounded-lg bg-linear-to-r from-orange-500 to-red-600 mt-2 flex items-center justify-center text-sm font-medium text-white flex-shrink-0">
                  AI
                </div>
              ) : (
                <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center text-sm font-medium text-white flex-shrink-0">
                  Y
                </div>
              )}
              <div className="flex-1 min-w-0">
                {message.parts.map((part, index) => {
                  if (part.type === 'text' && part.content) {
                    return (
                      <div
                        className="flex-1 min-w-0 prose dark:prose-invert max-w-none prose-sm"
                        key={index}
                      >
                        <Streamdown>{part.content}</Streamdown>
                      </div>
                    )
                  }
                  return null
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function OracleSidebar({ messages }: { messages: ChatMessages }) {
  const sidebarRef = useRef<HTMLDivElement>(null)

  const oracleCalls = messages.flatMap((message) =>
    message.parts
      .filter(
        (part) => part.type === 'tool-call' && part.name === 'execute_query',
      )
      .map((part) => {
        const p = part as any
        let question: string | undefined
        try {
          question = JSON.parse(p.arguments || '{}').question
        } catch {
          question = p.arguments
        }
        return {
          id: p.id as string,
          question,
          result: p.output?.result as string | undefined,
          pending: !p.output,
        }
      }),
  )

  useEffect(() => {
    if (sidebarRef.current) {
      sidebarRef.current.scrollTop = sidebarRef.current.scrollHeight
    }
  }, [oracleCalls])

  return (
    <div className="w-1/2 flex flex-col min-h-0 border-l border-orange-500/20">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-orange-500/20 bg-gray-800/50">
        <Database className="w-4 h-4 text-red-400" />
        <h2 className="text-sm font-semibold text-gray-200">
          Oracle Select AI
        </h2>
        {oracleCalls.length > 0 && (
          <span className="ml-auto text-xs text-gray-500">
            {oracleCalls.length} {oracleCalls.length === 1 ? 'query' : 'queries'}
          </span>
        )}
      </div>

      <div ref={sidebarRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {oracleCalls.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
            <Database className="w-8 h-8 opacity-30" />
            <p className="text-sm text-center">
              Oracle queries will appear here when the AI queries the shoe store
              database.
            </p>
          </div>
        ) : (
          oracleCalls.map((call) => (
            <div
              key={call.id}
              className="rounded-lg border border-orange-500/10 bg-gray-800/30 overflow-hidden"
            >
              <div className="px-3 py-2 border-b border-orange-500/10 bg-orange-500/5">
                <div className="flex items-center gap-2 text-xs text-orange-400 font-medium mb-1">
                  <ArrowUpRight className="w-3 h-3" />
                  QUERY
                </div>
                <p className="text-sm text-gray-200">{call.question}</p>
              </div>

              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium mb-1">
                  <ArrowDownLeft className="w-3 h-3" />
                  RESPONSE
                </div>
                {call.pending ? (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Querying Oracle...
                  </div>
                ) : (
                  <p className="text-sm text-gray-300 whitespace-pre-wrap">
                    {call.result}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function ChatPage() {
  const [input, setInput] = useState('')
  const { messages, sendMessage, isLoading, stop } = useAIChat()

  const Layout = messages.length ? ChattingLayout : InitialLayout

  return (
    <div className="relative flex h-screen bg-gray-900">
      <div className="w-1/2 flex flex-col min-h-0">
        <Messages messages={messages} />

        <Layout>
          <div className="space-y-3">
            {isLoading && (
              <div className="flex items-center justify-center">
                <button
                  onClick={stop}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <Square className="w-4 h-4 fill-current" />
                  Stop
                </button>
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (input.trim()) {
                  sendMessage(input)
                  setInput('')
                }
              }}
            >
              <div className="relative max-w-xl mx-auto">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type something clever..."
                  className="w-full rounded-lg border border-orange-500/20 bg-gray-800/50 pl-4 pr-12 py-3 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-transparent resize-none overflow-hidden shadow-lg"
                  rows={1}
                  style={{ minHeight: '44px', maxHeight: '200px' }}
                  disabled={isLoading}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement
                    target.style.height = 'auto'
                    target.style.height =
                      Math.min(target.scrollHeight, 200) + 'px'
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey && input.trim()) {
                      e.preventDefault()
                      sendMessage(input)
                      setInput('')
                    }
                  }}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-orange-500 hover:text-orange-400 disabled:text-gray-500 transition-colors focus:outline-none"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>
        </Layout>
      </div>

      <OracleSidebar messages={messages} />
    </div>
  )
}

export const Route = createFileRoute('/')({
  component: ChatPage,
})
