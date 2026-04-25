"use client";

import { Loader2, Play } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ConsoleOverview, QueueFilter, RunListItem } from "@/types/console";

interface SidebarProps {
  runs: RunListItem[];
  overview: ConsoleOverview | null;
  selectedRunId: string | null;
  filter: QueueFilter;
  search: string;
  launchingScenario: string | null;
  onFilterChange: (f: QueueFilter) => void;
  onSearchChange: (s: string) => void;
  onSelectRun: (runId: string) => void;
  onLaunchScenario: (name: "safe" | "risky" | "unmatched") => void;
}

const SCENARIOS = [
  { name: "safe" as const, label: "Compliant bid", meta: "$7.5k", tone: "good" as const },
  { name: "risky" as const, label: "Excessive bid", meta: "$50k", tone: "bad" as const },
  { name: "unmatched" as const, label: "New supplier", meta: "unconfig", tone: "warn" as const },
];

function outcomeDot(outcome: string) {
  if (outcome === "allowed") return "bg-[var(--green)]";
  if (outcome === "config_error") return "bg-[var(--bad)]";
  return "bg-[var(--warn)]";
}

function outcomeBadge(outcome: string): { tone: string; label: string } {
  if (outcome === "allowed") return { tone: "text-[var(--green)]", label: "allowed" };
  if (outcome === "config_error") return { tone: "text-[var(--bad)]", label: "config" };
  if (outcome === "unmatched_route") return { tone: "text-[var(--warn)]", label: "unmatched" };
  return { tone: "text-[var(--warn)]", label: "violation" };
}

function timeAgo(ts: string | null | undefined) {
  if (!ts) return null;
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
  if (diff < 1) return "now";
  if (diff < 60) return `${diff}m`;
  return `${Math.floor(diff / 60)}h`;
}

function filterCount(outcome: QueueFilter, overview: ConsoleOverview | null): number | null {
  if (!overview) return null;
  const s = overview.summary;
  if (outcome === "all") return s.totalRuns;
  if (outcome === "risky") return s.riskyRuns;
  if (outcome === "allowed") return s.allowed;
  if (outcome === "unmatched_route") return s.unmatchedRoute;
  return null;
}

const FILTERS: Array<{ value: QueueFilter; label: string }> = [
  { value: "all", label: "all" },
  { value: "risky", label: "risky" },
  { value: "allowed", label: "allowed" },
  { value: "unmatched_route", label: "unmatched" },
];

const TONE_RING: Record<"good" | "bad" | "warn", string> = {
  good: "border-l-[var(--green)]/60",
  bad: "border-l-[var(--bad)]/60",
  warn: "border-l-[var(--warn)]/60",
};

const TONE_TEXT: Record<"good" | "bad" | "warn", string> = {
  good: "text-[var(--green)]",
  bad: "text-[var(--bad)]",
  warn: "text-[var(--warn)]",
};

export function Sidebar({
  runs,
  overview,
  selectedRunId,
  filter,
  search,
  launchingScenario,
  onFilterChange,
  onSearchChange,
  onSelectRun,
  onLaunchScenario,
}: SidebarProps) {
  const maxCount = Math.max(...(overview?.topEndpoints.map((e) => e.count) ?? [1]), 1);

  return (
    <aside className="relative z-10 flex w-[288px] shrink-0 flex-col overflow-hidden border-r border-[var(--line)] bg-[rgba(10,10,10,0.4)]">
      {/* Section header */}
      <div className="flex shrink-0 items-baseline justify-between border-b border-[var(--line)] px-5 pb-3.5 pt-4">
        <div className="flex items-baseline gap-2">
          <span className="label">Queue</span>
        </div>
        <span className="numeral text-[16px] tabular-nums text-[var(--paper)]">
          {overview?.runs.length ?? 0}
        </span>
      </div>

      {/* Search */}
      <div className="shrink-0 px-5 pt-4">
        <input
          value={search}
          placeholder="filter by run id"
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full border-0 border-b border-[var(--line)] bg-transparent py-1.5 font-mono text-[11.5px] text-[var(--paper)] placeholder:text-[var(--paper-faint)] outline-none transition-colors focus:border-[var(--green)]/60"
        />
      </div>

      {/* Filters */}
      <div className="flex shrink-0 gap-4 px-5 pb-4 pt-3">
        {FILTERS.map((f) => {
          const count = filterCount(f.value, overview);
          const active = filter === f.value;
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => onFilterChange(f.value)}
              className={cn(
                "group relative flex items-baseline gap-1 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors",
                active
                  ? "text-[var(--paper)]"
                  : "text-[var(--paper-mute)] hover:text-[var(--paper-soft)]",
              )}
            >
              {f.label}
              {count !== null && (
                <span
                  className={cn(
                    "tabular-nums text-[9.5px]",
                    active ? "text-[var(--green)]" : "text-[var(--paper-faint)]",
                  )}
                >
                  {count}
                </span>
              )}
              {active && (
                <span className="absolute -bottom-1 left-0 right-0 h-px bg-[var(--green)]" aria-hidden />
              )}
            </button>
          );
        })}
      </div>

      {/* Run list */}
      <div className="flex-1 overflow-y-auto">
        <div className="border-t border-[var(--line)]">
          {runs.map((run) => {
            const badge = outcomeBadge(run.outcome);
            const selected = selectedRunId === run.runId;
            return (
              <button
                key={run.runId}
                type="button"
                onClick={() => onSelectRun(run.runId)}
                className={cn(
                  "group relative block w-full border-b border-[var(--line)] px-5 py-3 text-left transition-colors",
                  selected
                    ? "bg-[var(--green-faint)]"
                    : "hover:bg-[var(--surface)]",
                )}
              >
                {selected && (
                  <span className="absolute left-0 top-0 h-full w-[2px] bg-[var(--green)] shadow-[0_0_10px_var(--green-glow)]" aria-hidden />
                )}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className={cn("size-1.5 shrink-0 rounded-full", outcomeDot(run.outcome))} />
                    <span className={cn(
                      "truncate font-mono text-[11.5px] tracking-tight",
                      selected ? "text-[var(--paper)]" : "text-[var(--paper-soft)]",
                    )}>
                      {run.runId}
                    </span>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 font-mono text-[9.5px] uppercase tracking-[0.18em]",
                      badge.tone,
                    )}
                  >
                    {badge.label}
                  </span>
                </div>
                {(run.method || run.path) && (
                  <p className="mt-1 pl-3.5 font-mono text-[10px] text-[var(--paper-mute)] truncate">
                    <span className="text-[var(--paper-faint)]">{run.method}</span> {run.path}
                  </p>
                )}
                <p className="mt-0.5 pl-3.5 font-mono text-[9.5px] tabular-nums text-[var(--paper-faint)]">
                  {timeAgo(run.timestamp) ?? "—"}
                  {run.eventCount > 0 ? ` · ${run.eventCount} ev` : ""}
                </p>
              </button>
            );
          })}

          {runs.length === 0 && (
            <div className="px-5 py-10 text-center">
              <p className="font-display text-[14px] font-medium text-[var(--paper-mute)]">
                {search ? "Nothing matches" : "Queue is idle"}
              </p>
              <p className="mt-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--paper-faint)]">
                {search ? "adjust the filter" : "launch a scenario below"}
              </p>
            </div>
          )}
        </div>

        {/* Endpoints */}
        {!!overview?.topEndpoints.length && (
          <div className="border-t border-[var(--line)] px-5 py-4">
            <p className="label mb-3">Endpoints</p>
            <div className="space-y-2.5">
              {overview.topEndpoints.map((ep) => {
                const isRisky = ep.violationCount > ep.count / 2;
                const barColor = isRisky ? "bg-[var(--warn)]/55" : "bg-[var(--green)]/55";
                return (
                  <div key={ep.label}>
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="min-w-0 truncate font-mono text-[10px] text-[var(--paper-soft)]">
                        <span className="text-[var(--paper-faint)]">{ep.method}</span> {ep.path}
                      </span>
                      <span className="shrink-0 font-mono tabular-nums text-[10px] text-[var(--paper-mute)]">
                        {ep.count}
                      </span>
                    </div>
                    <div className="h-px w-full bg-[var(--line)]">
                      <div
                        className={cn("h-full transition-all", barColor)}
                        style={{ width: `${Math.round((ep.count / maxCount) * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Policy friction */}
        {!!overview?.topPolicyFailures.length && (
          <div className="border-t border-[var(--line)] px-5 py-4">
            <p className="label mb-3">Policy friction</p>
            <div className="space-y-1.5">
              {overview.topPolicyFailures.map((p) => (
                <div key={p.name} className="flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate font-mono text-[10.5px] text-[var(--paper-soft)]">
                    {p.name}
                  </span>
                  <span className="font-mono tabular-nums text-[10px] text-[var(--paper-mute)]">
                    {p.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scenarios */}
        <div className="border-t border-[var(--line)] px-5 py-4">
          <div className="mb-3 flex items-baseline justify-between">
            <p className="label">Scenarios</p>
            <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-[var(--paper-faint)]">
              demo
            </span>
          </div>
          <div className="space-y-1.5">
            {SCENARIOS.map((s) => {
              const isLaunching = launchingScenario === s.name;
              const dimmed = launchingScenario !== null && !isLaunching;
              return (
                <button
                  key={s.name}
                  type="button"
                  disabled={launchingScenario !== null}
                  onClick={() => onLaunchScenario(s.name)}
                  className={cn(
                    "group flex w-full items-center justify-between gap-3 border-l-2 border-[var(--line)] bg-[var(--surface)] py-2 pl-3 pr-3 text-left transition-all",
                    dimmed
                      ? "opacity-30"
                      : isLaunching
                        ? "border-l-[var(--green)] bg-[var(--green-faint)]"
                        : `${TONE_RING[s.tone]} hover:border-l-[var(--green)] hover:bg-[var(--green-faint)]`,
                  )}
                >
                  <span className="flex items-center gap-2.5">
                    {isLaunching ? (
                      <Loader2 className="size-3 animate-spin text-[var(--green)]" />
                    ) : (
                      <Play className="size-2.5 text-[var(--paper-mute)] transition-colors group-hover:text-[var(--green)]" fill="currentColor" />
                    )}
                    <span className="text-[12px] font-medium text-[var(--paper-soft)] group-hover:text-[var(--paper)]">
                      {s.label}
                    </span>
                  </span>
                  <span className={cn("font-mono text-[10.5px] tabular-nums", TONE_TEXT[s.tone])}>
                    {s.meta}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
