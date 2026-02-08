"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import type { Message, Conversation, SqlQuery } from "@/lib/chat-types"
import {
  createConversation as apiCreateConversation,
  listConversations as apiListConversations,
  getConversation as apiGetConversation,
  deleteConversation as apiDeleteConversation,
  chatStream,
  getRateLimitStatus as apiGetRateLimitStatus,
} from "@/lib/api"
import type { RateLimitStatus } from "@/lib/api"

function generateId() {
  return Math.random().toString(36).substring(2, 9)
}

// ---------------------------------------------------------------------------
// SSE event parsing helpers
// ---------------------------------------------------------------------------

interface SseEvent {
  event: string
  data: string
}

/**
 * Parse raw SSE text (which may contain multiple events separated by blank
 * lines) into structured events. Returns the remaining unparsed buffer so
 * incomplete trailing data can be carried over to the next chunk.
 */
function parseSseChunk(buffer: string): { events: SseEvent[]; remaining: string } {
  const events: SseEvent[] = []
  const blocks = buffer.split("\n\n")
  const remaining = blocks.pop()! // last element may be incomplete

  for (const block of blocks) {
    if (!block.trim()) continue
    let event = ""
    let data = ""
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) {
        event = line.slice(7)
      } else if (line.startsWith("data: ")) {
        data = line.slice(6)
      }
    }
    if (event || data) {
      events.push({ event, data })
    }
  }

  return { events, remaining }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSseChat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [rateLimit, setRateLimit] = useState<RateLimitStatus | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const streamedRef = useRef({ content: "", reasoningText: "" })

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null

  // -----------------------------------------------------------------------
  // Load conversation list on mount
  // -----------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const summaries = await apiListConversations()
        if (cancelled) return
        const convs: Conversation[] = summaries.map((s) => ({
          id: s.id,
          title: `Conversation from ${new Date(s.created_at).toLocaleDateString()}`,
          messages: [],
          createdAt: new Date(s.created_at),
          updatedAt: new Date(s.last_message),
        }))
        setConversations(convs)
      } catch {
        // If the API is not reachable, start with an empty list
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  // -----------------------------------------------------------------------
  // Load rate limit status on mount
  // -----------------------------------------------------------------------
  const refreshRateLimit = useCallback(async () => {
    try {
      const status = await apiGetRateLimitStatus()
      setRateLimit(status)
    } catch {
      // Ignore failures (e.g., API unavailable or missing auth)
    }
  }, [])

  useEffect(() => {
    refreshRateLimit()
  }, [refreshRateLimit])

  // -----------------------------------------------------------------------
  // Load full conversation when selected (if messages not yet loaded)
  // -----------------------------------------------------------------------
  const selectConversation = useCallback(
    async (id: string) => {
      setActiveId(id)
      const conv = conversations.find((c) => c.id === id)
      if (conv && conv.messages.length > 0) return // already loaded

      try {
        const detail = await apiGetConversation(id)
        const messages: Message[] = detail.messages.map((m) => ({
          id: generateId(),
          role: m.role as "user" | "assistant",
          content: m.content ?? "",
          timestamp: new Date(m.timestamp),
        }))

        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== id) return c
            const title =
              messages.find((m) => m.role === "user")?.content.slice(0, 40) ??
              c.title
            return { ...c, messages, title: title.length >= 40 ? title + "..." : title }
          })
        )
      } catch {
        // Could not load conversation details
      }
    },
    [conversations]
  )

  // -----------------------------------------------------------------------
  // Create conversation
  // -----------------------------------------------------------------------
  const createConversation = useCallback(async () => {
    try {
      const summary = await apiCreateConversation()
      const conv: Conversation = {
        id: summary.id,
        title: "New conversation",
        messages: [],
        createdAt: new Date(summary.created_at),
        updatedAt: new Date(summary.last_message),
      }
      setConversations((prev) => [conv, ...prev])
      setActiveId(summary.id)
      return summary.id
    } catch {
      // Fallback: create local-only conversation (will fail on send)
      const id = generateId()
      const conv: Conversation = {
        id,
        title: "New conversation",
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }
      setConversations((prev) => [conv, ...prev])
      setActiveId(id)
      return id
    }
  }, [])

  // -----------------------------------------------------------------------
  // Delete conversation
  // -----------------------------------------------------------------------
  const deleteConversation = useCallback(
    async (id: string) => {
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeId === id) {
        setConversations((prev) => {
          setActiveId(prev.length > 0 ? prev[0].id : null)
          return prev
        })
      }
      try {
        await apiDeleteConversation(id)
      } catch {
        // Best-effort server deletion
      }
    },
    [activeId]
  )

  // -----------------------------------------------------------------------
  // Send message (with SSE streaming)
  // -----------------------------------------------------------------------
  const sendMessage = useCallback(
    async (content: string) => {
      let convId = activeId

      // If no active conversation, create one on the server first
      if (!convId) {
        try {
          const summary = await apiCreateConversation()
          convId = summary.id
          const conv: Conversation = {
            id: convId,
            title: content.slice(0, 40) + (content.length > 40 ? "..." : ""),
            messages: [],
            createdAt: new Date(summary.created_at),
            updatedAt: new Date(summary.last_message),
          }
          setConversations((prev) => [conv, ...prev])
          setActiveId(convId)
        } catch {
          return // Cannot create conversation
        }
      }

      // Add user message optimistically
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content,
        timestamp: new Date(),
      }

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c
          return {
            ...c,
            title:
              c.messages.length === 0
                ? content.slice(0, 40) + (content.length > 40 ? "..." : "")
                : c.title,
            messages: [...c.messages, userMsg],
            updatedAt: new Date(),
          }
        })
      )

      // Prepare the assistant message placeholder
      const assistantId = generateId()
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
        statusText: "Thinking...",
        sqlQueries: [],
      }

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== convId) return c
          return {
            ...c,
            messages: [...c.messages, assistantMsg],
            updatedAt: new Date(),
          }
        })
      )

      // Start streaming
      const abortController = new AbortController()
      abortControllerRef.current = abortController
      streamedRef.current = { content: "", reasoningText: "" }
      setIsStreaming(true)

      try {
        const response = await chatStream(convId, content, abortController.signal)

        if (!response.ok) {
          if (response.status === 429) {
            setConversations((prev) =>
              prev.map((c) => {
                if (c.id !== convId) return c
                return {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          content:
                            "Rate limit reached. Please wait for the reset and try again.",
                          isStreaming: false,
                          statusText: undefined,
                        }
                      : m
                  ),
                }
              })
            )
            return
          }

          const errorText = await response.text()
          throw new Error(`API error ${response.status}: ${errorText}`)
        }

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const { events, remaining } = parseSseChunk(buffer)
          buffer = remaining

          for (const sseEvent of events) {
            if (abortController.signal.aborted) break

            let parsed: Record<string, unknown>
            try {
              parsed = JSON.parse(sseEvent.data)
            } catch {
              continue
            }

            const eventType = (parsed.type as string) || sseEvent.event

            switch (eventType) {
              case "status": {
                const statusText = (parsed.status as string) ?? "Processing..."
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? { ...m, statusText }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "reasoning_token": {
                const token = (parsed.token as string) ?? ""
                streamedRef.current.reasoningText += token
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              reasoningText: (m.reasoningText ?? "") + token,
                            }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "reasoning": {
                const content = (parsed.content as string) ?? ""
                // Accumulate across multiple tool-call rounds; do not replace (last round may be empty)
                const prevReasoning = streamedRef.current.reasoningText
                streamedRef.current.reasoningText = prevReasoning
                  ? prevReasoning + "\n\n" + content
                  : content
                const accumulated = streamedRef.current.reasoningText
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? { ...m, reasoningText: accumulated }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "tool_call": {
                const query = parsed.query as string
                const newSqlQuery: SqlQuery = {
                  id: generateId(),
                  query,
                  label: "Executing query",
                }
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              sqlQueries: [...(m.sqlQueries || []), newSqlQuery],
                            }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "tool_result": {
                const query = parsed.query as string
                const success = parsed.success as boolean
                const result = parsed.result as string | undefined
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) => {
                        if (m.id !== assistantId) return m
                        return {
                          ...m,
                          sqlQueries: (m.sqlQueries || []).map((sq) =>
                            sq.query === query
                              ? {
                                  ...sq,
                                  label: success
                                    ? "Queried database"
                                    : "Query failed",
                                  success,
                                  result,
                                }
                              : sq
                          ),
                        }
                      }),
                    }
                  })
                )
                break
              }

              case "token": {
                const token = parsed.token as string
                streamedRef.current.content += token
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              content: m.content + token,
                              statusText: undefined,
                            }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "done": {
                const finalContent =
                  typeof parsed.response === "string" ? parsed.response : ""
                // Main bubble shows interpretation only; use streamed interpretation tokens if done is empty, never reasoning
                const keptContent =
                  finalContent.length > 0
                    ? finalContent
                    : streamedRef.current.content.length > 0
                      ? streamedRef.current.content
                      : "(No summary was generated. See reasoning and query results above.)"
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              content: keptContent,
                              isStreaming: false,
                              statusText: undefined,
                            }
                          : m
                      ),
                    }
                  })
                )
                break
              }

              case "error": {
                const errorMessage = parsed.message as string
                const isContextLength =
                  errorMessage.includes("context_length_exceeded") ||
                  errorMessage.includes("too long")
                const fallbackMessage = isContextLength
                  ? "Conversation is too long. Please start a new conversation."
                  : `Error: ${errorMessage}`
                setConversations((prev) =>
                  prev.map((c) => {
                    if (c.id !== convId) return c
                    return {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              content: m.content || fallbackMessage,
                              isStreaming: false,
                              statusText: undefined,
                            }
                          : m
                      ),
                    }
                  })
                )
                break
              }
            }
          }
        }

        // Ensure the message is finalized even if no explicit "done" event
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id !== convId) return c
            return {
              ...c,
              messages: c.messages.map((m) =>
                m.id === assistantId && m.isStreaming
                  ? { ...m, isStreaming: false, statusText: undefined }
                  : m
              ),
            }
          })
        )
      } catch (err) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          // Set error on the assistant message
          setConversations((prev) =>
            prev.map((c) => {
              if (c.id !== convId) return c
              return {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content:
                          m.content ||
                          "Failed to get a response. Please try again.",
                        isStreaming: false,
                        statusText: undefined,
                      }
                    : m
                ),
              }
            })
          )
        }
      } finally {
        setIsStreaming(false)
        abortControllerRef.current = null
        await refreshRateLimit()
      }
    },
    [activeId, refreshRateLimit]
  )

  // -----------------------------------------------------------------------
  // Stop streaming
  // -----------------------------------------------------------------------
  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
    setConversations((prev) =>
      prev.map((c) => ({
        ...c,
        messages: c.messages.map((m) =>
          m.isStreaming ? { ...m, isStreaming: false, statusText: undefined } : m
        ),
      }))
    )
  }, [])

  return {
    conversations,
    activeConversation,
    activeId,
    isStreaming,
    setActiveId: selectConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    stopStreaming,
    rateLimit,
  }
}
