"use client";

import { useEffect, useState } from "react";
import { Check, Layers3, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ConsoleOverview } from "@/types/console";

interface TopBarProps {
  lastUpdated: Date | null;
  followLatest: boolean;
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
      else if (diff < 60) setLabel(`${diff}s ago`);
      else setLabel(`${Math.floor(diff / 60)}m ago`);
    };
    update();
    const id = setInterval(update, 5000);
    return () => clearInterval(id);
  }, [date]);

  return label;
}

export function TopBar({ lastUpdated, followLatest, overview, onRefresh, onToggleFollowLatest }: TopBarProps) {
  const timeSince = useTimeSince(lastUpdated);
  const riskyRuns = overview?.summary.riskyRuns ?? 0;
  const totalRuns = overview?.summary.totalRuns ?? 0;

  const updatedAt = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header className="flex h-11 shrink-0 items-center justify-between border-b border-white/[0.07] bg-[rgba(3,6,12,0.92)] px-4 backdrop-blur-xl">
      {/* Identity */}
      <div className="flex items-center gap-3">
        <Layers3 className="size-3.5 text-white/30" />
        <div className="flex items-center gap-2">
          <span className="relative flex size-1.5 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-green-500 opacity-50" />
            <span className="size-1.5 rounded-full bg-green-500" />
          </span>
          <span className="text-[13px] font-semibold text-white">Mirage</span>
        </div>
        <span className="text-white/15">|</span>
        <span className="text-[13px] text-white/50">Action Review</span>
      </div>

      {/* Center: timestamp */}
      {updatedAt && (
        <span className="text-[11px] text-white/30">Updated {updatedAt}</span>
      )}

      {/* Right: controls */}
      <div className="flex items-center gap-5">
        {totalRuns > 0 && (
          <div className="flex items-center gap-3 text-[11px] text-white/30">
            <span>{totalRuns} runs</span>
            {riskyRuns > 0 && (
              <span className="text-orange-400/70">{riskyRuns} risky</span>
            )}
          </div>
        )}

        {timeSince && (
          <span className="text-[11px] text-white/30">{timeSince}</span>
        )}

        <button
          className={cn(
            "flex items-center gap-1.5 text-[11px] transition-colors",
            followLatest ? "text-white/80" : "text-white/30 hover:text-white/50",
          )}
          onClick={onToggleFollowLatest}
          type="button"
        >
          <span
            className={cn(
              "flex size-3 items-center justify-center rounded-[2px] border transition-colors",
              followLatest
                ? "border-green-500 bg-green-500/25"
                : "border-white/20 bg-transparent",
            )}
          >
            {followLatest && <Check className="size-2 text-green-400" strokeWidth={3} />}
          </span>
          follow latest
        </button>

        <button
          className="flex items-center gap-1.5 border border-white/[0.1] bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white"
          onClick={onRefresh}
          type="button"
        >
          <RefreshCw className="size-2.5" />
          Refresh
        </button>
      </div>
    </header>
  );
}
