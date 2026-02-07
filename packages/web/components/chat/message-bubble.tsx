"use client"

import { User } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-types"
import { SqlQueryBlock } from "./sql-query-block"
import { TypingIndicator } from "./typing-indicator"

function formatTime(date: Date) {
  return new Date(date).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  if (message.isStreaming && !message.content) {
    return <TypingIndicator statusText={message.statusText} />
  }

  return (
    <div
      className={cn(
        "flex gap-3 animate-fade-in-up",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-secondary ring-1 ring-border"
            : "bg-primary/10 ring-1 ring-primary/20"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-foreground/70" />
        ) : (
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
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn("flex max-w-[75%] flex-col gap-1", isUser && "items-end")}
      >
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : "bg-card text-card-foreground border border-border/50 rounded-bl-md"
          )}
        >
          {message.content}
          {message.isStreaming && (
            <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current align-middle" />
          )}
        </div>

        {/* SQL Queries */}
        {message.sqlQueries && message.sqlQueries.length > 0 && (
          <div className="w-full mt-1">
            {message.sqlQueries.map((sq) => (
              <SqlQueryBlock key={sq.id} query={sq} />
            ))}
          </div>
        )}

        <span className="px-1 text-[10px] text-muted-foreground/60">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  )
}
