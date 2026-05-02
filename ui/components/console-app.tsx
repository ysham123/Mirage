"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { adaptOverview, adaptRun } from "@/lib/adapters";
import { fetchOverview, fetchRun, launchScenario as apiLaunchScenario, suppressSideEffect } from "@/lib/api";
import type { ConsoleOverview, ConsoleRun, QueueFilter, RunListItem } from "@/types/console";

import { GatewayFeed } from "@/components/gateway-feed";
import { RunDetail } from "@/components/run-detail";
import { Sidebar } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";

type ConsoleTab = "runs" | "gateway";

export function ConsoleApp() {
  const [overview, setOverview] = useState<ConsoleOverview | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [run, setRun] = useState<ConsoleRun | null>(null);
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [search, setSearch] = useState("");
  const [followLatest, setFollowLatest] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);
  const [launchingScenario, setLaunchingScenario] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ConsoleTab>("runs");

  // Stale-response guard: ignore responses for superseded requests.
  const activeRunId = useRef<string | null>(null);
  // Avoid stale closure in followLatest effect without adding to dep array.
  const selectedRunIdRef = useRef<string | null>(null);
  selectedRunIdRef.current = selectedRunId;

  const loadOverview = useCallback(async () => {
    try {
      const payload = await fetchOverview();
      const data = adaptOverview(payload);
      setOverview(data);
      setLastUpdated(new Date());
    } catch {
      // backend may not be ready
    }
  }, []);

  const loadRun = useCallback(async (runId: string) => {
    activeRunId.current = runId;
    setLoading(true);
    try {
      const payload = await fetchRun(runId);
      if (activeRunId.current !== runId) return;
      setRun(adaptRun(payload));
    } catch {
      // ignore fetch errors
    } finally {
      if (activeRunId.current === runId) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
    const id = setInterval(loadOverview, 10_000);
    return () => clearInterval(id);
  }, [loadOverview]);

  // Auto-select first run on initial load.
  useEffect(() => {
    if (!selectedRunIdRef.current && overview?.runs.length) {
      setSelectedRunId(overview.runs[0].runId);
    }
  }, [overview]);

  // Follow latest: advance selection when new runs arrive.
  useEffect(() => {
    if (followLatest && overview?.runs.length) {
      const latest = overview.runs[0].runId;
      if (latest !== selectedRunIdRef.current) setSelectedRunId(latest);
    }
  }, [followLatest, overview]);

  useEffect(() => {
    if (selectedRunId) loadRun(selectedRunId);
  }, [selectedRunId, loadRun]);

  const filteredRuns: RunListItem[] = (overview?.runs ?? []).filter((r) => {
    if (filter === "risky" && r.outcome !== "policy_violation") return false;
    if (filter === "allowed" && r.outcome !== "allowed") return false;
    if (filter === "unmatched_route" && r.outcome !== "unmatched_route") return false;
    if (search && !r.runId.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleSelectRun = (runId: string) => {
    setFollowLatest(false);
    setSelectedRunId(runId);
  };

  const handleLaunch = async (name: "safe" | "risky" | "unmatched") => {
    setLaunchingScenario(name);
    try {
      await apiLaunchScenario(name);
      await loadOverview();
      // Auto-select the newest run after launching.
      setFollowLatest(true);
    } catch {
      // ignore
    } finally {
      setLaunchingScenario(null);
    }
  };

  const handleRefresh = () => {
    loadOverview();
    if (selectedRunId) loadRun(selectedRunId);
  };

  const handleSuppress = async (stepIndex: number) => {
    if (!selectedRunId) return;
    try {
      await suppressSideEffect(selectedRunId, stepIndex);
      await loadRun(selectedRunId);
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--bg)]">
      <TopBar
        followLatest={followLatest}
        lastUpdated={lastUpdated}
        overview={overview}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onRefresh={handleRefresh}
        onToggleFollowLatest={() => setFollowLatest((v) => !v)}
      />
      <div className="flex min-h-0 flex-1">
        {activeTab === "runs" ? (
          <>
            <Sidebar
              filter={filter}
              launchingScenario={launchingScenario}
              overview={overview}
              runs={filteredRuns}
              search={search}
              selectedRunId={selectedRunId}
              onFilterChange={setFilter}
              onLaunchScenario={handleLaunch}
              onSearchChange={setSearch}
              onSelectRun={handleSelectRun}
            />
            {/* key resets internal view state when run changes */}
            <RunDetail
              key={selectedRunId ?? "empty"}
              loading={loading}
              overview={overview}
              run={run}
              onSuppress={handleSuppress}
            />
          </>
        ) : (
          <GatewayFeed />
        )}
      </div>
    </div>
  );
}
