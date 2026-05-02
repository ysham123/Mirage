"use client";

import { useEffect, useState } from "react";

import { fetchContainmentWindows } from "@/lib/api";
import { cn } from "@/lib/utils";

const WINDOWS = [
  { key: "window_24h", label: "24h" },
  { key: "window_7d", label: "7d" },
  { key: "window_30d", label: "30d" },
] as const;

const POLL_INTERVAL_MS = 15_000;

function formatRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return "n/a";
  return `${(rate * 100).toFixed(1)}%`;
}

function rateTone(rate: number | null | undefined): string {
  if (rate === null || rate === undefined) return "text-[var(--paper-mute)]";
  if (rate >= 0.95) return "text-[var(--green)]";
  if (rate >= 0.8) return "text-[var(--warn)]";
  return "text-[var(--bad)]";
}

export function ContainmentDashboard() {
  const [windows, setWindows] = useState<Record<string, number | null>>({});

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await fetchContainmentWindows();
        if (cancelled) return;
        setWindows(payload as Record<string, number | null>);
      } catch {
        // backend may not be ready
      }
    };
    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <section
      aria-label="Fleet containment rate"
      className="border-b border-[var(--line)] px-5 py-4"
    >
      <div className="flex items-baseline justify-between">
        <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
          fleet containment
        </h3>
        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--paper-faint)]">
          blocked / decisions
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-3">
        {WINDOWS.map(({ key, label }) => {
          const rate = windows[key];
          return (
            <div
              key={key}
              className="flex flex-col gap-1 border border-[var(--line)] bg-[var(--surface)] px-3 py-2.5"
            >
              <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                {label}
              </span>
              <span
                className={cn(
                  "numeral text-[18px] tabular-nums leading-none",
                  rateTone(rate),
                )}
              >
                {formatRate(rate)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
