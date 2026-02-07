/**
 * API client for the Ops Assistant FastAPI backend.
 *
 * All requests are authenticated via Bearer token using the
 * NEXT_PUBLIC_API_KEY environment variable.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3000"
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? ""

// ---------------------------------------------------------------------------
// API response types (match FastAPI schemas)
// ---------------------------------------------------------------------------

export interface ApiConversationSummary {
  id: string
  created_at: string
  last_message: string
}

export interface ApiMessageSchema {
  role: string
  content: string | null
  timestamp: string
}

export interface ApiConversationDetail {
  id: string
  created_at: string
  last_message: string
  messages: ApiMessageSchema[]
}

export interface RateLimitStatus {
  limit: number
  remaining: number
  reset: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function authHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_KEY}`,
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`API error ${response.status}: ${body}`)
  }
  return response.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Conversation CRUD
// ---------------------------------------------------------------------------

export async function createConversation(): Promise<ApiConversationSummary> {
  const res = await fetch(`${API_URL}/conversations`, {
    method: "POST",
    headers: authHeaders(),
  })
  return handleResponse<ApiConversationSummary>(res)
}

export async function listConversations(): Promise<ApiConversationSummary[]> {
  const res = await fetch(`${API_URL}/conversations`, {
    headers: authHeaders(),
  })
  return handleResponse<ApiConversationSummary[]>(res)
}

export async function getConversation(
  id: string
): Promise<ApiConversationDetail> {
  const res = await fetch(`${API_URL}/conversations/${id}`, {
    headers: authHeaders(),
  })
  return handleResponse<ApiConversationDetail>(res)
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API error ${res.status}: ${body}`)
  }
}

// ---------------------------------------------------------------------------
// Rate limit status
// ---------------------------------------------------------------------------

export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const res = await fetch(`${API_URL}/rate-limit`, {
    headers: authHeaders(),
  })
  return handleResponse<RateLimitStatus>(res)
}

// ---------------------------------------------------------------------------
// Streaming chat (SSE via fetch)
// ---------------------------------------------------------------------------

export function chatStream(
  conversationId: string,
  message: string,
  signal?: AbortSignal
): Promise<Response> {
  return fetch(`${API_URL}/conversations/${conversationId}/chat/stream`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ message }),
    signal,
  })
}
