export interface SqlQuery {
  id: string
  query: string
  label: string
  duration?: string
  rowsAffected?: number
  success?: boolean
  result?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  sqlQueries?: SqlQuery[]
  reasoningText?: string
  isStreaming?: boolean
  statusText?: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}
