"use client"

import { useState } from "react"
import { ChevronDown, Database, Clock, Rows3 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { SqlQuery } from "@/lib/chat-types"

function parseResult(resultJson: string | undefined): {
  results?: unknown[][]
  error?: string
} | null {
  if (!resultJson) return null
  try {
    return JSON.parse(resultJson) as { results?: unknown[][]; error?: string }
  } catch {
    return null
  }
}

function ResultDisplay({ result }: { result: string | undefined }) {
  const parsed = parseResult(result)
  if (!parsed) return null

  if (parsed.error) {
    return (
      <div className="mt-2">
        <p className="text-[11px] font-medium text-destructive/90">Error</p>
        <pre className="mt-0.5 overflow-x-auto rounded bg-destructive/10 px-2 py-1.5 text-[11px] text-destructive">
          {parsed.error}
        </pre>
      </div>
    )
  }

  const rows = parsed.results ?? []
  if (rows.length === 0) {
    return (
      <p className="mt-2 text-[11px] text-muted-foreground">
        No rows returned.
      </p>
    )
  }

  return (
    <div className="mt-2">
      <p className="text-[11px] font-medium text-muted-foreground">Result</p>
      <div className="mt-0.5 max-h-48 overflow-auto rounded border border-border/50 bg-muted/20">
        <table className="w-full border-collapse text-[11px]">
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className={cn(
                  "border-b border-border/30 last:border-b-0",
                  i % 2 === 0 ? "bg-transparent" : "bg-muted/10"
                )}
              >
                {row.map((cell, j) => (
                  <td key={j} className="px-2 py-1 font-mono text-foreground/90">
                    {cell === null || cell === undefined ? "—" : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SqlQueryBlock({ query }: { query: SqlQuery }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const hasResult = !!query.result

  return (
    <div className="my-1 animate-fade-in-up">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "group flex w-full items-center gap-2 rounded-md border border-border/50 px-2.5 py-1.5 text-left text-xs transition-colors",
          "hover:bg-muted/50 hover:border-border/80",
          !query.success && "border-destructive/40 text-destructive/90",
          isExpanded && "rounded-b-none border-border/80 bg-muted/30"
        )}
      >
        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/10">
          <Database className="h-3 w-3 text-primary" />
        </div>
        <span
          className={cn(
            "flex-1 font-medium",
            query.success ? "text-foreground/80" : "text-destructive/90"
          )}
        >
          {query.label}
        </span>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          {query.duration && (
            <span className="flex items-center gap-0.5">
              <Clock className="h-2.5 w-2.5" />
              {query.duration}
            </span>
          )}
          {query.rowsAffected !== undefined && (
            <span className="flex items-center gap-0.5">
              <Rows3 className="h-2.5 w-2.5" />
              {query.rowsAffected} rows
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-200",
            isExpanded && "rotate-180"
          )}
        />
      </button>
      <div
        className={cn(
          "grid transition-all duration-200 ease-in-out",
          isExpanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <div className="rounded-b-md border border-t-0 border-border/50 bg-muted/20 px-2.5 py-2">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Query
              </p>
              <pre className="mt-0.5 overflow-x-auto text-[11px] leading-relaxed">
                <code className="font-mono text-foreground/90">
                  {query.query}
                </code>
              </pre>
            </div>
            {hasResult && <ResultDisplay result={query.result} />}
          </div>
        </div>
      </div>
    </div>
  )
}
