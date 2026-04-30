import type {
  AgentHealth,
  ChatMessage,
  ConsoleOverview,
  ConsoleRun,
  PolicyFailure,
  RiskSnapshot,
  RunListItem,
  RunOutcome,
  SideEffect,
  TopEndpoint,
} from "@/types/console";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asArray<T = Record<string, unknown>>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function normalizeOutcome(value: unknown): RunOutcome {
  if (
    value === "allowed" ||
    value === "policy_violation" ||
    value === "unmatched_route" ||
    value === "config_error" ||
    value === "blocked" ||
    value === "flagged" ||
    value === "error"
  ) {
    return value;
  }
  return "unknown";
}

export function adaptOverview(payload: Record<string, unknown>): ConsoleOverview {
  const summary = asRecord(payload.summary);
  const runs = asArray<Record<string, unknown>>(payload.recent_runs).map(adaptRunListItem);
  const endpoints = asArray<Record<string, unknown>>(payload.top_endpoints).map(adaptTopEndpoint);
  const policyFailures = asArray<Record<string, unknown>>(payload.top_policy_failures).map(adaptPolicyFailure);

  return {
    summary: {
      totalRuns: Number(summary.total_runs ?? 0),
      totalActions: Number(summary.total_actions ?? 0),
      allowed: Number(summary.allowed ?? 0),
      policyViolation: Number(summary.policy_violation ?? 0),
      unmatchedRoute: Number(summary.unmatched_route ?? 0),
      configError: Number(summary.config_error ?? 0),
      blocked: Number(summary.blocked ?? 0),
      flagged: Number(summary.flagged ?? 0),
      error: Number(summary.error ?? 0),
      riskyRuns: Number(summary.risky_runs ?? 0),
      suppressedActions: Number(summary.suppressed_actions ?? 0),
    },
    runs,
    topEndpoints: endpoints,
    topPolicyFailures: policyFailures,
  };
}

function adaptRunListItem(payload: Record<string, unknown>): RunListItem {
  const request = asRecord(payload.request);
  return {
    runId: String(payload.run_id ?? ""),
    outcome: normalizeOutcome(payload.outcome),
    headline: String(payload.headline ?? "Mirage run review."),
    timestamp: payload.timestamp ? String(payload.timestamp) : null,
    method: request.method ? String(request.method) : null,
    path: request.path ? String(request.path) : null,
    eventCount: Number(payload.event_count ?? payload.trace_event_count ?? 0),
    suppressedCount: Number(payload.suppressed_count ?? 0),
  };
}

function adaptTopEndpoint(payload: Record<string, unknown>): TopEndpoint {
  return {
    label: String(payload.label ?? ""),
    description: String(payload.description ?? ""),
    count: Number(payload.count ?? 0),
    method: String(payload.method ?? "GET"),
    path: String(payload.path ?? "/"),
    violationCount: Number(payload.policy_violation_count ?? 0),
  };
}

function adaptPolicyFailure(payload: Record<string, unknown>): PolicyFailure {
  return {
    name: String(payload.name ?? "unknown"),
    count: Number(payload.count ?? 0),
    description: String(payload.description ?? ""),
    field: payload.field ? String(payload.field) : null,
  };
}

export function adaptRun(payload: Record<string, unknown>): ConsoleRun {
  const meta = asRecord(payload.meta);
  const summary = asRecord(payload.summary);
  const risk = adaptRisk(asRecord(payload.risk));
  const agentHealth = adaptHealth(asRecord(payload.agent_health));
  const sideEffects = asArray<Record<string, unknown>>(payload.side_effects).map(adaptSideEffect);
  const trace = asRecord(payload.trace);

  return {
    runId: String(payload.run_id ?? ""),
    source: String(meta.source ?? "trace metrics review"),
    tracePath: String(payload.trace_path ?? summary.trace_path ?? ""),
    headline: String(summary.headline ?? "Mirage run review."),
    finalOutcome: normalizeOutcome(summary.final_outcome),
    eventCount: Number(meta.event_count ?? summary.trace_event_count ?? sideEffects.length),
    trace,
    sideEffects,
    risk,
    agentHealth,
    messages: buildMessages(payload, sideEffects),
  };
}

function adaptRisk(payload: Record<string, unknown>): RiskSnapshot {
  return {
    score: Number(payload.score ?? 0),
    level: (payload.level as RiskSnapshot["level"]) ?? "stable",
    totalSteps: Number(payload.total_steps ?? 0),
    riskySteps: Number(payload.risky_steps ?? 0),
    suppressedSteps: Number(payload.suppressed_steps ?? 0),
    allowedSteps: Number(payload.allowed_steps ?? 0),
  };
}

function adaptHealth(payload: Record<string, unknown>): AgentHealth {
  return {
    status: (payload.status as AgentHealth["status"]) ?? "stable",
    summary: String(payload.summary ?? "Agent actions are tracking inside configured guardrails."),
    confidence: Number(payload.confidence ?? 0.75),
    label: String(payload.label ?? "Nominal"),
  };
}

function adaptSideEffect(payload: Record<string, unknown>): SideEffect {
  const suppressionPayload = asRecord(payload.suppression);
  return {
    id: String(payload.id ?? ""),
    stepIndex: Number(payload.step_index ?? 0),
    name: String(payload.name ?? "Action"),
    method: String(payload.method ?? "GET"),
    path: String(payload.path ?? "/"),
    payload: payload.payload ?? null,
    statusCode: payload.status_code ? Number(payload.status_code) : null,
    responseBody: payload.response_body ?? null,
    outcome: normalizeOutcome(payload.outcome),
    severity: (payload.severity as SideEffect["severity"]) ?? "low",
    message: payload.message ? String(payload.message) : null,
    decisionSummary: payload.decision_summary ? String(payload.decision_summary) : null,
    decisions: asArray<Record<string, unknown>>(payload.decisions),
    matchedMock: payload.matched_mock ? String(payload.matched_mock) : null,
    policyPassed: Boolean(payload.policy_passed),
    timestamp: payload.timestamp ? String(payload.timestamp) : null,
    confidence: Number(payload.confidence ?? 0.5),
    suppressed: Boolean(payload.suppressed),
    suppression: suppressionPayload.suppressed
      ? {
          suppressed: true,
          reason: String(suppressionPayload.reason ?? ""),
          suppressedAt: String(suppressionPayload.suppressed_at ?? ""),
          stepIndex: Number(suppressionPayload.step_index ?? payload.step_index ?? 0),
        }
      : null,
    status: String(payload.status ?? payload.outcome ?? "unknown"),
  };
}

export function buildMessages(payload: Record<string, unknown>, sideEffects: SideEffect[]): ChatMessage[] {
  const summary = asRecord(payload.summary);
  const meta = asRecord(payload.meta);
  const intro: ChatMessage = {
    id: `${payload.run_id}-intro`,
    role: "assistant",
    title: String(summary.headline ?? "Mirage run review."),
    body: [
      `Mirage is tracking \`${String(payload.run_id ?? "")}\` from **${String(meta.source ?? "trace metrics review")}**.`,
      "",
      `- Final outcome: **${formatOutcome(normalizeOutcome(summary.final_outcome))}**`,
      `- Trace path: \`${String(summary.trace_path ?? payload.trace_path ?? "")}\``,
      `- Actions intercepted: **${sideEffects.length}**`,
    ].join("\n"),
    tone: toneForOutcome(normalizeOutcome(summary.final_outcome)),
  };

  const stepMessages = sideEffects.flatMap<ChatMessage>((effect) => {
    const user: ChatMessage = {
      id: `${effect.id}-request`,
      role: "user",
      title: `${effect.method} ${effect.path}`,
      body: [
        `### ${effect.name}`,
        "",
        "```http",
        `${effect.method} ${effect.path}`,
        "```",
        effect.payload ? ["```json", JSON.stringify(effect.payload, null, 2), "```"].join("\n") : "_No payload_",
      ].join("\n"),
      createdAt: effect.timestamp ?? undefined,
      sideEffectId: effect.id,
    };
    const assistant: ChatMessage = {
      id: `${effect.id}-response`,
      role: "assistant",
      title: effect.suppressed ? "Suppressed" : formatOutcome(effect.outcome),
      body: buildEffectSummary(effect),
      createdAt: effect.timestamp ?? undefined,
      tone: effect.suppressed ? "warning" : toneForOutcome(effect.outcome),
      sideEffectId: effect.id,
    };
    return [user, assistant];
  });

  return [intro, ...stepMessages];
}

function buildEffectSummary(effect: SideEffect) {
  const responseBlock = effect.responseBody
    ? ["```json", JSON.stringify(effect.responseBody, null, 2), "```"].join("\n")
    : "_No response body_";

  const lines = [
    `**Outcome:** ${effect.suppressed ? "Suppressed for review" : formatOutcome(effect.outcome)}`,
    "",
    effect.decisionSummary || effect.message || "Mirage captured this side effect without additional commentary.",
    "",
    `- Confidence ring: **${Math.round(effect.confidence * 100)}%**`,
    `- Mock: \`${effect.matchedMock ?? "none"}\``,
    `- Status code: **${effect.statusCode ?? "n/a"}**`,
  ];

  if (effect.suppression) {
    lines.push(`- Suppression: ${effect.suppression.reason}`);
  }

  lines.push("", responseBlock);
  return lines.join("\n");
}

function toneForOutcome(outcome: RunOutcome): ChatMessage["tone"] {
  if (outcome === "allowed") {
    return "success";
  }
  if (outcome === "policy_violation" || outcome === "unmatched_route" || outcome === "flagged") {
    return "warning";
  }
  if (outcome === "config_error" || outcome === "error" || outcome === "blocked") {
    return "critical";
  }
  return "neutral";
}

export function formatOutcome(outcome: RunOutcome) {
  return outcome.replaceAll("_", " ");
}

export function respondToPrompt(prompt: string, run: ConsoleRun): string {
  const lower = prompt.toLowerCase();
  if (lower.includes("risk") || lower.includes("unsafe")) {
    if (!run.sideEffects.some((effect) => effect.outcome !== "allowed")) {
      return "This run is clean. Mirage did not observe any risky side effects.";
    }
    return [
      `Mirage marked **${run.risk.riskySteps}** side effect(s) as risky.`,
      "",
      ...run.sideEffects
        .filter((effect) => effect.outcome !== "allowed")
        .map(
          (effect) =>
            `- **${effect.name}** on \`${effect.method} ${effect.path}\`: ${effect.decisionSummary || effect.message || "Needs review."}`,
        ),
    ].join("\n");
  }

  if (lower.includes("trace")) {
    return `The trace for this run is stored at \`${run.tracePath}\`. Switch to the Trace view to inspect the full JSON payload.`;
  }

  if (lower.includes("suppress")) {
    const nextRisk = run.sideEffects.find((effect) => effect.outcome !== "allowed" && !effect.suppressed);
    if (!nextRisk) {
      return "There are no unsuppressed risky side effects in the current run.";
    }
    return `Use the suppress control on **${nextRisk.name}** to mute that side effect while the team investigates.`;
  }

  return [
    `Mirage is reviewing **${run.runId}**.`,
    "",
    `- Health: **${run.agentHealth.label}**`,
    `- Risk score: **${run.risk.score}**`,
    `- Suppressed actions: **${run.risk.suppressedSteps}**`,
    "",
    "Ask about `risk`, `trace`, or `suppress` for a more targeted summary.",
  ].join("\n");
}

export function mergeMessageBodies(snapshotBody: string, streamedBody: string): string {
  if (!snapshotBody) return streamedBody;
  if (!streamedBody) return snapshotBody;
  if (snapshotBody === streamedBody) return snapshotBody;
  if (streamedBody.includes(snapshotBody)) return streamedBody;
  if (snapshotBody.includes(streamedBody)) return snapshotBody;

  const maxOverlap = Math.min(snapshotBody.length, streamedBody.length);
  for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
    if (snapshotBody.slice(-overlap) === streamedBody.slice(0, overlap)) {
      return `${snapshotBody}${streamedBody.slice(overlap)}`;
    }
  }
  for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
    if (streamedBody.slice(-overlap) === snapshotBody.slice(0, overlap)) {
      return `${streamedBody}${snapshotBody.slice(overlap)}`;
    }
  }
  return `${snapshotBody}${streamedBody}`;
}
