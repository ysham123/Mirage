"use client";

import { useEffect, useState } from "react";
import { Check, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ConsoleOverview } from "@/types/console";

interface TopBarProps {
  lastUpdated: Date | null;
  followLatest: boolean;
  // kept for forward-compat with the parent props contract
  overview: ConsoleOverview | null;
  onRefresh: () => void;
  onToggleFollowLatest: () => void;
}

function useTimeSince(date: Date | null) {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!date) return;
    const update = () => {
      const diff = Math.floor((Date.now() - date.getTime()) / 1000);
      if (diff < 10) setLabel("just now");
      else if (diff < 60) setLabel(`${diff}s`);
      else setLabel(`${Math.floor(diff / 60)}m`);
    };
    update();
    const id = setInterval(update, 5000);
    return () => clearInterval(id);
  }, [date]);

  return label;
}

export function TopBar({
  lastUpdated,
  followLatest,
  onRefresh,
  onToggleFollowLatest,
}: TopBarProps) {
  const timeSince = useTimeSince(lastUpdated);

  return (
    <header className="relative z-20 flex h-14 shrink-0 items-center justify-between border-b border-[var(--line)] bg-[rgba(10,10,10,0.85)] px-6 backdrop-blur-xl">
      {/* Wordmark */}
      <div className="flex items-center gap-3">
        {/* Logo glyph: chevron sliver in green */}
        <div className="relative flex size-6 items-center justify-center">
          <svg viewBox="0 0 24 24" className="size-6" aria-hidden>
            <path
              d="M4 12 L11 5 L11 9 L20 9 L20 15 L11 15 L11 19 Z"
              fill="var(--green)"
            />
          </svg>
        </div>
        <div className="flex items-baseline gap-2.5">
          <span className="font-display text-[19px] font-medium leading-none tracking-tight text-[var(--paper)]">
            Mirage
          </span>
          <span className="font-mono text-[10px] tracking-[0.04em] text-[var(--paper-mute)]">
            console
          </span>
        </div>
        <div className="ml-2 hidden items-center gap-2 border-l border-[var(--line)] pl-4 sm:flex">
          <span className="size-1.5 rounded-full bg-[var(--green)] shadow-[0_0_8px_var(--green-glow)]" aria-hidden />
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-soft)]">
            live
          </span>
          <span className="font-mono text-[10px] tracking-[0.04em] text-[var(--paper-faint)]">
            local · port 5100
          </span>
        </div>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-7">
        {timeSince && (
          <span className="font-mono text-[10px] tabular-nums text-[var(--paper-faint)]">
            sync · {timeSince}
          </span>
        )}

        <button
          type="button"
          onClick={onToggleFollowLatest}
          className={cn(
            "group flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors",
            followLatest ? "text-[var(--paper)]" : "text-[var(--paper-mute)] hover:text-[var(--paper-soft)]",
          )}
          aria-pressed={followLatest}
        >
          <span
            className={cn(
              "flex size-3.5 items-center justify-center border transition-colors",
              followLatest
                ? "border-[var(--green)] bg-[var(--green-soft)]"
                : "border-[var(--line-strong)] bg-transparent group-hover:border-[var(--paper-mute)]",
            )}
          >
            {followLatest && <Check className="size-2.5 text-[var(--green)]" strokeWidth={3} />}
          </span>
          follow latest
        </button>

        <button
          type="button"
          onClick={onRefresh}
          className="group flex items-center gap-2 border border-[var(--line-strong)] bg-transparent px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-soft)] transition-colors hover:border-[var(--green)]/60 hover:bg-[var(--green-faint)] hover:text-[var(--paper)]"
        >
          <RefreshCw className="size-3 transition-transform group-hover:rotate-180 duration-500" />
          refresh
        </button>
      </div>
    </header>
  );
}
