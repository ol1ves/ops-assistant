"use client"

import React from "react"

import { useState } from "react"
import {
  Plus,
  MessageSquare,
  Trash2,
  PanelLeftClose,
  PanelLeft,
  Search,
} from "lucide-react"
import { cn } from "@/lib/utils"
import type { Conversation } from "@/lib/chat-types"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ChatSidebarProps {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
  isCollapsed: boolean
  onToggleCollapse: () => void
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
  isCollapsed,
  onToggleCollapse,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("")
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setDeletingId(id)
    setTimeout(() => {
      onDelete(id)
      setDeletingId(null)
    }, 200)
  }

  // Group conversations by date
  const today = new Date()
  const todayStr = today.toDateString()
  const yesterdayStr = new Date(
    today.getTime() - 86400000
  ).toDateString()

  const groups: { label: string; items: Conversation[] }[] = []
  const todayItems = filtered.filter(
    (c) => new Date(c.updatedAt).toDateString() === todayStr
  )
  const yesterdayItems = filtered.filter(
    (c) => new Date(c.updatedAt).toDateString() === yesterdayStr
  )
  const olderItems = filtered.filter(
    (c) =>
      new Date(c.updatedAt).toDateString() !== todayStr &&
      new Date(c.updatedAt).toDateString() !== yesterdayStr
  )
  if (todayItems.length > 0) groups.push({ label: "Today", items: todayItems })
  if (yesterdayItems.length > 0)
    groups.push({ label: "Yesterday", items: yesterdayItems })
  if (olderItems.length > 0) groups.push({ label: "Previous", items: olderItems })

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex h-full flex-col bg-sidebar transition-all duration-300 ease-in-out border-r border-sidebar-border",
          isCollapsed ? "w-16" : "w-72"
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 pt-4 pb-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={onToggleCollapse}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {isCollapsed ? (
                  <PanelLeft className="h-5 w-5" />
                ) : (
                  <PanelLeftClose className="h-5 w-5" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {isCollapsed ? "Expand" : "Collapse"}
            </TooltipContent>
          </Tooltip>

          {!isCollapsed && (
            <span className="text-sm font-semibold text-sidebar-accent-foreground flex-1 truncate">
              Ops Assistant
            </span>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={onCreate}
                className={cn(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                  "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )}
                aria-label="New conversation"
              >
                <Plus className="h-5 w-5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side={isCollapsed ? "right" : "bottom"}>
              New chat
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Search */}
        {!isCollapsed && (
          <div className="px-3 pb-2">
            <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent/60 px-2.5 py-2 text-sm">
              <Search className="h-3.5 w-3.5 text-sidebar-foreground/50" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search conversations..."
                className="flex-1 bg-transparent text-xs text-sidebar-accent-foreground placeholder:text-sidebar-foreground/40 focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto dark-scrollbar px-2 pb-4">
          {isCollapsed ? (
            <div className="flex flex-col items-center gap-1 pt-2">
              {conversations.slice(0, 8).map((conv) => (
                <Tooltip key={conv.id}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => onSelect(conv.id)}
                      className={cn(
                        "flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
                        conv.id === activeId
                          ? "bg-sidebar-accent text-sidebar-primary"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      )}
                    >
                      <MessageSquare className="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-48">
                    {conv.title}
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {groups.map((group) => (
                <div key={group.label}>
                  <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                    {group.label}
                  </p>
                  <div className="flex flex-col gap-0.5">
                    {group.items.map((conv) => (
                      <div
                        key={conv.id}
                        className={cn(
                          "group relative",
                          deletingId === conv.id &&
                            "opacity-0 scale-95 transition-all duration-200"
                        )}
                        onMouseEnter={() => setHoveredId(conv.id)}
                        onMouseLeave={() => setHoveredId(null)}
                      >
                        <button
                          type="button"
                          onClick={() => onSelect(conv.id)}
                          className={cn(
                            "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-all duration-150",
                            conv.id === activeId
                              ? "bg-sidebar-accent text-sidebar-accent-foreground"
                              : "text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
                          )}
                        >
                          <MessageSquare className="h-4 w-4 shrink-0 opacity-60" />
                          <span className="flex-1 truncate text-[13px]">
                            {conv.title}
                          </span>
                        </button>
                        {hoveredId === conv.id && (
                          <button
                            type="button"
                            onClick={(e) => handleDelete(e, conv.id)}
                            className="absolute right-1.5 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-md bg-sidebar-accent text-sidebar-foreground/60 transition-colors hover:bg-destructive/20 hover:text-destructive"
                            aria-label={`Delete ${conv.title}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <p className="px-2 py-8 text-center text-xs text-sidebar-foreground/40">
                  {search ? "No conversations found" : "No conversations yet"}
                </p>
              )}
            </div>
          )}
        </div>
      </aside>
    </TooltipProvider>
  )
}
