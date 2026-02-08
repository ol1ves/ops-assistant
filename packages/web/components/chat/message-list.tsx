"use client"

import { useEffect, useRef } from "react"
import type { Message } from "@/lib/chat-types"
import { MessageBubble } from "./message-bubble"

export function MessageList({ messages }: { messages: Message[] }) {
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return

    const scrollBottom = el.scrollHeight - el.clientHeight
    const atBottom = scrollBottom - el.scrollTop <= 80

    // Only auto-scroll when user is already near the bottom (so we don't fight manual scroll)
    if (!atBottom) return

    // Instant scroll instead of smooth to avoid hundreds of interrupted animations during streaming
    el.scrollTop = scrollBottom
  }, [messages])

  return (
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6 flex flex-col gap-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div />
      </div>
    </div>
  )
}
