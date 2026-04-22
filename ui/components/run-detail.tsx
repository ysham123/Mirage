"use client";

import { useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ConsoleOverview, ConsoleRun, SideEffect } from "@/types/console";

type RunView = "overview" | "timeline" | "graph" | "trace";

interface RunDetailProps {
  overview: ConsoleOverview | null;
  run: ConsoleRun | null;
  loading: boolean;
  onSuppress: (stepIndex: number) => void;
}

/* ─── helpers ──────────────────────────────────────────────────────────── */

function outcomeBadge(outcome: string): { cls: string; label: string } {
  if (outcome === "allowed")
    return { cls: "border-green-500/25 bg-green-500/8 text-green-400", label: "allowed" };
  if (outcome === "config_error")
    return { cls: "border-red-400/25 bg-red-500/8 text-red-400", label: "config error" };
  if (outcome === "unmatched_route")
    return { cls: "border-orange-400/25 bg-orange-400/8 text-orange-300", label: "unmatched route" };
  return { cls: "border-orange-400/25 bg-orange-400/8 text-orange-300", label: "policy violation" };
}

function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 1500);
    }).catch(() => null);
  };
  return { copied, copy };
}

/* ─── Stat card ─────────────────────────────────────────────────────────── */

function StatCard({
  label, value, percent, accent,
}: { label: string; value: number; percent?: boolean; accent?: "orange" | "green" }) {
  return (
    <div className={cn(
      "flex flex-1 flex-col border-r border-white/[0.07] px-5 py-4 last:border-r-0",
      accent === "orange" && value > 0 && "border-t border-t-orange-400/30",
    )}>
      <span className="text-[9px] font-semibold uppercase tracking-[0.2em] text-white/25">{label}</span>
      <div className="mt-1.5 flex items-baseline gap-0.5">
        <span className={cn(
          "text-[22px] font-semibold leading-none tabular-nums",
          accent === "orange" && value > 0 ? "text-orange-300" : "text-white",
        )}>
          {value}
        </span>
        {percent && <span className="text-sm text-white/25">%</span>}
      </div>
    </div>
  );
}

/* ─── Overview tab ──────────────────────────────────────────────────────── */

function OverviewPanel({ run, overview }: { run: ConsoleRun; overview: ConsoleOverview | null }) {
  const latestEffect = run.sideEffects.at(-1);
  const policyFailures = run.sideEffects.filter((e) => !e.policyPassed).length;
  const primaryPolicy = overview?.topPolicyFailures[0]?.name ?? "—";

  const rows = [
    { label: "Final outcome", value: outcomeBadge(run.finalOutcome).label },
    { label: "Latest action", value: latestEffect ? `${latestEffect.method} ${latestEffect.path}` : "—" },
    { label: "Policy failures", value: String(policyFailures) },
    { label: "Trace path", value: run.tracePath },
    { label: "Primary policy", value: primaryPolicy },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Action path */}
      <div className="rounded border border-white/[0.07] bg-white/[0.02] p-5">
        <h3 className="text-[12px] font-semibold text-white/80">Action path</h3>
        <p className="mt-0.5 text-[11px] text-white/25">
          The contained flow before drilling into timeline, graph, or raw trace.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {run.sideEffects.length > 0 ? (
            run.sideEffects.map((effect, i) => (
              <span key={effect.id} className="flex items-center gap-2">
                <span className={cn(
                  "rounded border px-3 py-1.5 text-[11px] transition-colors",
                  effect.outcome === "allowed"
                    ? "border-green-500/20 text-green-400/70"
                    : "border-orange-400/20 text-orange-300/70",
                )}>
                  {effect.name}
                </span>
                {i < run.sideEffects.length - 1 && (
                  <span className="text-white/20 text-[11px]">→</span>
                )}
              </span>
            ))
          ) : (
            <span className="text-[11px] text-white/20">No actions recorded.</span>
          )}
        </div>
      </div>

      {/* Review summary */}
      <div className="rounded border border-white/[0.07] bg-white/[0.02] p-5">
        <h3 className="text-[12px] font-semibold text-white/80">Review summary</h3>
        <div className="mt-4 divide-y divide-white/[0.05]">
          {rows.map(({ label, value }) => (
            <div key={label} className="flex items-start gap-3 py-2 first:pt-0 last:pb-0">
              <span className="w-28 shrink-0 text-[11px] text-white/30">{label}</span>
              <span className="min-w-0 break-all font-mono text-[11px] text-white/60">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Timeline tab ──────────────────────────────────────────────────────── */

function TimelinePanel({
  effects,
  focusedIndex,
  onSuppress,
}: {
  effects: SideEffect[];
  focusedIndex: number | null;
  onSuppress: (i: number) => void;
}) {
  const focusRef = useRef<HTMLDivElement | null>(null);

  if (effects.length === 0) {
    return (
      <p className="py-10 text-center text-[11px] text-white/20">No side effects recorded.</p>
    );
  }

  return (
    <div className="relative pl-6">
      {/* vertical guide */}
      <div className="absolute left-[11px] top-2 bottom-2 w-px bg-white/[0.06]" />

      <div className="space-y-3">
        {effects.map((effect, i) => {
          const badge = outcomeBadge(effect.outcome);
          const isFocused = focusedIndex === effect.stepIndex;
          return (
            <div
              key={effect.id}
              ref={isFocused ? focusRef : null}
              className={cn(
                "relative rounded border p-4 transition-colors",
                isFocused
                  ? "border-orange-400/30 bg-orange-400/[0.04]"
                  : "border-white/[0.07] bg-white/[0.02]",
              )}
            >
              {/* step dot */}
              <div
                className={cn(
                  "absolute -left-[19px] top-[18px] size-2 rounded-full border",
                  effect.outcome === "allowed"
                    ? "border-green-500/50 bg-green-500/30"
                    : "border-orange-400/50 bg-orange-400/30",
                )}
              />

              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-semibold text-white/20 tabular-nums">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="font-mono text-[12px] font-medium text-white/80">
                      {effect.method} {effect.path}
                    </span>
                  </div>
                  {effect.decisionSummary && (
                    <p className="mt-1.5 text-[11px] leading-relaxed text-white/35">{effect.decisionSummary}</p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={cn(
                      "rounded border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
                      badge.cls,
                    )}
                  >
                    {badge.label}
                  </span>
                  {effect.suppressed ? (
                    <span className="text-[9px] text-white/20">suppressed</span>
                  ) : (
                    !effect.policyPassed && (
                      <button
                        className="rounded border border-white/[0.1] px-2 py-0.5 text-[9px] text-white/30 transition-colors hover:border-white/25 hover:text-white/60"
                        onClick={() => onSuppress(effect.stepIndex)}
                        type="button"
                      >
                        Suppress
                      </button>
                    )
                  )}
                </div>
              </div>

              {effect.statusCode && (
                <div className="mt-2 text-[10px] text-white/20">
                  Status <span className="font-mono">{effect.statusCode}</span>
                  {effect.confidence > 0 && (
                    <> · Confidence <span className="font-mono">{Math.round(effect.confidence * 100)}%</span></>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Graph tab ─────────────────────────────────────────────────────────── */

function GraphPanel({ run }: { run: ConsoleRun }) {
  if (run.sideEffects.length === 0) {
    return <p className="py-10 text-center text-[11px] text-white/20">No graph data.</p>;
  }

  return (
    <div className="flex min-h-[200px] items-center justify-center overflow-x-auto rounded border border-white/[0.07] bg-white/[0.01] p-8">
      <div className="flex items-center gap-0">
        {run.sideEffects.map((effect, i) => {
          const isRisky = effect.outcome !== "allowed";
          return (
            <div key={effect.id} className="flex items-center">
              <div
                className={cn(
                  "flex flex-col items-center gap-2 rounded border px-4 py-3 min-w-[100px]",
                  isRisky
                    ? "border-orange-400/20 bg-orange-400/[0.04]"
                    : "border-green-500/20 bg-green-500/[0.04]",
                )}
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    isRisky ? "bg-orange-400" : "bg-green-500",
                  )}
                />
                <span className="text-center text-[11px] font-medium text-white/70">{effect.name}</span>
                <span className="font-mono text-[9px] text-white/25">{effect.method}</span>
                {effect.statusCode && (
                  <span className={cn(
                    "rounded px-1.5 py-0.5 font-mono text-[9px]",
                    isRisky ? "bg-orange-400/10 text-orange-300" : "bg-green-500/10 text-green-400",
                  )}>
                    {effect.statusCode}
                  </span>
                )}
              </div>
              {i < run.sideEffects.length - 1 && (
                <div className="flex items-center px-2">
                  <div className="h-px w-6 bg-white/10" />
                  <span className="text-[10px] text-white/15">→</span>
                  <div className="h-px w-6 bg-white/10" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Trace tab ─────────────────────────────────────────────────────────── */

function TracePanel({ trace }: { trace: Record<string, unknown> }) {
  const { copied, copy } = useCopy();
  const json = JSON.stringify(trace, null, 2);

  return (
    <div className="relative">
      <button
        className="absolute right-3 top-3 flex items-center gap-1.5 rounded border border-white/[0.1] bg-black/40 px-2 py-1 text-[9px] text-white/40 transition-colors hover:text-white/70 z-10"
        onClick={() => copy(json, "trace")}
        type="button"
      >
        {copied === "trace" ? <Check className="size-2.5" /> : <Copy className="size-2.5" />}
        {copied === "trace" ? "Copied" : "Copy"}
      </button>
      <pre className="overflow-x-auto rounded border border-white/[0.07] bg-black/25 p-4 pt-10 text-[11px] leading-relaxed text-[rgb(180,220,255)]">
        {json}
      </pre>
    </div>
  );
}

/* ─── Main component ────────────────────────────────────────────────────── */

export function RunDetail({ overview, run, loading, onSuppress }: RunDetailProps) {
  const [view, setView] = useState<RunView>("overview");
  const [focusedStep, setFocusedStep] = useState<number | null>(null);
  const { copied, copy } = useCopy();

  const summary = overview?.summary;
  const riskRate = summary && summary.totalRuns > 0
    ? Math.round((summary.riskyRuns / summary.totalRuns) * 100)
    : 0;

  const firstRiskyStep = run?.sideEffects.find((e) => !e.policyPassed && !e.suppressed);

  const handleNextRisky = () => {
    if (!firstRiskyStep) return;
    setView("timeline");
    setFocusedStep(firstRiskyStep.stepIndex);
  };

  const VIEWS: Array<{ value: RunView; label: string }> = [
    { value: "overview", label: "Overview" },
    { value: "timeline", label: "Timeline" },
    { value: "graph", label: "Run Graph" },
    { value: "trace", label: "Raw Trace" },
  ];

  return (
    <div className="flex flex-1 flex-col overflow-hidden">

      {/* Stats bar */}
      <div className="flex shrink-0 border-b border-white/[0.07]">
        <StatCard label="Total Actions" value={summary?.totalActions ?? 0} />
        <StatCard label="Tracked Runs" value={summary?.totalRuns ?? 0} />
        <StatCard label="Risky" value={summary?.riskyRuns ?? 0} accent="orange" />
        <StatCard label="Allowed" value={summary?.allowed ?? 0} accent="green" />
        <StatCard label="Unmatched" value={summary?.unmatchedRoute ?? 0} />
        <StatCard label="Risk Rate" value={riskRate} percent accent={riskRate > 20 ? "orange" : undefined} />
      </div>

      {/* Empty / loading state */}
      {!run && (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-[12px] text-white/20">
            {loading ? "Loading run…" : "Select a run to inspect."}
          </p>
        </div>
      )}

      {run && (
        <>
          {/* Context banner */}
          <div className="flex shrink-0 items-center justify-between gap-4 border-b border-white/[0.06] px-6 py-2.5">
            <p className="text-[12px] text-white/40 truncate">{run.headline}</p>
            <span
              className={cn(
                "shrink-0 rounded border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
                outcomeBadge(run.finalOutcome).cls,
              )}
            >
              {outcomeBadge(run.finalOutcome).label}
            </span>
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto">

            {/* Run heading */}
            <div className="border-b border-white/[0.05] px-6 py-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1
                    role="heading"
                    className="font-mono text-xl font-semibold text-white"
                  >
                    {run.runId}
                  </h1>
                  <p className="mt-1 text-[11px] text-white/30">{run.headline}</p>
                </div>
                <span
                  className={cn(
                    "mt-0.5 shrink-0 rounded border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
                    outcomeBadge(run.finalOutcome).cls,
                  )}
                >
                  {outcomeBadge(run.finalOutcome).label}
                </span>
              </div>

              {/* Info cards */}
              <div className="mt-4 grid grid-cols-4 gap-2.5">
                {[
                  { label: "Run ID", value: run.runId, mono: true },
                  { label: "Source", value: run.source, mono: true },
                  { label: "Trace Path", value: run.tracePath, mono: true },
                  { label: "Events", value: String(run.eventCount), mono: false },
                ].map(({ label, value, mono }) => (
                  <div
                    key={label}
                    className="rounded border border-white/[0.07] bg-white/[0.02] p-3"
                  >
                    <p className="text-[8.5px] font-semibold uppercase tracking-[0.18em] text-white/25">{label}</p>
                    <p className={cn(
                      "mt-1.5 break-all text-[10px] text-white/55",
                      mono && "font-mono",
                    )}>
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Action buttons */}
              <div className="mt-3.5 flex flex-wrap gap-2">
                {[
                  {
                    label: "Copy Run ID",
                    key: "runId",
                    action: () => copy(run.runId, "runId"),
                    icon: copied === "runId" ? Check : Copy,
                  },
                  {
                    label: "Copy Trace Path",
                    key: "tracePath",
                    action: () => copy(run.tracePath, "tracePath"),
                    icon: copied === "tracePath" ? Check : Copy,
                  },
                  {
                    label: "Open Raw Trace",
                    key: "rawTrace",
                    action: () => setView("trace"),
                    icon: null,
                  },
                  {
                    label: firstRiskyStep ? "Next Risky Action" : "No Risky Actions",
                    key: "nextRisky",
                    action: handleNextRisky,
                    icon: null,
                    disabled: !firstRiskyStep,
                  },
                ].map(({ label, key, action, icon: Icon, disabled }) => (
                  <button
                    key={key}
                    disabled={disabled}
                    className={cn(
                      "flex items-center gap-1.5 rounded border px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.14em] transition-colors",
                      disabled
                        ? "border-white/[0.05] text-white/15 cursor-default"
                        : "border-white/[0.1] text-white/40 hover:border-white/25 hover:text-white/70",
                      key === "runId" && copied === "runId" && "border-green-500/20 text-green-400",
                      key === "tracePath" && copied === "tracePath" && "border-green-500/20 text-green-400",
                    )}
                    onClick={action}
                    type="button"
                  >
                    {Icon && <Icon className="size-2.5" />}
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/[0.07] px-6">
              {VIEWS.map(({ value: v, label }) => (
                <button
                  key={v}
                  className={cn(
                    "border-b-2 px-3 py-2.5 text-[10px] font-semibold uppercase tracking-[0.15em] transition-colors",
                    view === v
                      ? "border-white/70 text-white/90"
                      : "border-transparent text-white/25 hover:text-white/50",
                  )}
                  onClick={() => setView(v)}
                  type="button"
                >
                  {label}
                </button>
              ))}
              {loading && (
                <span className="ml-auto flex items-center self-center text-[10px] text-white/20">
                  Refreshing…
                </span>
              )}
            </div>

            {/* Tab content */}
            <div className="p-6">
              {view === "overview" && <OverviewPanel overview={overview} run={run} />}
              {view === "timeline" && (
                <TimelinePanel
                  effects={run.sideEffects}
                  focusedIndex={focusedStep}
                  onSuppress={onSuppress}
                />
              )}
              {view === "graph" && <GraphPanel run={run} />}
              {view === "trace" && <TracePanel trace={run.trace} />}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
