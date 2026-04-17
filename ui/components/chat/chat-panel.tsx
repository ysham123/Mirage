"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Activity, ArrowRight, FileJson2, MessageSquare, Shield } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { ChatMessage, ConsoleRun } from "@/types/console";

import { MessageBubble } from "./message-bubble";

interface ChatPanelProps {
  run: ConsoleRun | null;
  messages: ChatMessage[];
  streamStatus: string;
  focusedSideEffectId: string | null;
}

export function ChatPanel({ run, messages, streamStatus, focusedSideEffectId }: ChatPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  if (!run) {
    return (
      <Card className="flex h-full min-h-[480px] items-center justify-center p-8">
        <div className="max-w-xl text-center">
          <div className="mx-auto mb-5 flex size-16 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[var(--accent)]">
            <MessageSquare className="size-6" />
          </div>
          <h2 className="text-3xl font-semibold tracking-[-0.04em] text-white">Massive chat, deterministic traces</h2>
          <p className="mt-4 text-base text-[var(--text-secondary)]">
            Select a run from the queue or launch a scenario to stream Mirage review reasoning, side effects, and CI-safe suppression controls in one place.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="flex h-full min-h-[620px] flex-col overflow-hidden">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-[0.68rem] uppercase tracking-[0.28em] text-[var(--text-muted)]">Conversational Interface</p>
            <h2 className="mt-2 truncate text-3xl font-semibold tracking-[-0.05em] text-white">{run.runId}</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">{run.headline}</p>
          </div>
          <Badge tone={run.finalOutcome === "allowed" ? "success" : run.finalOutcome === "config_error" ? "critical" : "warning"}>
            {run.finalOutcome.replaceAll("_", " ")}
          </Badge>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
            <Shield className="size-3.5 text-[var(--accent)]" />
            {run.agentHealth.label}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
            <Activity className="size-3.5 text-[var(--accent)]" />
            {streamStatus}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
            <FileJson2 className="size-3.5 text-[var(--accent)]" />
            Trace-backed replay
          </span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
            <ArrowRight className="size-3.5 text-[var(--accent)]" />
            {run.eventCount} intercepted actions
          </span>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        <AnimatePresence initial={false}>
          {messages.map((message) => (
            <motion.div key={message.id} layout>
              <MessageBubble active={message.sideEffectId === focusedSideEffectId} message={message} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Card>
  );
}
