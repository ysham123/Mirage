import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  fetchOverview: vi.fn(),
  fetchRun: vi.fn(),
  launchScenario: vi.fn(),
  streamRun: vi.fn(),
  suppressSideEffect: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  fetchOverview: apiMocks.fetchOverview,
  fetchRun: apiMocks.fetchRun,
  launchScenario: apiMocks.launchScenario,
  streamRun: apiMocks.streamRun,
  suppressSideEffect: apiMocks.suppressSideEffect,
}));

vi.mock("@/lib/shortcuts", () => ({
  useConsoleShortcuts: () => undefined,
}));

import { ConsoleApp, mergeMessageBodies } from "@/components/console-app";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function createOverviewPayload() {
  return {
    summary: {
      total_runs: 2,
      total_actions: 2,
      allowed: 1,
      policy_violation: 1,
      unmatched_route: 0,
      config_error: 0,
      risky_runs: 1,
      suppressed_actions: 0,
    },
    recent_runs: [
      {
        run_id: "run-risky",
        outcome: "policy_violation",
        headline: "Risky run headline",
        timestamp: "2026-04-20T12:30:00+00:00",
        request: { method: "POST", path: "/v1/risky" },
        event_count: 1,
        suppressed_count: 0,
      },
      {
        run_id: "run-safe",
        outcome: "allowed",
        headline: "Safe run headline",
        timestamp: "2026-04-20T12:20:00+00:00",
        request: { method: "GET", path: "/v1/safe" },
        event_count: 1,
        suppressed_count: 0,
      },
    ],
    top_endpoints: [],
    top_policy_failures: [],
  };
}

function createRunPayload(runId: string, headline: string) {
  return {
    run_id: runId,
    meta: {
      run_id: runId,
      trace_path: `artifacts/traces/${runId}.json`,
      source: "trace metrics review",
      event_count: 1,
    },
    summary: {
      headline,
      final_outcome: runId === "run-safe" ? "allowed" : "policy_violation",
      trace_event_count: 1,
      trace_path: `artifacts/traces/${runId}.json`,
    },
    risk: {
      score: runId === "run-safe" ? 10 : 70,
      level: runId === "run-safe" ? "stable" : "elevated",
      total_steps: 0,
      risky_steps: runId === "run-safe" ? 0 : 1,
      suppressed_steps: 0,
      allowed_steps: 0,
    },
    agent_health: {
      status: runId === "run-safe" ? "stable" : "watch",
      summary: `${headline} status`,
      confidence: 0.8,
      label: runId === "run-safe" ? "Nominal" : "Needs Review",
    },
    side_effects: [],
    trace: {
      run_id: runId,
      events: [],
    },
    trace_path: `artifacts/traces/${runId}.json`,
  };
}

describe("ConsoleApp races", () => {
  beforeAll(() => {
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      value: vi.fn(),
    });
  });

  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/?run_id=run-risky");
    apiMocks.fetchOverview.mockResolvedValue(createOverviewPayload());
    apiMocks.streamRun.mockImplementation(() => () => undefined);
  });

  it("ignores stale run snapshots when a newer selection resolves first", async () => {
    const riskyRun = deferred<Record<string, unknown>>();
    const safeRun = deferred<Record<string, unknown>>();

    apiMocks.fetchRun.mockImplementation((runId: string) => {
      if (runId === "run-risky") {
        return riskyRun.promise;
      }
      if (runId === "run-safe") {
        return safeRun.promise;
      }
      throw new Error(`Unexpected run ${runId}`);
    });

    render(<ConsoleApp />);

    await screen.findByRole("button", { name: /run-safe/i });
    fireEvent.click(screen.getByRole("button", { name: /run-safe/i }));

    await waitFor(() => expect(apiMocks.fetchRun).toHaveBeenCalledWith("run-safe"));

    await act(async () => {
      safeRun.resolve(createRunPayload("run-safe", "Safe run headline"));
      await safeRun.promise;
    });

    await screen.findByRole("heading", { name: "run-safe" });
    expect(screen.getByText("Safe run headline")).toBeInTheDocument();

    await act(async () => {
      riskyRun.resolve(createRunPayload("run-risky", "Risky run headline"));
      await riskyRun.promise;
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "run-safe" })).toBeInTheDocument();
      expect(screen.getByText("Safe run headline")).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: "run-risky" })).not.toBeInTheDocument();
  });

  it("keeps streamed deltas when the snapshot arrives after the stream starts", async () => {
    const riskyRun = deferred<Record<string, unknown>>();

    apiMocks.fetchRun.mockImplementation((runId: string) => {
      if (runId !== "run-risky") {
        throw new Error(`Unexpected run ${runId}`);
      }
      return riskyRun.promise;
    });

    apiMocks.streamRun.mockImplementation(
      (_runId: string, handlers: { onEvent: (event: { event: string; data: Record<string, unknown> }) => void }) => {
        handlers.onEvent({
          event: "message_delta",
          data: {
            message_id: "run-risky-intro",
            delta: " Extra streaming context.",
          },
        });
        return () => undefined;
      },
    );

    render(<ConsoleApp />);

    await waitFor(() => expect(apiMocks.fetchRun).toHaveBeenCalledWith("run-risky"));

    await act(async () => {
      riskyRun.resolve(createRunPayload("run-risky", "Risky run headline"));
      await riskyRun.promise;
    });

    expect(await screen.findByRole("heading", { name: "run-risky" })).toBeInTheDocument();
    expect(screen.getByText(/Extra streaming context\./)).toBeInTheDocument();
  });

  it("does not restore a launched run after the user switches selection mid-refresh", async () => {
    const launchedOverview = deferred<Record<string, unknown>>();

    apiMocks.fetchOverview
      .mockResolvedValueOnce(createOverviewPayload())
      .mockImplementationOnce(() => launchedOverview.promise);
    apiMocks.fetchRun.mockImplementation((runId: string) => Promise.resolve(createRunPayload(runId, `${runId} headline`)));
    apiMocks.launchScenario.mockResolvedValue(createRunPayload("run-launch", "Launch headline"));

    render(<ConsoleApp />);

    await screen.findByRole("button", { name: /compliant/i });

    fireEvent.click(screen.getByRole("button", { name: /compliant/i }));
    await screen.findByRole("heading", { name: "run-launch" });

    fireEvent.click(screen.getByRole("button", { name: /run-safe/i }));
    await waitFor(() => expect(apiMocks.fetchRun).toHaveBeenCalledWith("run-safe"));

    await act(async () => {
      launchedOverview.resolve(createOverviewPayload());
      await launchedOverview.promise;
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "run-safe" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("heading", { name: "run-launch" })).not.toBeInTheDocument();
  });

  it("merges overlapping snapshot and stream text without duplication", () => {
    expect(
      mergeMessageBodies(
        "Risky action gets flagged ",
        "Risky action gets flagged while the workflow keeps moving.",
      ),
    ).toBe("Risky action gets flagged while the workflow keeps moving.");
  });
});
