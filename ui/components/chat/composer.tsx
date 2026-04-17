"use client";

import { ArrowUpRight, Copy, Download, Eye, MoveDownRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ComposerProps {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCopyRunId: () => void;
  onCopyTracePath: () => void;
  onOpenTrace: () => void;
  onJumpRisk: () => void;
  onExport: () => void;
}

export function Composer({
  value,
  disabled,
  onChange,
  onSubmit,
  onCopyRunId,
  onCopyTracePath,
  onOpenTrace,
  onJumpRisk,
  onExport,
}: ComposerProps) {
  return (
    <div className="mt-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="ghost" onClick={onCopyRunId}>
          <Copy className="size-3.5" />
          Copy run id
        </Button>
        <Button size="sm" variant="ghost" onClick={onCopyTracePath}>
          <Copy className="size-3.5" />
          Copy trace path
        </Button>
        <Button size="sm" variant="ghost" onClick={onOpenTrace}>
          <Eye className="size-3.5" />
          Open trace
        </Button>
        <Button size="sm" variant="ghost" onClick={onJumpRisk}>
          <MoveDownRight className="size-3.5" />
          Next risky
        </Button>
        <Button size="sm" variant="outline" onClick={onExport}>
          <Download className="size-3.5" />
          Export
        </Button>
      </div>

      <div className="glass-panel rounded-[1.8rem] border border-white/10 p-3">
        <Textarea
          aria-label="Ask Mirage about this run"
          className="min-h-28 border-transparent bg-transparent shadow-none focus:border-transparent focus:bg-transparent focus:ring-0"
          disabled={disabled}
          placeholder="Ask Mirage to summarize risk, trace drift, or the next suppression candidate..."
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-[var(--text-muted)]">Enter submits. Shift+Enter adds a new line.</p>
          <Button disabled={disabled || !value.trim()} onClick={onSubmit}>
            <ArrowUpRight className="size-3.5" />
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
