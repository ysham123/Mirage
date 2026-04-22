"use client";

import { Loader2 } from "lucide-react";

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
  { name: "safe" as const, label: "Compliant Bid", meta: "$7.5k" },
  { name: "risky" as const, label: "Excessive Bid", meta: "$50k" },
  { name: "unmatched" as const, label: "New Supplier", meta: "unconfig" },
];

function outcomeDot(outcome: string) {
  if (outcome === "allowed") return "bg-green-500";
  if (outcome === "config_error") return "bg-red-400";
  return "bg-orange-400";
}

function outcomeBadge(outcome: string) {
  if (outcome === "allowed") return { style: "border-green-500/25 text-green-400/80", label: "allowed" };
  if (outcome === "config_error") return { style: "border-red-400/25 text-red-400/80", label: "config error" };
  if (outcome === "unmatched_route") return { style: "border-orange-400/25 text-orange-300/80", label: "unmatched" };
  return { style: "border-orange-400/25 text-orange-300/80", label: "policy violation" };
}

function timeAgo(ts: string | null | undefined) {
  if (!ts) return null;
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
  if (diff < 1) return "just now";
  if (diff < 60) return `${diff}m ago`;
  return `${Math.floor(diff / 60)}h ago`;
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
  { value: "all", label: "All" },
  { value: "risky", label: "Risky" },
  { value: "allowed", label: "Allowed" },
  { value: "unmatched_route", label: "Unmatched" },
];

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
    <aside className="flex w-[256px] shrink-0 flex-col overflow-hidden border-r border-white/[0.07] bg-[rgba(4,8,16,0.6)]">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
        <span className="text-[9px] font-semibold uppercase tracking-[0.22em] text-white/30">
          Needs Review
        </span>
        <span className="text-[10px] tabular-nums text-white/30">
          {overview?.runs.length ?? 0} runs
        </span>
      </div>

      {/* Search */}
      <div className="px-3 pt-2.5 pb-1.5">
        <input
          className="w-full border-0 border-b border-white/[0.08] bg-transparent py-1.5 text-[11px] text-white/70 placeholder:text-white/20 outline-none transition-colors focus:border-white/20"
          placeholder="Filter runs..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Filter pills */}
      <div className="flex gap-0.5 px-3 pb-2.5">
        {FILTERS.map((f) => {
          const count = filterCount(f.value, overview);
          return (
            <button
              key={f.value}
              className={cn(
                "flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium transition-colors",
                filter === f.value
                  ? "bg-white text-black"
                  : "text-white/30 hover:text-white/60",
              )}
              onClick={() => onFilterChange(f.value)}
              type="button"
            >
              {f.label}
              {count !== null && filter !== f.value && (
                <span className="tabular-nums opacity-60">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Run list */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-px pb-1">
          {runs.map((run) => {
            const badge = outcomeBadge(run.outcome);
            const selected = selectedRunId === run.runId;
            return (
              <button
                key={run.runId}
                className={cn(
                  "w-full px-4 py-2.5 text-left transition-colors",
                  selected
                    ? "bg-white/[0.07] border-l-2 border-l-white/40 pl-[14px]"
                    : "border-l-2 border-l-transparent hover:bg-white/[0.03]",
                )}
                onClick={() => onSelectRun(run.runId)}
                type="button"
              >
                <div className="flex items-center justify-between gap-2 min-w-0">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span className={cn("size-1.5 shrink-0 rounded-full", outcomeDot(run.outcome))} />
                    <span className="truncate font-mono text-[11px] text-white/80">{run.runId}</span>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 border rounded px-1.5 py-px text-[8.5px] font-semibold uppercase tracking-wider whitespace-nowrap",
                      badge.style,
                    )}
                  >
                    {badge.label}
                  </span>
                </div>
                {(run.method || run.path) && (
                  <p className="mt-0.5 pl-3 font-mono text-[10px] text-white/25 truncate">
                    {run.method} {run.path}
                  </p>
                )}
                <p className="mt-0.5 pl-3 text-[10px] text-white/20">
                  {timeAgo(run.timestamp) ?? ""}
                  {run.eventCount > 0 ? ` · ${run.eventCount} ${run.eventCount === 1 ? "event" : "events"}` : ""}
                </p>
              </button>
            );
          })}

          {runs.length === 0 && (
            <p className="px-4 py-5 text-center text-[11px] text-white/20">
              {search ? "No runs match your filter." : "No runs yet. Launch a scenario below."}
            </p>
          )}
        </div>

        {/* Endpoints */}
        {!!overview?.topEndpoints.length && (
          <div className="border-t border-white/[0.06] px-4 py-3">
            <p className="mb-2.5 text-[8.5px] font-semibold uppercase tracking-[0.22em] text-white/25">
              Endpoints
            </p>
            <div className="space-y-2">
              {overview.topEndpoints.map((ep) => {
                const isRisky = ep.violationCount > ep.count / 2;
                const barColor = isRisky ? "bg-orange-400/50" : "bg-green-500/50";
                return (
                  <div key={ep.label}>
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <span className="min-w-0 truncate font-mono text-[10px] text-white/40">
                        {ep.method} {ep.path}
                      </span>
                      <span className="shrink-0 tabular-nums text-[10px] text-white/25">{ep.count}</span>
                    </div>
                    <div className="h-px w-full bg-white/[0.05]">
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

        {/* Policy Friction */}
        {!!overview?.topPolicyFailures.length && (
          <div className="border-t border-white/[0.06] px-4 py-3">
            <p className="mb-2.5 text-[8.5px] font-semibold uppercase tracking-[0.22em] text-white/25">
              Policy Friction
            </p>
            <div className="space-y-1.5">
              {overview.topPolicyFailures.map((p) => (
                <div key={p.name} className="flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate text-[10px] text-white/40">{p.name}</span>
                  <span className="tabular-nums text-[10px] text-white/25">{p.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scenarios */}
        <div className="border-t border-white/[0.06] px-4 py-3">
          <div className="mb-2.5 flex items-center justify-between">
            <p className="text-[8.5px] font-semibold uppercase tracking-[0.22em] text-white/25">Scenarios</p>
            <span className="rounded border border-white/[0.08] px-1.5 py-px text-[8px] text-white/20">demo</span>
          </div>
          <div className="space-y-px">
            {SCENARIOS.map((s) => {
              const isLaunching = launchingScenario === s.name;
              return (
                <button
                  key={s.name}
                  disabled={launchingScenario !== null}
                  className={cn(
                    "flex w-full items-center justify-between py-1.5 text-left transition-opacity",
                    launchingScenario !== null && !isLaunching ? "opacity-40" : "hover:opacity-80",
                  )}
                  onClick={() => onLaunchScenario(s.name)}
                  type="button"
                >
                  <span className="flex items-center gap-1.5 text-[11px] text-white/50">
                    {isLaunching && <Loader2 className="size-2.5 animate-spin" />}
                    {s.label}
                  </span>
                  <span className="font-mono text-[10px] text-white/25">{s.meta}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
}
