"use client";

import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { springs } from "@/lib/motion";
import type { ConsoleOverview, ConsoleRun, ConsoleView, SideEffect } from "@/types/console";

import { FrictionChart } from "../telemetry/friction-chart";
import { HealthStrip } from "../telemetry/health-strip";
import { LiveMetrics } from "../telemetry/live-metrics";
import { OutcomeChart } from "../telemetry/outcome-chart";
import { ConfidenceRing } from "./confidence-ring";
import { EffectTimeline } from "./effect-timeline";
import { RiskGauge } from "./risk-gauge";

interface SideEffectsPanelProps {
  run: ConsoleRun | null;
  overview: ConsoleOverview | null;
  view: ConsoleView;
  focusedStepIndex: number | null;
  className?: string;
  onViewChange: (view: ConsoleView) => void;
  onFocusStep: (stepIndex: number) => void;
  onSuppress: (effect: SideEffect) => void;
}

const tabs: Array<{ value: ConsoleView; label: string }> = [
  { value: "overview", label: "Overview" },
  { value: "timeline", label: "Timeline" },
  { value: "trace", label: "Trace" },
];

export function SideEffectsPanel({
  run,
  overview,
  view,
  focusedStepIndex,
  className,
  onViewChange,
  onFocusStep,
  onSuppress,
}: SideEffectsPanelProps) {
  if (!run) {
    return (
      <Card className={className ? `${className} p-6` : "p-6"}>
        <div className="flex items-start gap-4">
          <div className="flex size-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-[var(--accent)]">
            <ShieldAlert className="size-5" />
          </div>
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Side Effects</p>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.04em] text-white">Select a run to inspect live metrics</h3>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Risk gauges, confidence rings, suppression controls, and trace drilldowns appear here once a run is selected.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <aside className={className}>
      <Card className="flex h-full flex-col overflow-hidden p-5">
        <div className="flex items-start justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Side Effects Panel</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.05em] text-white">Live metrics and suppression</h2>
          </div>
          <Badge tone={run.finalOutcome === "allowed" ? "success" : run.finalOutcome === "config_error" ? "critical" : "warning"}>
            {run.risk.level}
          </Badge>
        </div>

        <div className="mt-4 flex gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.value}
              className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] transition ${
                view === tab.value
                  ? "border-[var(--border-strong)] bg-[rgba(111,231,255,.14)] text-white"
                  : "border-white/10 bg-white/[0.03] text-[var(--text-secondary)] hover:bg-white/[0.06] hover:text-white"
              }`}
              onClick={() => onViewChange(tab.value)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        <motion.div
          key={view}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 flex-1 overflow-y-auto pr-1"
          initial={{ opacity: 0, y: 10 }}
          transition={springs.soft}
        >
          {view === "overview" ? (
            <div className="space-y-4">
              <Card className="p-5">
                <RiskGauge risk={run.risk} />
              </Card>
              <div className="grid gap-4 xl:grid-cols-[1fr,1fr]">
                <ConfidenceRing label="health confidence" value={run.agentHealth.confidence} />
                <ConfidenceRing
                  label="effect confidence"
                  value={
                    run.sideEffects.reduce((total, effect) => total + effect.confidence, 0) /
                    Math.max(run.sideEffects.length, 1)
                  }
                />
              </div>
              <HealthStrip health={run.agentHealth} />
              <LiveMetrics run={run} />
              <OutcomeChart run={run} />
              <FrictionChart policyFailures={overview?.topPolicyFailures ?? []} />
            </div>
          ) : null}

          {view === "timeline" ? (
            <EffectTimeline
              effects={run.sideEffects}
              focusedStepIndex={focusedStepIndex}
              onFocusStep={onFocusStep}
              onSuppress={onSuppress}
            />
          ) : null}

          {view === "trace" ? (
            <Card className="p-4">
              <p className="mb-3 text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Trace JSON</p>
              <pre className="overflow-x-auto rounded-[1.2rem] border border-white/10 bg-[rgba(0,0,0,.42)] p-4 text-[13px] text-[rgb(222,245,255)]">
                {JSON.stringify(run.trace, null, 2)}
              </pre>
            </Card>
          ) : null}
        </motion.div>
      </Card>
    </aside>
  );
}
