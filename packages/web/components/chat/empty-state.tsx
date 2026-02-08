"use client"

import { Users, Clock, MapPin, Locate, AlertTriangle } from "lucide-react"

const suggestions = [
  {
    icon: Users,
    title: "Who was in Zone A?",
    description: "Who was in Zone A between 2 and 3 PM yesterday?",
  },
  {
    icon: Clock,
    title: "Dwell time in loading dock",
    description: "How long did badge_12 stay in the loading dock today?",
  },
  {
    icon: MapPin,
    title: "Movement between zones",
    description: "Which entities moved from Lobby to Floor 2?",
  },
  {
    icon: Locate,
    title: "Where was forklift_3?",
    description: "Where was forklift_3 in the last 30 minutes?",
  },
  {
    icon: AlertTriangle,
    title: "Data quality",
    description: "Flag suspicious location jumps",
  },
]

export function EmptyState({
  onSuggestionClick,
}: {
  onSuggestionClick: (text: string) => void
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="flex flex-col items-center gap-6 max-w-lg">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
          <svg
            className="h-8 w-8 text-primary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
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
        <div className="text-center">
          <h2 className="text-xl font-semibold text-foreground text-balance">
            Operations Assistant
          </h2>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed text-balance">
            I can help you explore location tracking data, analyze foot traffic
            patterns, monitor zone activity, and answer questions about your
            retail store operations.
          </p>
        </div>
        <div className="grid w-full grid-cols-2 gap-2.5">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.title}
              type="button"
              onClick={() => onSuggestionClick(suggestion.description)}
              className="group flex flex-col gap-2 rounded-xl border border-border/60 bg-card/50 p-3.5 text-left transition-all duration-200 hover:bg-card hover:border-border hover:shadow-sm"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/8 group-hover:bg-primary/12 transition-colors">
                <suggestion.icon className="h-4 w-4 text-primary/80 group-hover:text-primary transition-colors" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground/90">
                  {suggestion.title}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                  {suggestion.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
