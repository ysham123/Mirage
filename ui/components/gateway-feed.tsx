"use client";

import { useEffect, useState } from "react";

import { fetchGatewayFeed } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { GatewayFeedEvent, RunOutcome } from "@/types/console";

const POLL_INTERVAL_MS = 2000;

function adaptGatewayEvent(payload: Record<string, unknown>): GatewayFeedEvent {
  return {
    runId: String(payload.run_id ?? ""),
    timestamp: payload.timestamp ? String(payload.timestamp) : null,
    mode: (payload.mode === "enforce" ? "enforce" : "passthrough") as GatewayFeedEvent["mode"],
    outcome: (payload.outcome as RunOutcome) ?? "unknown",
    method: payload.method ? String(payload.method) : null,
    path: payload.path ? String(payload.path) : null,
    upstreamUrl: payload.upstream_url ? String(payload.upstream_url) : null,
    upstreamStatus: payload.upstream_status === null || payload.upstream_status === undefined
      ? null
      : Number(payload.upstream_status),
    statusCode: payload.status_code === null || payload.status_code === undefined
      ? null
      : Number(payload.status_code),
    policyPassed: Boolean(payload.policy_passed),
    timeToDecideUs: payload.time_to_decide_us === null || payload.time_to_decide_us === undefined
      ? null
      : Number(payload.time_to_decide_us),
    failedDecisions: Array.isArray(payload.failed_decisions)
      ? (payload.failed_decisions as Array<Record<string, unknown>>).map((decision) => ({
          name: decision.name ? String(decision.name) : null,
          field: decision.field ? String(decision.field) : null,
          operator: decision.operator ? String(decision.operator) : null,
          message: decision.message ? String(decision.message) : null,
        }))
      : [],
    message: payload.message ? String(payload.message) : null,
  };
}

function outcomeTone(outcome: RunOutcome): { tone: string; border: string; label: string } {
  if (outcome === "allowed")
    return { tone: "text-[var(--green)]", border: "border-[var(--green)]/40", label: "allowed" };
  if (outcome === "blocked")
    return { tone: "text-[var(--bad)]", border: "border-[var(--bad)]/40", label: "blocked" };
  if (outcome === "flagged")
    return { tone: "text-[var(--warn)]", border: "border-[var(--warn)]/40", label: "flagged" };
  if (outcome === "error")
    return { tone: "text-[var(--bad)]", border: "border-[var(--bad)]/40", label: "error" };
  return { tone: "text-[var(--paper-mute)]", border: "border-[var(--line-strong)]", label: outcome };
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleTimeString();
  } catch {
    return ts;
  }
}

export function GatewayFeed() {
  const [events, setEvents] = useState<GatewayFeedEvent[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await fetchGatewayFeed(100);
        if (cancelled) return;
        const raw = Array.isArray(payload.events) ? (payload.events as Array<Record<string, unknown>>) : [];
        setEvents(raw.map(adaptGatewayEvent));
        setLastUpdated(new Date());
        setError(null);
      } catch (exc) {
        if (cancelled) return;
        setError(String(exc));
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
    <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between border-b border-[var(--line)] px-7 py-5">
        <div>
          <h2 className="font-display text-[19px] font-medium tracking-tight text-[var(--paper)]">
            Gateway live feed
          </h2>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
            passthrough + enforce events, newest first
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
            polled · 2s
          </span>
          {lastUpdated && (
            <span className="font-mono text-[10px] tabular-nums text-[var(--paper-faint)]">
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {error && (
        <div className="border-b border-[var(--bad)]/30 bg-[var(--bad)]/10 px-7 py-3 font-mono text-[11px] text-[var(--bad)]">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center">
            <p className="font-display text-[20px] font-medium leading-none tracking-tight text-[var(--paper)]">
              No gateway events yet
            </p>
            <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--paper-mute)]">
              start the gateway with `mirage gateway --upstream ...`
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-[var(--line)]">
            {events.map((event, index) => {
              const badge = outcomeTone(event.outcome);
              return (
                <li
                  key={`${event.runId}-${event.timestamp}-${index}`}
                  className="px-7 py-4 transition-colors hover:bg-[var(--surface)]"
                >
                  <div className="flex items-start justify-between gap-6">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-3">
                        <span className="font-mono text-[10.5px] tabular-nums text-[var(--paper-faint)]">
                          {formatTimestamp(event.timestamp)}
                        </span>
                        <span className="font-mono text-[12.5px] font-medium text-[var(--paper)]">
                          <span className="text-[var(--paper-faint)]">{event.method}</span>{" "}
                          {event.path}
                        </span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--paper-mute)]">
                          {event.mode}
                        </span>
                      </div>
                      <div className="mt-1 flex items-baseline gap-4 font-mono text-[10.5px] text-[var(--paper-mute)]">
                        <span>run · {event.runId}</span>
                        {event.upstreamUrl && (
                          <span className="truncate">upstream · {event.upstreamUrl}</span>
                        )}
                        {event.timeToDecideUs !== null && (
                          <span>ttd · {event.timeToDecideUs}us</span>
                        )}
                      </div>
                      {event.failedDecisions.length > 0 && (
                        <p className="mt-2 max-w-[68ch] text-[12px] leading-relaxed text-[var(--paper-soft)]">
                          {event.failedDecisions
                            .map((decision) => `${decision.name}: ${decision.message}`)
                            .join(" | ")}
                        </p>
                      )}
                    </div>
                    <span
                      className={cn(
                        "shrink-0 border px-2.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.22em]",
                        badge.tone,
                        badge.border,
                      )}
                    >
                      {badge.label}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
