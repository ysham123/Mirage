import type { StreamEvent } from "@/types/console";

const PUBLIC_API_BASE = process.env.NEXT_PUBLIC_MIRAGE_API_BASE_URL ?? "";

function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  const url = new URL(path, PUBLIC_API_BASE || window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  if (!PUBLIC_API_BASE) {
    return `${url.pathname}${url.search}`;
  }
  return url.toString();
}

async function parseResponseBody(response: Response) {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function extractErrorMessage(payload: unknown, status: number) {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.error === "string" && record.error.trim()) {
      return record.error;
    }
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message;
    }
  }

  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  return `Request failed: ${status}`;
}

async function requestJson<T>(path: string, init?: RequestInit, params?: Record<string, string | number | undefined>) {
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && init.body !== null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const response = await fetch(buildUrl(path, params), {
    ...init,
    headers,
  });
  const payload = await parseResponseBody(response);

  if (!response.ok) {
    throw new Error(extractErrorMessage(payload, response.status));
  }
  return payload as T;
}

export function fetchOverview() {
  return requestJson<Record<string, unknown>>("/api/metrics/overview");
}

export function fetchGatewayFeed(limit = 50) {
  return requestJson<Record<string, unknown>>("/api/gateway/feed", undefined, { limit });
}

export function fetchContainmentWindows() {
  return requestJson<Record<string, number | null>>("/api/metrics/containment_windows");
}

export function fetchRun(runId: string) {
  return requestJson<Record<string, unknown>>(`/api/metrics/runs/${encodeURIComponent(runId)}`);
}

export function launchScenario(name: string) {
  return requestJson<Record<string, unknown>>(`/api/scenario/${name}`);
}

export function suppressSideEffect(runId: string, stepIndex: number, reason?: string) {
  return requestJson<Record<string, unknown>>(`/api/runs/${encodeURIComponent(runId)}/side-effects/${stepIndex}/suppress`, {
    method: "POST",
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

export function streamRun(
  runId: string,
  handlers: {
    onEvent: (event: StreamEvent) => void;
    onError?: (error: Event) => void;
  },
) {
  const source = new EventSource(buildUrl("/api/chat/stream", { run_id: runId }));

  const bind = (eventName: StreamEvent["event"]) => {
    source.addEventListener(eventName, (event) => {
      const messageEvent = event as MessageEvent<string>;
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(messageEvent.data) as Record<string, unknown>;
      } catch {
        handlers.onError?.(new Event("error"));
        return;
      }

      handlers.onEvent({
        event: eventName,
        data: payload,
      });
    });
  };

  bind("status");
  bind("message_delta");
  bind("step");
  bind("metric");
  bind("complete");

  source.onerror = (error) => {
    handlers.onError?.(error);
  };

  return () => source.close();
}
