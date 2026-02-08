"use client"

export function TypingIndicator({ statusText }: { statusText?: string }) {
  return (
    <div className="flex items-start gap-3 animate-fade-in-up">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
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
      </div>
      <div className="flex flex-col gap-2 pt-1">
        {statusText && (
          <span className="text-xs font-medium text-muted-foreground">
            {statusText}
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <span className="typing-dot h-2 w-2 rounded-full bg-primary/60" />
          <span className="typing-dot h-2 w-2 rounded-full bg-primary/60" />
          <span className="typing-dot h-2 w-2 rounded-full bg-primary/60" />
        </div>
      </div>
    </div>
  )
}
