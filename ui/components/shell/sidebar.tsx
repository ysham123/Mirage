"use client";

import type { RefObject } from "react";
import { Clock3, ShieldCheck, ShieldX, Sparkles, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ConsoleOverview, QueueFilter } from "@/types/console";

interface SidebarProps {
  overview: ConsoleOverview | null;
  selectedRunId: string | null;
  filter: QueueFilter;
  search: string;
  collapsed?: boolean;
  className?: string;
  searchRef?: RefObject<HTMLInputElement | null>;
  onSearchChange: (value: string) => void;
  onFilterChange: (value: QueueFilter) => void;
  onSelectRun: (runId: string) => void;
}

const filters: Array<{ value: QueueFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "risky", label: "Risky" },
  { value: "allowed", label: "Allowed" },
  { value: "unmatched_route", label: "Unmatched" },
];

function outcomeTone(outcome: string) {
  if (outcome === "allowed") {
    return "success";
  }
  if (outcome === "config_error") {
    return "critical";
  }
  return "warning";
}

export function Sidebar({
  overview,
  selectedRunId,
  filter,
  search,
  collapsed,
  className,
  searchRef,
  onSearchChange,
  onFilterChange,
  onSelectRun,
}: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col gap-4 border-r border-white/10 bg-[rgba(5,11,18,.72)] px-4 py-4 backdrop-blur-xl transition-all duration-300",
        collapsed ? "pointer-events-none w-0 overflow-hidden border-transparent px-0 py-0 opacity-0" : "w-full",
        className,
      )}
    >
      <Card className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Agent Status</p>
            <h2 className="mt-2 text-xl font-semibold tracking-[-0.04em] text-white">
              {overview ? overview.summary.totalRuns : 0} trace-backed runs
            </h2>
          </div>
          <div className="rounded-full border border-white/10 bg-white/6 p-2 text-[var(--accent)]">
            <Sparkles className="size-4" />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-[var(--text-muted)]">Risky Runs</p>
            <p className="mt-2 text-2xl font-semibold text-white">{overview?.summary.riskyRuns ?? 0}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <p className="text-[0.68rem] uppercase tracking-[0.24em] text-[var(--text-muted)]">Suppressed</p>
            <p className="mt-2 text-2xl font-semibold text-white">{overview?.summary.suppressedActions ?? 0}</p>
          </div>
        </div>
      </Card>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Conversation History</p>
            <p className="text-sm text-[var(--text-secondary)]">Run queue with deep-link and review filters</p>
          </div>
          <Badge tone="neutral">{overview?.runs.length ?? 0}</Badge>
        </div>
        <Input
          ref={searchRef}
          aria-label="Filter runs"
          placeholder="Filter runs or endpoints"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {filters.map((item) => (
            <button
              key={item.value}
              className={cn(
                "rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] transition",
                filter === item.value
                  ? "border-[var(--border-strong)] bg-[rgba(111,231,255,.14)] text-white"
                  : "border-white/10 bg-white/[0.03] text-[var(--text-secondary)] hover:bg-white/[0.06] hover:text-white",
              )}
              onClick={() => onFilterChange(item.value)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="space-y-2 overflow-y-auto pr-1">
          {overview?.runs.map((run) => (
            <button
              key={run.runId}
              className={cn(
                "group w-full rounded-[1.4rem] border p-4 text-left transition",
                selectedRunId === run.runId
                  ? "border-[var(--border-strong)] bg-[linear-gradient(180deg,rgba(111,231,255,.12),rgba(255,255,255,.02))] shadow-[0_18px_45px_rgba(0,155,255,.18)]"
                  : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]",
              )}
              onClick={() => onSelectRun(run.runId)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "size-2 rounded-full",
                        run.outcome === "allowed"
                          ? "bg-[rgb(83,255,197)]"
                          : run.outcome === "config_error"
                            ? "bg-[rgb(255,112,146)]"
                            : "bg-[rgb(255,186,102)]",
                      )}
                    />
                    <p className="truncate text-sm font-semibold text-white">{run.runId}</p>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-[var(--text-secondary)]">{run.headline}</p>
                </div>
                <Badge tone={outcomeTone(run.outcome)}>{run.outcome.replaceAll("_", " ")}</Badge>
              </div>

              <div className="mt-4 flex items-center gap-3 text-xs text-[var(--text-muted)]">
                <span className="inline-flex items-center gap-1">
                  <Zap className="size-3" />
                  {run.eventCount} actions
                </span>
                {run.timestamp ? (
                  <span className="inline-flex items-center gap-1">
                    <Clock3 className="size-3" />
                    {new Date(run.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                ) : null}
                {run.suppressedCount > 0 ? (
                  <span className="inline-flex items-center gap-1">
                    <ShieldCheck className="size-3" />
                    {run.suppressedCount} suppressed
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1">
                    <ShieldX className="size-3" />
                    live review
                  </span>
                )}
              </div>
            </button>
          ))}

          {!overview?.runs.length ? (
            <Card className="p-6 text-center text-sm text-[var(--text-secondary)]">
              Launch a scenario or point the UI at an existing Mirage trace store.
            </Card>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
