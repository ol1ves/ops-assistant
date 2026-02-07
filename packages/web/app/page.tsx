"use client"

import { useState } from "react"
import { ChatSidebar } from "@/components/chat/chat-sidebar"
import { MessageList } from "@/components/chat/message-list"
import { ChatInput } from "@/components/chat/chat-input"
import { EmptyState } from "@/components/chat/empty-state"
import { useSseChat } from "@/hooks/use-sse-chat"

export default function Page() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const {
    conversations,
    activeConversation,
    activeId,
    isStreaming,
    setActiveId,
    createConversation,
    deleteConversation,
    sendMessage,
    stopStreaming,
    rateLimit,
  } = useSseChat()

  const handleSend = (text: string) => {
    sendMessage(text)
  }

  const hasMessages =
    activeConversation && activeConversation.messages.length > 0

  const resetLabel = rateLimit?.reset
    ? (() => {
        const resetDate = new Date(rateLimit.reset)
        if (Number.isNaN(resetDate.getTime())) return null
        return resetDate.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      })()
    : null

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={createConversation}
        onDelete={deleteConversation}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-border/40 bg-background/80 backdrop-blur-sm px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
              <svg
                className="h-4 w-4 text-primary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.64 0 8.577 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.64 0-8.577-3.007-9.963-7.178z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-foreground">
                {activeConversation?.title ?? "Operations Assistant"}
              </h1>
              <p className="text-[11px] text-muted-foreground">
                {isStreaming ? (
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                    Processing
                  </span>
                ) : (
                  "Ready"
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {rateLimit && (
              <div className="flex items-center gap-1.5 rounded-md border border-border/60 bg-muted/30 px-2 py-1 text-[11px] text-muted-foreground">
                <span className="font-medium text-foreground">
                  {rateLimit.remaining}
                </span>
                <span>/ {rateLimit.limit} left</span>
                {resetLabel && (
                  <span className="text-muted-foreground/60">
                    · resets {resetLabel}
                  </span>
                )}
              </div>
            )}
            {activeConversation && (
              <span className="text-[11px] text-muted-foreground/50">
                {activeConversation.messages.length} messages
              </span>
            )}
          </div>
        </header>

        {/* Messages or Empty State */}
        {hasMessages ? (
          <MessageList messages={activeConversation.messages} />
        ) : (
          <EmptyState onSuggestionClick={handleSend} />
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          onStop={stopStreaming}
          isStreaming={isStreaming}
          disabled={false}
        />
      </main>
    </div>
  )
}
