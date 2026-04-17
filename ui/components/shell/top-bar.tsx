"use client";

import { Activity, Command, Download, Layers3, Menu, Sparkles, Workflow } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AgentHealth, ConsoleRun } from "@/types/console";

interface TopBarProps {
  health: AgentHealth | null;
  selectedRun: ConsoleRun | null;
  onOpenPalette: () => void;
  onLaunchScenario: (name: "safe" | "risky" | "unmatched") => void;
  onExport: () => void;
  onToggleSidebar: () => void;
  onOpenMobileSidebar: () => void;
  onOpenMobileEffects: () => void;
}

function healthTone(status: AgentHealth["status"] | undefined) {
  if (status === "stable") {
    return "success";
  }
  if (status === "critical") {
    return "critical";
  }
  return "warning";
}

export function TopBar({
  health,
  selectedRun,
  onOpenPalette,
  onLaunchScenario,
  onExport,
  onToggleSidebar,
  onOpenMobileSidebar,
  onOpenMobileEffects,
}: TopBarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[rgba(3,7,12,.72)] px-4 py-3 backdrop-blur-2xl lg:px-6">
      <div className="mx-auto flex max-w-[1800px] items-center gap-3">
        <button
          aria-label="Open navigation"
          className="inline-flex size-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[var(--text-secondary)] transition hover:bg-white/[0.08] hover:text-white xl:hidden"
          onClick={onOpenMobileSidebar}
          type="button"
        >
          <Menu className="size-4" />
        </button>

        <button
          aria-label="Toggle sidebar"
          className="hidden size-11 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[var(--text-secondary)] transition hover:bg-white/[0.08] hover:text-white xl:inline-flex"
          onClick={onToggleSidebar}
          type="button"
        >
          <Layers3 className="size-4" />
        </button>

        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-2xl border border-[rgba(111,231,255,.18)] bg-[radial-gradient(circle_at_35%_30%,rgba(111,231,255,.35),rgba(8,13,20,.9))] shadow-[0_0_40px_rgba(22,205,255,.25)]">
            <Workflow className="size-5 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-[0.7rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">CI for Agent Side Effects</p>
            <div className="flex items-center gap-2">
              <h1 className="truncate text-lg font-semibold tracking-[-0.03em] text-white">Mirage Console</h1>
              {health ? <Badge tone={healthTone(health.status)}>{health.label}</Badge> : null}
            </div>
          </div>
        </div>

        <div className="ml-auto hidden min-w-0 flex-1 items-center justify-center xl:flex">
          <button
            className="flex min-w-[360px] items-center gap-3 rounded-full border border-white/10 bg-white/[0.04] px-4 py-3 text-left transition hover:border-[var(--border-strong)] hover:bg-white/[0.06]"
            onClick={onOpenPalette}
            type="button"
          >
            <Command className="size-4 text-[var(--accent)]" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-white">{selectedRun ? selectedRun.runId : "Jump to a run, launch a scenario, or trigger export"}</p>
              <p className="truncate text-xs text-[var(--text-muted)]">Cmd/Ctrl+K opens the command palette</p>
            </div>
            <span className="rounded-full border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-[var(--text-muted)]">⌘K</span>
          </button>
        </div>

        <div className="hidden items-center gap-2 xl:flex">
          <Button size="sm" variant="ghost" onClick={() => onLaunchScenario("safe")}>
            <Sparkles className="size-3.5" />
            Compliant
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onLaunchScenario("risky")}>
            <Activity className="size-3.5" />
            Excessive
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onLaunchScenario("unmatched")}>
            <Layers3 className="size-3.5" />
            New Route
          </Button>
          <Button size="sm" variant="outline" onClick={onExport}>
            <Download className="size-3.5" />
            Export
          </Button>
        </div>

        <div className="flex items-center gap-2 xl:hidden">
          <Button aria-label="Open command palette" size="icon" variant="outline" onClick={onOpenPalette}>
            <Command className="size-4" />
          </Button>
          <Button aria-label="Open side effects panel" size="icon" variant="outline" onClick={onOpenMobileEffects}>
            <Activity className="size-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
