"use client"

import { useState } from "react"
import { ChevronDown, Database, Clock, Rows3 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { SqlQuery } from "@/lib/chat-types"

export function SqlQueryBlock({ query }: { query: SqlQuery }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="my-2 animate-fade-in-up">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-all duration-200",
          "bg-card/60 border-border/60 hover:bg-card hover:border-border",
          isExpanded && "bg-card border-border rounded-b-none"
        )}
      >
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Database className="h-3.5 w-3.5 text-primary" />
        </div>
        <span className="flex-1 font-medium text-foreground/90">
          {query.label}
        </span>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {query.duration && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {query.duration}
            </span>
          )}
          {query.rowsAffected !== undefined && (
            <span className="flex items-center gap-1">
              <Rows3 className="h-3 w-3" />
              {query.rowsAffected} rows
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
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
          <div className="rounded-b-lg border border-t-0 border-border/60 bg-sidebar p-3">
            <pre className="overflow-x-auto text-xs leading-relaxed">
              <code className="font-mono text-sidebar-foreground">
                {query.query}
              </code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}
