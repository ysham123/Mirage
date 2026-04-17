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

async function requestJson<T>(path: string, init?: RequestInit, params?: Record<string, string | number | undefined>) {
  const response = await fetch(buildUrl(path, params), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchOverview() {
  return requestJson<Record<string, unknown>>("/api/metrics/overview");
}

export function fetchRun(runId: string) {
  return requestJson<Record<string, unknown>>(`/api/metrics/runs/${runId}`);
}

export function launchScenario(name: string) {
  return requestJson<Record<string, unknown>>(`/api/scenario/${name}`);
}

export function suppressSideEffect(runId: string, stepIndex: number, reason?: string) {
  return requestJson<Record<string, unknown>>(`/api/runs/${runId}/side-effects/${stepIndex}/suppress`, {
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
      handlers.onEvent({
        event: eventName,
        data: JSON.parse(messageEvent.data),
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
    source.close();
  };

  return () => source.close();
}
