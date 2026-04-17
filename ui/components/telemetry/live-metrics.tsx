import { Card } from "@/components/ui/card";
import type { ConsoleRun } from "@/types/console";

interface LiveMetricsProps {
  run: ConsoleRun;
}

export function LiveMetrics({ run }: LiveMetricsProps) {
  const metrics = [
    { label: "Allowed", value: run.risk.allowedSteps },
    { label: "Risky", value: run.risk.riskySteps },
    { label: "Suppressed", value: run.risk.suppressedSteps },
    { label: "Trace Events", value: run.eventCount },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {metrics.map((metric) => (
        <Card key={metric.label} className="p-4">
          <p className="text-[0.68rem] uppercase tracking-[0.24em] text-[var(--text-muted)]">{metric.label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-[-0.05em] text-white">{metric.value}</p>
        </Card>
      ))}
    </div>
  );
}
