"use client";

import { AnimatePresence, motion } from "framer-motion";
import { startTransition, useDeferredValue, useEffect, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { Composer } from "@/components/chat/composer";
import { CommandPalette } from "@/components/shell/command-palette";
import { Sidebar } from "@/components/shell/sidebar";
import { TopBar } from "@/components/shell/top-bar";
import { SideEffectsPanel } from "@/components/side-effects/side-effects-panel";
import { fetchOverview, fetchRun, launchScenario, streamRun, suppressSideEffect } from "@/lib/api";
import { adaptOverview, adaptRun, respondToPrompt } from "@/lib/adapters";
import { springs } from "@/lib/motion";
import { useConsoleShortcuts } from "@/lib/shortcuts";
import type {
  ChatMessage,
  ConsoleOverview,
  ConsoleRun,
  ConsoleView,
  QueueFilter,
  SideEffect,
  StreamEvent,
} from "@/types/console";

type ScenarioName = "safe" | "risky" | "unmatched";

function parseUrlState() {
  const params = new URLSearchParams(window.location.search);
  const filter = params.get("filter");
  const view = params.get("view");
  const focused = params.get("step");
  return {
    runId: params.get("run_id"),
    filter: filter === "risky" || filter === "allowed" || filter === "unmatched_route" ? filter : "all",
    view: view === "timeline" || view === "trace" ? view : "overview",
    focusedStepIndex: focused ? Number(focused) : null,
  } satisfies {
    runId: string | null;
    filter: QueueFilter;
    view: ConsoleView;
    focusedStepIndex: number | null;
  };
}

type StreamMessageStore = Map<string, ChatMessage>;

export function mergeMessageBodies(snapshotBody: string, streamedBody: string) {
  if (!snapshotBody) {
    return streamedBody;
  }
  if (!streamedBody) {
    return snapshotBody;
  }
  if (snapshotBody === streamedBody) {
    return snapshotBody;
  }
  if (streamedBody.includes(snapshotBody)) {
    return streamedBody;
  }
  if (snapshotBody.includes(streamedBody)) {
    return snapshotBody;
  }

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

export function mergeConversationMessages(snapshotMessages: ChatMessage[], streamedMessages: StreamMessageStore) {
  if (!streamedMessages.size) {
    return snapshotMessages;
  }

  const mergedStreamIds = new Set<string>();
  const mergedSnapshot = snapshotMessages.map((message) => {
    const streamedMessage = streamedMessages.get(message.id);
    if (!streamedMessage) {
      return message;
    }
    mergedStreamIds.add(message.id);
    return {
      ...message,
      role: streamedMessage.role ?? message.role,
      title: streamedMessage.title ?? message.title,
      tone: streamedMessage.tone ?? message.tone,
      body: mergeMessageBodies(message.body, streamedMessage.body),
      streaming: streamedMessage.streaming ?? message.streaming,
    };
  });

  const appendedStreamMessages = [...streamedMessages.values()]
    .filter((message) => !mergedStreamIds.has(message.id))
    .map((message) => ({ ...message }));

  return [...mergedSnapshot, ...appendedStreamMessages];
}

export function accumulateStreamMessage(
  streamedMessages: StreamMessageStore,
  runId: string,
  data: StreamEvent["data"],
) {
  const nextMessages = new Map(streamedMessages);
  const messageId = String(data.message_id ?? `stream-${runId}`);
  const delta = String(data.delta ?? "");
  const current = nextMessages.get(messageId);

  nextMessages.set(messageId, {
    id: messageId,
    role: current?.role ?? "assistant",
    title: current?.title,
    tone: current?.tone ?? "neutral",
    body: `${current?.body ?? ""}${delta}`,
    streaming: true,
  });

  return nextMessages;
}

export function completeStreamMessages(streamedMessages: StreamMessageStore) {
  return new Map(
    [...streamedMessages.entries()].map(([messageId, message]) => [
      messageId,
      {
        ...message,
        streaming: false,
      },
    ]),
  );
}

export function ConsoleApp() {
  const searchRef = useRef<HTMLInputElement | null>(null);
  const riskyCursor = useRef(0);
  const selectedRunIdRef = useRef<string | null>(null);
  const runRequestRef = useRef(0);
  const streamSessionRef = useRef(0);
  const streamedMessagesRef = useRef<StreamMessageStore>(new Map());

  const [overview, setOverview] = useState<ConsoleOverview | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<ConsoleRun | null>(null);
  const [conversation, setConversation] = useState<ChatMessage[]>([]);
  const [queueFilter, setQueueFilter] = useState<QueueFilter>("all");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<ConsoleView>("overview");
  const [focusedStepIndex, setFocusedStepIndex] = useState<number | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [mobileEffectsOpen, setMobileEffectsOpen] = useState(false);
  const [composerValue, setComposerValue] = useState("");
  const [streamStatus, setStreamStatus] = useState("Awaiting run selection");
  const [loadError, setLoadError] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search);

  const filteredRuns =
    overview?.runs.filter((run) => {
      const matchesFilter =
        queueFilter === "all"
          ? true
          : queueFilter === "risky"
            ? run.outcome !== "allowed"
            : run.outcome === queueFilter;
      if (!matchesFilter) {
        return false;
      }
      if (!deferredSearch.trim()) {
        return true;
      }
      const haystack = `${run.runId} ${run.headline} ${run.method ?? ""} ${run.path ?? ""} ${run.outcome}`.toLowerCase();
      return haystack.includes(deferredSearch.toLowerCase());
    }) ?? [];

  const sidebarOverview = overview ? { ...overview, runs: filteredRuns } : null;
  const focusedSideEffectId =
    selectedRun?.sideEffects.find((effect) => effect.stepIndex === focusedStepIndex)?.id ?? null;

  selectedRunIdRef.current = selectedRunId;

  async function refreshOverview(preferredRunId?: string | null) {
    try {
      const payload = await fetchOverview();
      const nextOverview = adaptOverview(payload);
      setOverview(nextOverview);
      if (!selectedRunId && !preferredRunId && nextOverview.runs[0]) {
        setSelectedRunId(nextOverview.runs[0].runId);
      } else if (preferredRunId) {
        setSelectedRunId(preferredRunId);
      }
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to load Mirage overview.");
    }
  }

  async function refreshRun(runId: string, requestId = ++runRequestRef.current) {
    try {
      const payload = await fetchRun(runId);
      const nextRun = adaptRun(payload);
      if (requestId !== runRequestRef.current || selectedRunIdRef.current !== runId) {
        return;
      }
      setSelectedRun(nextRun);
      setConversation(mergeConversationMessages(nextRun.messages, streamedMessagesRef.current));
      setLoadError(null);
    } catch (error) {
      if (requestId !== runRequestRef.current || selectedRunIdRef.current !== runId) {
        return;
      }
      setLoadError(error instanceof Error ? error.message : `Failed to load run ${runId}.`);
    }
  }

  function syncUrlState(next: {
    runId?: string | null;
    filter?: QueueFilter;
    view?: ConsoleView;
    focusedStepIndex?: number | null;
  }) {
    const params = new URLSearchParams(window.location.search);
    const runId = next.runId ?? selectedRunId;
    const filter = next.filter ?? queueFilter;
    const activeView = next.view ?? view;
    const focusStep = next.focusedStepIndex ?? focusedStepIndex;

    if (runId) params.set("run_id", runId);
    else params.delete("run_id");

    if (filter !== "all") params.set("filter", filter);
    else params.delete("filter");

    if (activeView !== "overview") params.set("view", activeView);
    else params.delete("view");

    if (focusStep) params.set("step", String(focusStep));
    else params.delete("step");

    const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }

  useEffect(() => {
    const state = parseUrlState();
    setSelectedRunId(state.runId);
    setQueueFilter(state.filter);
    setView(state.view);
    setFocusedStepIndex(state.focusedStepIndex);
    void refreshOverview(state.runId);

    const onPopState = () => {
      const next = parseUrlState();
      setSelectedRunId(next.runId);
      setQueueFilter(next.filter);
      setView(next.view);
      setFocusedStepIndex(next.focusedStepIndex);
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      streamedMessagesRef.current = new Map();
      runRequestRef.current += 1;
      streamSessionRef.current += 1;
      setSelectedRun(null);
      setConversation([]);
      return;
    }

    streamedMessagesRef.current = new Map();
    setSelectedRun((current) => (current?.runId === selectedRunId ? current : null));
    setConversation([]);
    void refreshRun(selectedRunId);
    syncUrlState({ runId: selectedRunId });
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }

    const streamSessionId = ++streamSessionRef.current;
    setStreamStatus("Connecting to live review stream");
    const stop = streamRun(selectedRunId, {
      onEvent(event: StreamEvent) {
        if (streamSessionId !== streamSessionRef.current || selectedRunIdRef.current !== selectedRunId) {
          return;
        }
        if (event.event === "status") {
          setStreamStatus(String(event.data.message ?? "Streaming"));
          return;
        }

        if (event.event === "message_delta") {
          streamedMessagesRef.current = accumulateStreamMessage(streamedMessagesRef.current, selectedRunId, event.data);
          setConversation((current) => mergeConversationMessages(current, streamedMessagesRef.current));
          return;
        }

        if (event.event === "step") {
          const stepIndex = Number(event.data.step_index ?? 0);
          if (stepIndex) {
            setFocusedStepIndex((current) => current ?? stepIndex);
          }
          return;
        }

        if (event.event === "metric") {
          const stepIndex = Number(event.data.focus_step_index ?? 0);
          if (stepIndex) {
            setFocusedStepIndex((current) => current ?? stepIndex);
          }
          return;
        }

        if (event.event === "complete") {
          setStreamStatus("Review stream synced");
          streamedMessagesRef.current = completeStreamMessages(streamedMessagesRef.current);
          setConversation((current) => current.map((message) => ({ ...message, streaming: false })));
        }
      },
      onError() {
        if (streamSessionId !== streamSessionRef.current || selectedRunIdRef.current !== selectedRunId) {
          return;
        }
        setStreamStatus("Stream unavailable, using trace snapshot");
      },
    });

    return () => {
      stop();
      if (streamSessionRef.current === streamSessionId) {
        streamSessionRef.current += 1;
      }
    };
  }, [selectedRunId]);

  useEffect(() => {
    syncUrlState({});
  }, [queueFilter, view, focusedStepIndex]);

  async function handleScenarioLaunch(name: ScenarioName) {
    startTransition(() => {
      setStreamStatus(`Launching ${name} scenario`);
    });

    try {
      const payload = await launchScenario(name);
      const run = adaptRun(payload);
      setSelectedRunId(run.runId);
      setSelectedRun(run);
      setConversation(run.messages);
      await refreshOverview(run.runId);
      setFocusedStepIndex(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : `Failed to launch ${name} scenario.`);
    }
  }

  async function handleSuppress(effect: SideEffect | null) {
    if (!selectedRunId || !effect) {
      return;
    }
    try {
      await suppressSideEffect(selectedRunId, effect.stepIndex, effect.decisionSummary ?? effect.message ?? undefined);
      await Promise.all([refreshRun(selectedRunId), refreshOverview(selectedRunId)]);
      setView("timeline");
      setFocusedStepIndex(effect.stepIndex);
      setStreamStatus(`Suppressed ${effect.name}`);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to suppress side effect.");
    }
  }

  function handleComposeSubmit() {
    if (!selectedRun || !composerValue.trim()) {
      return;
    }
    const prompt = composerValue.trim();
    const userMessage: ChatMessage = {
      id: `${selectedRun.runId}-prompt-${Date.now()}`,
      role: "user",
      body: prompt,
    };
    const assistantMessage: ChatMessage = {
      id: `${selectedRun.runId}-answer-${Date.now()}`,
      role: "assistant",
      title: "Mirage answer",
      body: respondToPrompt(prompt, selectedRun),
      tone: "neutral",
    };
    setConversation((current) => [...current, userMessage, assistantMessage]);
    setComposerValue("");
  }

  async function copyText(value: string, label: string) {
    if (!value) {
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      setStreamStatus(`${label} copied`);
    } catch {
      setStreamStatus(`Clipboard unavailable for ${label.toLowerCase()}`);
    }
  }

  function handleExport() {
    if (!selectedRun) {
      return;
    }
    const blob = new Blob([JSON.stringify(selectedRun.trace, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selectedRun.runId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setStreamStatus(`Exported ${selectedRun.runId}`);
  }

  function jumpToNextRisky() {
    if (!selectedRun) {
      return;
    }
    const risky = selectedRun.sideEffects.filter((effect) => effect.outcome !== "allowed");
    if (!risky.length) {
      setStreamStatus("No risky side effects in this run");
      return;
    }
    const next = risky[riskyCursor.current % risky.length];
    riskyCursor.current += 1;
    setFocusedStepIndex(next.stepIndex);
    setView("timeline");
    setStreamStatus(`Focused ${next.name}`);
  }

  function suppressNextRisky() {
    const target = selectedRun?.sideEffects.find((effect) => effect.outcome !== "allowed" && !effect.suppressed) ?? null;
    void handleSuppress(target);
  }

  function selectRelative(offset: number) {
    if (!filteredRuns.length) {
      return;
    }
    const currentIndex = filteredRuns.findIndex((run) => run.runId === selectedRunId);
    const nextIndex = currentIndex < 0 ? 0 : Math.max(0, Math.min(filteredRuns.length - 1, currentIndex + offset));
    const nextRunId = filteredRuns[nextIndex]?.runId;
    if (nextRunId) {
      setSelectedRunId(nextRunId);
    }
  }

  useConsoleShortcuts({
    onCommandPalette: () => setCommandPaletteOpen(true),
    onFocusSearch: () => searchRef.current?.focus(),
    onToggleSidebar: () => setSidebarCollapsed((current) => !current),
    onExport: handleExport,
    onSuppress: suppressNextRisky,
    onNext: () => selectRelative(1),
    onPrevious: () => selectRelative(-1),
    onView: (index) => setView(index === 1 ? "overview" : index === 2 ? "timeline" : "trace"),
    onEscape: () => {
      setCommandPaletteOpen(false);
      setMobileSidebarOpen(false);
      setMobileEffectsOpen(false);
    },
  });

  const actions = [
    {
      id: "launch-safe",
      label: "Launch compliant bid",
      description: "Seed the console with an allowed procurement workflow.",
      group: "Scenarios",
      onSelect: () => void handleScenarioLaunch("safe"),
    },
    {
      id: "launch-risky",
      label: "Launch excessive bid",
      description: "Trigger a policy violation and watch the console react.",
      group: "Scenarios",
      onSelect: () => void handleScenarioLaunch("risky"),
    },
    {
      id: "launch-unmatched",
      label: "Launch new supplier",
      description: "Create an unmatched route to inspect missing mock coverage.",
      group: "Scenarios",
      onSelect: () => void handleScenarioLaunch("unmatched"),
    },
    {
      id: "open-trace",
      label: "Open raw trace",
      description: "Switch the right rail into trace view.",
      group: "Navigation",
      onSelect: () => setView("trace"),
    },
    {
      id: "filter-risky",
      label: "Filter risky runs",
      description: "Collapse the queue to runs that require human review.",
      group: "Queue",
      shortcut: "/",
      onSelect: () => setQueueFilter("risky"),
    },
    {
      id: "export-run",
      label: "Export selected run",
      description: "Download the current trace JSON from the client.",
      group: "Actions",
      shortcut: "E",
      onSelect: handleExport,
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--bg)] text-white">
      <TopBar
        health={selectedRun?.agentHealth ?? null}
        selectedRun={selectedRun}
        onExport={handleExport}
        onLaunchScenario={handleScenarioLaunch}
        onOpenMobileEffects={() => setMobileEffectsOpen(true)}
        onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        onOpenPalette={() => setCommandPaletteOpen(true)}
        onToggleSidebar={() => setSidebarCollapsed((current) => !current)}
      />

      <main className="mx-auto grid max-w-[1800px] gap-4 px-4 py-4 xl:grid-cols-[320px_minmax(0,1fr)_420px] xl:px-6">
        <Sidebar
          className="hidden xl:flex"
          collapsed={sidebarCollapsed}
          filter={queueFilter}
          overview={sidebarOverview}
          search={search}
          searchRef={searchRef}
          selectedRunId={selectedRunId}
          onFilterChange={(next) => {
            setQueueFilter(next);
            syncUrlState({ filter: next });
          }}
          onSearchChange={setSearch}
          onSelectRun={(runId) => {
            setSelectedRunId(runId);
            setFocusedStepIndex(null);
            setMobileSidebarOpen(false);
          }}
        />

        <section className="min-w-0">
          {loadError ? (
            <div className="mb-4 rounded-[1.4rem] border border-[rgba(255,90,124,.16)] bg-[rgba(255,90,124,.08)] px-4 py-3 text-sm text-[rgb(255,194,208)]">
              {loadError}
            </div>
          ) : null}
          <ChatPanel
            focusedSideEffectId={focusedSideEffectId}
            messages={conversation}
            run={selectedRun}
            streamStatus={streamStatus}
          />
          <Composer
            disabled={!selectedRun}
            value={composerValue}
            onChange={setComposerValue}
            onCopyRunId={() => void copyText(selectedRun?.runId ?? "", "Run id")}
            onCopyTracePath={() => void copyText(selectedRun?.tracePath ?? "", "Trace path")}
            onExport={handleExport}
            onJumpRisk={jumpToNextRisky}
            onOpenTrace={() => setView("trace")}
            onSubmit={handleComposeSubmit}
          />
        </section>

        <SideEffectsPanel
          className="hidden h-[calc(100vh-7rem)] xl:block"
          focusedStepIndex={focusedStepIndex}
          overview={overview}
          run={selectedRun}
          view={view}
          onFocusStep={(stepIndex) => {
            setFocusedStepIndex(stepIndex);
            syncUrlState({ focusedStepIndex: stepIndex, view: "timeline" });
          }}
          onSuppress={(effect) => void handleSuppress(effect)}
          onViewChange={(nextView) => {
            setView(nextView);
            syncUrlState({ view: nextView });
          }}
        />
      </main>

      <AnimatePresence>
        {mobileSidebarOpen ? (
          <motion.div
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-40 bg-[rgba(2,6,10,.72)] xl:hidden"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={() => setMobileSidebarOpen(false)}
          >
            <motion.div
              animate={{ x: 0 }}
              className="h-full w-[88vw] max-w-sm"
              exit={{ x: "-100%" }}
              initial={{ x: "-100%" }}
              transition={springs.snappy}
              onClick={(event) => event.stopPropagation()}
            >
              <Sidebar
                filter={queueFilter}
                overview={sidebarOverview}
                search={search}
                searchRef={searchRef}
                selectedRunId={selectedRunId}
                onFilterChange={(next) => {
                  setQueueFilter(next);
                  syncUrlState({ filter: next });
                }}
                onSearchChange={setSearch}
                onSelectRun={(runId) => {
                  setSelectedRunId(runId);
                  setMobileSidebarOpen(false);
                  setFocusedStepIndex(null);
                }}
              />
            </motion.div>
          </motion.div>
        ) : null}

        {mobileEffectsOpen ? (
          <motion.div
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-40 bg-[rgba(2,6,10,.72)] px-3 pb-3 pt-24 xl:hidden"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={() => setMobileEffectsOpen(false)}
          >
            <motion.div
              animate={{ y: 0 }}
              className="h-full"
              exit={{ y: "100%" }}
              initial={{ y: "100%" }}
              transition={springs.snappy}
              onClick={(event) => event.stopPropagation()}
            >
              <SideEffectsPanel
                className="h-full"
                focusedStepIndex={focusedStepIndex}
                overview={overview}
                run={selectedRun}
                view={view}
                onFocusStep={(stepIndex) => {
                  setFocusedStepIndex(stepIndex);
                  setView("timeline");
                  syncUrlState({ focusedStepIndex: stepIndex, view: "timeline" });
                }}
                onSuppress={(effect) => void handleSuppress(effect)}
                onViewChange={(nextView) => {
                  setView(nextView);
                  syncUrlState({ view: nextView });
                }}
              />
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <CommandPalette actions={actions} open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </div>
  );
}
