export type RunOutcome = "allowed" | "policy_violation" | "unmatched_route" | "config_error" | "unknown";
export type ConsoleView = "overview" | "timeline" | "trace";
export type QueueFilter = "all" | "risky" | "allowed" | "unmatched_route";
export type ChatRole = "system" | "user" | "assistant";

export interface OverviewSummary {
  totalRuns: number;
  totalActions: number;
  allowed: number;
  policyViolation: number;
  unmatchedRoute: number;
  configError: number;
  riskyRuns: number;
  suppressedActions: number;
}

export interface TopEndpoint {
  label: string;
  description: string;
  count: number;
  method: string;
  path: string;
}

export interface PolicyFailure {
  name: string;
  count: number;
  description: string;
  field?: string | null;
}

export interface RunListItem {
  runId: string;
  outcome: RunOutcome;
  headline: string;
  timestamp?: string | null;
  method?: string | null;
  path?: string | null;
  eventCount: number;
  suppressedCount: number;
}

export interface SuppressionState {
  suppressed: boolean;
  reason: string;
  suppressedAt: string;
  stepIndex: number;
}

export interface SideEffect {
  id: string;
  stepIndex: number;
  name: string;
  method: string;
  path: string;
  payload: unknown;
  statusCode?: number | null;
  responseBody: unknown;
  outcome: RunOutcome;
  severity: "nominal" | "medium" | "high" | "critical" | "suppressed" | "low";
  message?: string | null;
  decisionSummary?: string | null;
  decisions: Array<Record<string, unknown>>;
  matchedMock?: string | null;
  policyPassed: boolean;
  timestamp?: string | null;
  confidence: number;
  suppressed: boolean;
  suppression?: SuppressionState | null;
  status: string;
}

export interface RiskSnapshot {
  score: number;
  level: "stable" | "guarded" | "elevated" | "critical";
  totalSteps: number;
  riskySteps: number;
  suppressedSteps: number;
  allowedSteps: number;
}

export interface AgentHealth {
  status: "stable" | "watch" | "critical";
  summary: string;
  confidence: number;
  label: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  title?: string;
  body: string;
  createdAt?: string;
  tone?: "neutral" | "success" | "warning" | "critical";
  sideEffectId?: string;
  streaming?: boolean;
}

export interface ConsoleRun {
  runId: string;
  source: string;
  tracePath: string;
  headline: string;
  finalOutcome: RunOutcome;
  eventCount: number;
  trace: Record<string, unknown>;
  sideEffects: SideEffect[];
  risk: RiskSnapshot;
  agentHealth: AgentHealth;
  messages: ChatMessage[];
}

export interface ConsoleOverview {
  summary: OverviewSummary;
  runs: RunListItem[];
  topEndpoints: TopEndpoint[];
  topPolicyFailures: PolicyFailure[];
}

export interface StreamEvent {
  event: "status" | "message_delta" | "step" | "metric" | "complete";
  data: Record<string, unknown>;
}
