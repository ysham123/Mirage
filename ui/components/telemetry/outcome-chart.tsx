"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { Card } from "@/components/ui/card";
import type { ConsoleRun } from "@/types/console";

interface OutcomeChartProps {
  run: ConsoleRun;
}

export function OutcomeChart({ run }: OutcomeChartProps) {
  const data = [
    { name: "Allowed", value: run.risk.allowedSteps, color: "#6fffe0" },
    { name: "Risky", value: run.risk.riskySteps, color: "#ffb56a" },
    { name: "Suppressed", value: run.risk.suppressedSteps, color: "#6fe7ff" },
  ];

  return (
    <Card className="p-4">
      <div className="mb-4">
        <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Outcome Visualizer</p>
        <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-white">Side-effect distribution</h3>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="name" stroke="#7e92a8" tickLine={false} axisLine={false} />
            <YAxis stroke="#7e92a8" tickLine={false} axisLine={false} allowDecimals={false} />
            <Bar dataKey="value" radius={[14, 14, 4, 4]}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
