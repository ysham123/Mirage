"use client";

import type { CSSProperties } from "react";
import type { RiskSnapshot } from "@/types/console";

interface RiskGaugeProps {
  risk: RiskSnapshot;
}

export function RiskGauge({ risk }: RiskGaugeProps) {
  const gradient =
    risk.level === "critical"
      ? ["rgba(255,89,126,.92)", "rgba(255,133,71,.92)"]
      : risk.level === "elevated"
        ? ["rgba(255,183,76,.9)", "rgba(255,120,88,.9)"]
        : risk.level === "guarded"
          ? ["rgba(111,231,255,.9)", "rgba(32,125,255,.88)"]
          : ["rgba(83,255,197,.92)", "rgba(111,231,255,.88)"];

  return (
    <div className="flex items-center gap-5">
      <div
        className="relative flex size-36 items-center justify-center rounded-full"
        style={
          {
            "--risk": String(Math.max(36, Math.round((risk.score / 100) * 320) + 36)),
            background: `conic-gradient(from 210deg, rgba(255,255,255,.05) 0deg, rgba(255,255,255,.05) 35deg, ${gradient[0]} 35deg, ${gradient[1]} calc(var(--risk) * 1deg), rgba(255,255,255,.05) calc(var(--risk) * 1deg))`,
          } as CSSProperties
        }
      >
        <div className="absolute inset-[10px] rounded-full bg-[rgba(4,8,12,.94)] shadow-[inset_0_1px_0_rgba(255,255,255,.06)]" />
        <div className="relative text-center">
          <p className="text-4xl font-semibold tracking-[-0.06em] text-white">{risk.score}</p>
          <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">risk score</p>
        </div>
      </div>
      <div className="space-y-2">
        <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Risk posture</p>
        <h3 className="text-2xl font-semibold tracking-[-0.04em] text-white">{risk.level}</h3>
        <p className="max-w-xs text-sm text-[var(--text-secondary)]">
          Mirage assigns risk from the final outcome, the number of risky steps, and whether suppressions are already active.
        </p>
      </div>
    </div>
  );
}
