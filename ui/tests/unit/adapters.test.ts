import { adaptOverview, adaptRun, mergeMessageBodies, respondToPrompt } from "@/lib/adapters";

import { overviewFixture, runFixture } from "../fixtures/console";

describe("adapter layer", () => {
  it("normalizes overview payloads for the sidebar", () => {
    const overview = adaptOverview(overviewFixture);

    expect(overview.summary.totalRuns).toBe(2);
    expect(overview.runs[0]?.runId).toBe("run-risky");
    expect(overview.topPolicyFailures[0]?.name).toBe("enforce_bid_limit");
  });

  it("builds conversational messages from a trace-backed run", () => {
    const run = adaptRun(runFixture);

    expect(run.runId).toBe("run-risky");
    expect(run.messages[0]?.body).toContain("Mirage is tracking");
    expect(run.messages.some((message) => message.body.includes("Submit Bid"))).toBe(true);
    expect(run.sideEffects[1]?.suppressed).toBe(true);
  });

  it("responds to local operator prompts using run context", () => {
    const run = adaptRun(runFixture);
    expect(respondToPrompt("summarize risk", run)).toContain("Mirage marked");
    expect(respondToPrompt("where is the trace", run)).toContain("artifacts/traces/run-risky.json");
  });

  it("merges overlapping snapshot and stream bodies without duplication", () => {
    expect(
      mergeMessageBodies(
        "Risky action gets flagged ",
        "Risky action gets flagged while the workflow keeps moving.",
      ),
    ).toBe("Risky action gets flagged while the workflow keeps moving.");
  });
});
