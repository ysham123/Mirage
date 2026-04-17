"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

import { Card } from "@/components/ui/card";
import type { PolicyFailure } from "@/types/console";

interface FrictionChartProps {
  policyFailures: PolicyFailure[];
}

export function FrictionChart({ policyFailures }: FrictionChartProps) {
  const data = policyFailures.slice(0, 4).map((failure) => ({
    name: failure.name,
    count: failure.count,
  }));

  return (
    <Card className="p-4">
      <div className="mb-4">
        <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Policy Friction</p>
        <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-white">Most frequent policy failures</h3>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical">
            <XAxis type="number" stroke="#7e92a8" tickLine={false} axisLine={false} allowDecimals={false} />
            <YAxis dataKey="name" type="category" stroke="#7e92a8" tickLine={false} axisLine={false} width={120} />
            <Bar dataKey="count" fill="#56d8ff" radius={[0, 14, 14, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
