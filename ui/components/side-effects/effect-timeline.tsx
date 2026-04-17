"use client";

import { Activity, ArrowRight, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SideEffect } from "@/types/console";

import { SuppressAction } from "./suppress-action";

interface EffectTimelineProps {
  effects: SideEffect[];
  focusedStepIndex: number | null;
  onFocusStep: (stepIndex: number) => void;
  onSuppress: (effect: SideEffect) => void;
}

function toneForEffect(effect: SideEffect) {
  if (effect.suppressed) {
    return "suppressed";
  }
  if (effect.outcome === "allowed") {
    return "success";
  }
  if (effect.outcome === "config_error") {
    return "critical";
  }
  return "warning";
}

export function EffectTimeline({ effects, focusedStepIndex, onFocusStep, onSuppress }: EffectTimelineProps) {
  return (
    <div className="space-y-3">
      {effects.map((effect) => (
        <button
          key={effect.id}
          className={cn(
            "relative w-full rounded-[1.4rem] border p-4 text-left transition",
            focusedStepIndex === effect.stepIndex
              ? "border-[var(--border-strong)] bg-[linear-gradient(180deg,rgba(111,231,255,.12),rgba(255,255,255,.02))]"
              : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]",
          )}
          onClick={() => onFocusStep(effect.stepIndex)}
          type="button"
        >
          {effect.outcome !== "allowed" && !effect.suppressed ? <div className="risk-bloom" aria-hidden="true" /> : null}
          <div className="relative flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="inline-flex size-8 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[var(--accent)]">
                  {effect.outcome === "allowed" ? <Activity className="size-4" /> : <ShieldAlert className="size-4" />}
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{effect.name}</p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {effect.method} {effect.path}
                  </p>
                </div>
              </div>
              <p className="mt-3 text-sm text-[var(--text-secondary)]">
                {effect.decisionSummary || effect.message || "Mirage captured this side effect for review."}
              </p>
            </div>

            <div className="flex shrink-0 flex-col items-end gap-3">
              <Badge tone={toneForEffect(effect)}>{effect.suppressed ? "suppressed" : effect.outcome.replaceAll("_", " ")}</Badge>
              <SuppressAction effect={effect} onSuppress={onSuppress} />
            </div>
          </div>

          <div className="relative mt-4 flex items-center gap-4 text-xs text-[var(--text-muted)]">
            <span>{Math.round(effect.confidence * 100)}% confidence</span>
            <span className="inline-flex items-center gap-1">
              <ArrowRight className="size-3" />
              event {effect.stepIndex}
            </span>
            {effect.timestamp ? <span>{new Date(effect.timestamp).toLocaleString()}</span> : null}
          </div>
        </button>
      ))}
    </div>
  );
}
