import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchOverview, fetchRun, suppressSideEffect } from "@/lib/api";

describe("api helpers", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("encodes run ids in path-based requests", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("{}"),
    });

    await fetchRun("run/with?reserved#chars");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/metrics/runs/run%2Fwith%3Freserved%23chars",
      expect.any(Object),
    );
  });

  it("surfaces backend error payloads for failed requests", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
      text: vi.fn().mockResolvedValue(JSON.stringify({ error: "Unknown run: missing" })),
    });

    await expect(fetchRun("missing")).rejects.toThrow("Unknown run: missing");
  });

  it("avoids JSON content-type preflights for GET requests", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("{}"),
    });

    await fetchOverview();

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBeNull();
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("keeps JSON content-type for POST requests with bodies", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("{}"),
    });

    await suppressSideEffect("run-safe", 2, "review");

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
  });
});
