"use client";

import { motion } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/console";

import { MarkdownRenderer } from "./markdown-renderer";

interface MessageBubbleProps {
  message: ChatMessage;
  active?: boolean;
}

function toneClass(tone: ChatMessage["tone"]) {
  if (tone === "success") {
    return "border-[rgba(83,255,197,.18)] bg-[rgba(83,255,197,.08)]";
  }
  if (tone === "warning") {
    return "border-[rgba(255,173,61,.18)] bg-[rgba(255,173,61,.08)]";
  }
  if (tone === "critical") {
    return "border-[rgba(255,90,124,.2)] bg-[rgba(255,90,124,.09)]";
  }
  return "border-white/10 bg-white/[0.04]";
}

export function MessageBubble({ message, active }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.article
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "max-w-[92%] rounded-[1.7rem] border p-5 shadow-[0_20px_60px_rgba(0,0,0,.18)]",
        isUser ? "ml-auto bg-[rgba(255,255,255,.06)]" : toneClass(message.tone),
        active ? "ring-2 ring-[rgba(111,231,255,.22)]" : "",
      )}
      initial={{ opacity: 0, y: 10 }}
    >
      <div className="mb-4 flex items-center gap-3">
        <Badge tone={isUser ? "neutral" : message.tone === "critical" ? "critical" : message.tone === "warning" ? "warning" : message.tone === "success" ? "success" : "neutral"}>
          {message.role}
        </Badge>
        {message.title ? <p className="text-sm font-semibold tracking-[-0.02em] text-white">{message.title}</p> : null}
        {message.streaming ? <span className="stream-cursor ml-auto" aria-hidden="true" /> : null}
      </div>
      <MarkdownRenderer>{message.body}</MarkdownRenderer>
    </motion.article>
  );
}
