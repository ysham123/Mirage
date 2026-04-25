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

function outcomeBadge(outcome: string): { tone: string; border: string; label: string } {
  if (outcome === "allowed")
    return { tone: "text-[var(--green)]", border: "border-[var(--green)]/40", label: "allowed" };
  if (outcome === "config_error")
    return { tone: "text-[var(--bad)]", border: "border-[var(--bad)]/40", label: "config error" };
  if (outcome === "unmatched_route")
    return { tone: "text-[var(--warn)]", border: "border-[var(--warn)]/40", label: "unmatched route" };
  return { tone: "text-[var(--warn)]", border: "border-[var(--warn)]/40", label: "policy violation" };
}

function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = (text: string, key: string) => {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(key);
        setTimeout(() => setCopied(null), 1500);
      })
      .catch(() => null);
  };
  return { copied, copy };
}

/* ─── Stat ──────────────────────────────────────────────────────────────── */

function Stat({
  label,
  value,
  percent,
  tone,
}: {
  label: string;
  value: number;
  percent?: boolean;
  tone?: "green" | "warn" | "bad";
}) {
  const numeralTone =
    tone === "green" && value > 0
      ? "text-[var(--green)]"
      : tone === "warn" && value > 0
        ? "text-[var(--warn)]"
        : tone === "bad" && value > 0
          ? "text-[var(--bad)]"
          : "text-[var(--paper)]";

  const railTone =
    tone === "green" && value > 0
      ? "bg-[var(--green)]"
      : tone === "warn" && value > 0
        ? "bg-[var(--warn)]"
        : tone === "bad" && value > 0
          ? "bg-[var(--bad)]"
          : "bg-transparent";

  return (
    <div className="relative flex flex-1 flex-col justify-between border-r border-[var(--line)] px-6 py-4 last:border-r-0">
      <span className={cn("absolute left-0 top-0 h-[2px] w-8 transition-colors", railTone)} aria-hidden />
      <span className="label">{label}</span>
      <div className="mt-2.5 flex items-baseline gap-1">
        <span className={cn("numeral text-[34px] tabular-nums leading-[0.9]", numeralTone)}>
          {value}
        </span>
        {percent && (
          <span className="font-display text-[15px] font-medium text-[var(--paper-mute)]">%</span>
        )}
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
    { label: "Final outcome", value: outcomeBadge(run.finalOutcome).label, mono: false },
    {
      label: "Latest action",
      value: latestEffect ? `${latestEffect.method} ${latestEffect.path}` : "—",
      mono: true,
    },
    { label: "Policy failures", value: String(policyFailures), mono: false },
    { label: "Trace path", value: run.tracePath, mono: true },
    { label: "Primary policy", value: primaryPolicy, mono: true },
  ];

  return (
    <div className="grid grid-cols-2 gap-10">
      {/* Action path */}
      <section>
        <header className="border-b border-[var(--line)] pb-2">
          <h3 className="font-display text-[15px] font-medium tracking-tight text-[var(--paper)]">
            Action path
          </h3>
          <p className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
            ordered side-effects
          </p>
        </header>
        <div className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-2.5">
          {run.sideEffects.length > 0 ? (
            run.sideEffects.map((effect, i) => (
              <span key={effect.id} className="flex items-center gap-2">
                <span
                  className={cn(
                    "border px-3 py-1.5 font-mono text-[10.5px]",
                    effect.outcome === "allowed"
                      ? "border-[var(--green)]/30 text-[var(--green)]/90"
                      : "border-[var(--warn)]/30 text-[var(--warn)]/95",
                  )}
                >
                  {effect.name}
                </span>
                {i < run.sideEffects.length - 1 && (
                  <span className="text-[14px] text-[var(--paper-faint)]">→</span>
                )}
              </span>
            ))
          ) : (
            <span className="text-[12px] text-[var(--paper-mute)]">No actions recorded.</span>
          )}
        </div>
      </section>

      {/* Review summary */}
      <section>
        <header className="border-b border-[var(--line)] pb-2">
          <h3 className="font-display text-[15px] font-medium tracking-tight text-[var(--paper)]">
            Review summary
          </h3>
          <p className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
            run metadata
          </p>
        </header>
        <dl className="mt-3 divide-y divide-[var(--line)]">
          {rows.map(({ label, value, mono }) => (
            <div key={label} className="flex items-baseline gap-4 py-2.5">
              <dt className="w-32 shrink-0 font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                {label}
              </dt>
              <dd
                className={cn(
                  "min-w-0 break-all text-[12px] text-[var(--paper-soft)]",
                  mono && "font-mono",
                )}
              >
                {value}
              </dd>
            </div>
          ))}
        </dl>
      </section>
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
      <p className="py-12 text-center text-[12px] text-[var(--paper-mute)]">
        No side effects recorded.
      </p>
    );
  }

  return (
    <div className="relative pl-8">
      {/* vertical guide */}
      <div className="absolute left-[14px] top-3 bottom-3 w-px bg-[var(--line)]" />

      <div className="space-y-3.5">
        {effects.map((effect, i) => {
          const badge = outcomeBadge(effect.outcome);
          const isFocused = focusedIndex === effect.stepIndex;
          const risky = effect.outcome !== "allowed";
          return (
            <div
              key={effect.id}
              ref={isFocused ? focusRef : null}
              className={cn(
                "relative border bg-[var(--surface)] px-5 py-4 transition-colors",
                isFocused
                  ? "border-[var(--green)]/40 bg-[var(--green-faint)]"
                  : "border-[var(--line)] hover:border-[var(--line-strong)]",
              )}
            >
              {/* step marker */}
              <div
                className={cn(
                  "absolute -left-[24px] top-[20px] flex size-[18px] items-center justify-center rounded-full border bg-[var(--ink)]",
                  risky ? "border-[var(--warn)]/60" : "border-[var(--green)]/60",
                )}
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    risky ? "bg-[var(--warn)]" : "bg-[var(--green)]",
                  )}
                />
              </div>

              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-baseline gap-3">
                    <span className="numeral text-[15px] tabular-nums text-[var(--paper-mute)]">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="font-mono text-[12.5px] font-medium text-[var(--paper)]">
                      <span className="text-[var(--paper-faint)]">{effect.method}</span>{" "}
                      {effect.path}
                    </span>
                  </div>
                  {effect.decisionSummary && (
                    <p className="mt-2 max-w-[60ch] text-[12px] leading-relaxed text-[var(--paper-soft)]">
                      {effect.decisionSummary}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span
                    className={cn(
                      "font-mono text-[9.5px] uppercase tracking-[0.18em]",
                      badge.tone,
                    )}
                  >
                    {badge.label}
                  </span>
                  {effect.suppressed ? (
                    <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--paper-faint)]">
                      suppressed
                    </span>
                  ) : (
                    !effect.policyPassed && (
                      <button
                        type="button"
                        onClick={() => onSuppress(effect.stepIndex)}
                        className="border border-[var(--line-strong)] px-2.5 py-1 font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--paper-soft)] transition-colors hover:border-[var(--green)]/60 hover:bg-[var(--green-faint)] hover:text-[var(--paper)]"
                      >
                        suppress
                      </button>
                    )
                  )}
                </div>
              </div>

              {effect.statusCode && (
                <div className="mt-3 flex items-baseline gap-4 border-t border-[var(--line)] pt-2.5">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                    status{" "}
                    <span className="font-mono text-[12px] tabular-nums tracking-normal text-[var(--paper)]">
                      {effect.statusCode}
                    </span>
                  </span>
                  {effect.confidence > 0 && (
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                      conf{" "}
                      <span className="font-mono text-[12px] tabular-nums tracking-normal text-[var(--paper)]">
                        {Math.round(effect.confidence * 100)}
                      </span>
                      <span className="text-[var(--paper-faint)]">%</span>
                    </span>
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
    return (
      <p className="py-12 text-center text-[12px] text-[var(--paper-mute)]">
        No graph data.
      </p>
    );
  }

  return (
    <div className="flex min-h-[220px] items-center overflow-x-auto border border-[var(--line)] bg-[var(--surface)] scan-bg px-10 py-12">
      <div className="flex items-center gap-0">
        {run.sideEffects.map((effect, i) => {
          const isRisky = effect.outcome !== "allowed";
          return (
            <div key={effect.id} className="flex items-center">
              <div
                className={cn(
                  "flex min-w-[120px] flex-col items-center gap-2.5 border bg-[var(--ink-elevated)] px-5 py-4",
                  isRisky
                    ? "border-[var(--warn)]/40"
                    : "border-[var(--green)]/40",
                )}
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    isRisky ? "bg-[var(--warn)]" : "bg-[var(--green)]",
                  )}
                />
                <span className="text-center text-[11.5px] font-medium text-[var(--paper)]">
                  {effect.name}
                </span>
                <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                  {effect.method}
                </span>
                {effect.statusCode && (
                  <span
                    className={cn(
                      "font-mono text-[10px] tabular-nums",
                      isRisky ? "text-[var(--warn)]" : "text-[var(--green)]",
                    )}
                  >
                    {effect.statusCode}
                  </span>
                )}
              </div>
              {i < run.sideEffects.length - 1 && (
                <div className="flex items-center px-3">
                  <div className="h-px w-7 bg-[var(--line-strong)]" />
                  <span className="text-[14px] text-[var(--paper-mute)]">→</span>
                  <div className="h-px w-7 bg-[var(--line-strong)]" />
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
        type="button"
        onClick={() => copy(json, "trace")}
        className="absolute right-3 top-3 z-10 flex items-center gap-1.5 border border-[var(--line-strong)] bg-[var(--ink)]/80 px-2.5 py-1 font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--paper-mute)] backdrop-blur transition-colors hover:border-[var(--green)]/60 hover:text-[var(--paper)]"
      >
        {copied === "trace" ? <Check className="size-2.5" /> : <Copy className="size-2.5" />}
        {copied === "trace" ? "copied" : "copy"}
      </button>
      <pre className="overflow-x-auto border border-[var(--line)] bg-black p-5 pt-12 font-mono text-[11.5px] leading-relaxed text-[var(--paper-soft)]">
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
  const riskRate =
    summary && summary.totalRuns > 0
      ? Math.round((summary.riskyRuns / summary.totalRuns) * 100)
      : 0;

  const firstRiskyStep = run?.sideEffects.find((e) => !e.policyPassed && !e.suppressed);

  const handleNextRisky = () => {
    if (!firstRiskyStep) return;
    setView("timeline");
    setFocusedStep(firstRiskyStep.stepIndex);
  };

  const VIEWS: Array<{ value: RunView; label: string }> = [
    { value: "overview", label: "overview" },
    { value: "timeline", label: "timeline" },
    { value: "graph", label: "run graph" },
    { value: "trace", label: "raw trace" },
  ];

  return (
    <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
      {/* Stats bar */}
      <div className="flex shrink-0 border-b border-[var(--line)]">
        <Stat label="Total actions" value={summary?.totalActions ?? 0} />
        <Stat label="Tracked runs" value={summary?.totalRuns ?? 0} />
        <Stat label="Risky" value={summary?.riskyRuns ?? 0} tone="warn" />
        <Stat label="Allowed" value={summary?.allowed ?? 0} tone="green" />
        <Stat label="Unmatched" value={summary?.unmatchedRoute ?? 0} />
        <Stat
          label="Risk rate"
          value={riskRate}
          percent
          tone={riskRate > 20 ? "warn" : undefined}
        />
      </div>

      {/* Empty / loading state */}
      {!run && (
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <p className="font-display text-[26px] font-medium leading-none tracking-tight text-[var(--paper)]">
            {loading ? "Loading run" : "Console idle"}
          </p>
          <p className="mt-3 font-mono text-[10.5px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
            {loading ? "fetching trace" : "select a run from the queue to inspect"}
          </p>
        </div>
      )}

      {run && (
        <>
          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto fade-in">
            {/* Sticky context strip — persists while scrolling */}
            <div className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-[var(--line)] bg-[rgba(10,10,10,0.92)] px-7 py-3 backdrop-blur-xl">
              <div className="flex min-w-0 items-baseline gap-3">
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
                  run
                </span>
                <span className="truncate font-mono text-[12.5px] tracking-tight text-[var(--paper)]">
                  {run.runId}
                </span>
              </div>
              <span
                className={cn(
                  "shrink-0 border px-2.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.22em]",
                  outcomeBadge(run.finalOutcome).tone,
                  outcomeBadge(run.finalOutcome).border,
                )}
              >
                {outcomeBadge(run.finalOutcome).label}
              </span>
            </div>

            {/* Run heading */}
            <div className="border-b border-[var(--line)] px-7 py-6">
              <p className="max-w-[72ch] font-display text-[19px] font-medium leading-snug tracking-tight text-[var(--paper)]">
                {run.headline}
              </p>

              {/* Info row */}
              <dl className="mt-6 grid grid-cols-4 divide-x divide-[var(--line)] border-y border-[var(--line)]">
                {[
                  {
                    label: "Risk level",
                    value: run.risk.level,
                    mono: false,
                    big: false,
                    tone:
                      run.risk.level === "critical" || run.risk.level === "elevated"
                        ? "text-[var(--bad)]"
                        : run.risk.level === "guarded"
                          ? "text-[var(--warn)]"
                          : "text-[var(--green)]",
                  },
                  { label: "Source", value: run.source, mono: true, big: false },
                  { label: "Trace path", value: run.tracePath, mono: true, big: false },
                  { label: "Events", value: String(run.eventCount), mono: false, big: true },
                ].map(({ label, value, mono, big, tone }, i) => (
                  <div key={label} className={cn("py-3", i === 0 ? "pr-4" : "px-4")}>
                    <dt className="label">{label}</dt>
                    <dd
                      className={cn(
                        "mt-1.5 break-all",
                        big
                          ? "numeral text-[20px] tabular-nums text-[var(--paper)]"
                          : mono
                            ? "font-mono text-[11px] text-[var(--paper-soft)]"
                            : "text-[12px] text-[var(--paper-soft)]",
                        tone,
                      )}
                    >
                      {big ? value : <span className={tone ? "uppercase tracking-[0.05em]" : ""}>{value}</span>}
                    </dd>
                  </div>
                ))}
              </dl>

              {/* Actions */}
              <div className="mt-5 flex flex-wrap gap-2">
                {[
                  {
                    label: "copy run id",
                    key: "runId",
                    action: () => copy(run.runId, "runId"),
                    icon: copied === "runId" ? Check : Copy,
                  },
                  {
                    label: "copy trace path",
                    key: "tracePath",
                    action: () => copy(run.tracePath, "tracePath"),
                    icon: copied === "tracePath" ? Check : Copy,
                  },
                  {
                    label: "open raw trace",
                    key: "rawTrace",
                    action: () => setView("trace"),
                    icon: null,
                  },
                  {
                    label: firstRiskyStep ? "next risky action" : "no risky actions",
                    key: "nextRisky",
                    action: handleNextRisky,
                    icon: null,
                    disabled: !firstRiskyStep,
                  },
                ].map(({ label, key, action, icon: Icon, disabled }) => {
                  const justCopied =
                    (key === "runId" && copied === "runId") ||
                    (key === "tracePath" && copied === "tracePath");
                  return (
                    <button
                      key={key}
                      type="button"
                      disabled={disabled}
                      onClick={action}
                      className={cn(
                        "flex items-center gap-1.5 border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors",
                        disabled
                          ? "cursor-default border-[var(--line)] text-[var(--paper-faint)]"
                          : "border-[var(--line-strong)] text-[var(--paper-soft)] hover:border-[var(--green)]/60 hover:bg-[var(--green-faint)] hover:text-[var(--paper)]",
                        justCopied && "border-[var(--green)]/60 text-[var(--green)] bg-[var(--green-faint)]",
                      )}
                    >
                      {Icon && <Icon className="size-2.5" />}
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-end gap-7 border-b border-[var(--line)] px-7">
              {VIEWS.map(({ value: v, label }) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setView(v)}
                  className={cn(
                    "relative pb-3 pt-3 font-mono text-[10.5px] uppercase tracking-[0.22em] transition-colors",
                    view === v
                      ? "text-[var(--paper)]"
                      : "text-[var(--paper-mute)] hover:text-[var(--paper-soft)]",
                  )}
                >
                  {label}
                  {view === v && (
                    <span
                      className="absolute -bottom-px left-0 right-0 h-[2px] bg-[var(--green)] shadow-[0_0_10px_var(--green-glow)]"
                      aria-hidden
                    />
                  )}
                </button>
              ))}
              {loading && (
                <span className="ml-auto self-center font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
                  refreshing
                </span>
              )}
            </div>

            {/* Tab content */}
            <div className="px-7 py-7">
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
