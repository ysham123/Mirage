import { Activity, ShieldCheck } from "lucide-react";

import { Card } from "@/components/ui/card";
import type { AgentHealth } from "@/types/console";

interface HealthStripProps {
  health: AgentHealth;
}

export function HealthStrip({ health }: HealthStripProps) {
  return (
    <Card className="flex items-center gap-4 p-4">
      <div className="flex size-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-[var(--accent)]">
        {health.status === "stable" ? <ShieldCheck className="size-5" /> : <Activity className="size-5" />}
      </div>
      <div className="min-w-0">
        <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Agent Health</p>
        <h3 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-white">{health.label}</h3>
        <p className="text-sm text-[var(--text-secondary)]">{health.summary}</p>
      </div>
    </Card>
  );
}
