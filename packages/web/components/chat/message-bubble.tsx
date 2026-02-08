"use client"

import { useState, useEffect } from "react"
import { User, ChevronDown, Brain } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import type { Message } from "@/lib/chat-types"
import { SqlQueryBlock } from "./sql-query-block"
import { TypingIndicator } from "./typing-indicator"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

function formatTime(date: Date) {
  return new Date(date).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"
  const isStreaming = message.isStreaming ?? false
  const [reasoningManuallyOpen, setReasoningManuallyOpen] = useState(false)
  const reasoningOpen = isStreaming || reasoningManuallyOpen

  useEffect(() => {
    if (!isStreaming) setReasoningManuallyOpen(false)
  }, [isStreaming])

  const hasReasoningOrTools =
    (message.reasoningText && message.reasoningText.length > 0) ||
    (message.sqlQueries && message.sqlQueries.length > 0)

  if (
    message.isStreaming &&
    !message.content &&
    !hasReasoningOrTools
  ) {
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
          {isUser ? (
            message.content
          ) : !message.content && message.isStreaming ? (
            <span className="text-muted-foreground">Thinking...</span>
          ) : (
            <div className="chat-markdown">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => (
                    <p className="mb-2 last:mb-0">{children}</p>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold">{children}</strong>
                  ),
                  em: ({ children }) => (
                    <em className="italic">{children}</em>
                  ),
                  code: ({ className, children, ...rest }) =>
                    className ? (
                      <code
                        className="block overflow-x-auto rounded bg-muted px-2 py-1 font-mono text-[12px]"
                        {...rest}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className="rounded bg-muted/80 px-1 font-mono text-[12px]"
                        {...rest}
                      >
                        {children}
                      </code>
                    ),
                  pre: ({ children }) => (
                    <pre className="mb-2 overflow-x-auto rounded bg-muted p-2 font-mono text-[12px]">
                      {children}
                    </pre>
                  ),
                  ul: ({ children }) => (
                    <ul className="mb-2 list-disc pl-4 [&>li]:my-0.5">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="mb-2 list-decimal pl-4 [&>li]:my-0.5">
                      {children}
                    </ol>
                  ),
                  h1: ({ children }) => (
                    <h1 className="mb-1.5 mt-2 text-base font-semibold first:mt-0">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="mb-1 mt-2 text-[13px] font-semibold first:mt-0">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="mb-1 mt-1.5 text-sm font-semibold first:mt-0">
                      {children}
                    </h3>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-2 border-border pl-3 text-muted-foreground">
                      {children}
                    </blockquote>
                  ),
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline underline-offset-2 hover:no-underline"
                    >
                      {children}
                    </a>
                  ),
                  table: ({ children }) => (
                    <div className="mb-2 overflow-x-auto">
                      <table className="w-full border-collapse border border-border/50 text-left text-[12px]">
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-border/50 bg-muted/50 px-2 py-1 font-medium">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-border/50 px-2 py-1">
                      {children}
                    </td>
                  ),
                  tr: ({ children }) => (
                    <tr className="border-b border-border/30 last:border-b-0">
                      {children}
                    </tr>
                  ),
                }}
              >
                {message.content || ""}
              </ReactMarkdown>
            </div>
          )}
          {message.isStreaming && (
            <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-current align-middle" />
          )}
        </div>

        {/* Reasoning (chain of thought) */}
        {!isUser && message.reasoningText && (
          <Collapsible
            className="w-full mt-1"
            open={reasoningOpen}
            onOpenChange={setReasoningManuallyOpen}
          >
            <CollapsibleTrigger
              className={cn(
                "group flex w-full items-center gap-2 rounded-md border border-border/50 px-2.5 py-1.5 text-left text-xs transition-colors",
                "hover:bg-muted/50 hover:border-border/80"
              )}
            >
              <Brain className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="font-medium text-muted-foreground">
                {isStreaming ? "Reasoning" : "Reasoned"}
              </span>
              <ChevronDown className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-1 rounded-b-md border border-t-0 border-border/50 bg-muted/30 px-3 py-2">
                <pre className="whitespace-pre-wrap text-[11px] leading-relaxed text-muted-foreground font-sans">
                  {message.reasoningText}
                </pre>
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

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
