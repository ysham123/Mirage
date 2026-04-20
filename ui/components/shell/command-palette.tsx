"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Command, CornerDownLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { handleDialogKeyDown, useDialogFocus } from "@/lib/dialog";
import { springs } from "@/lib/motion";

interface CommandAction {
  id: string;
  label: string;
  description: string;
  group: string;
  shortcut?: string;
  onSelect: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  actions: CommandAction[];
  onClose: () => void;
}

export function CommandPalette({ open, actions, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const titleId = "command-palette-title";

  useDialogFocus(open, dialogRef, inputRef);

  useEffect(() => {
    if (open) {
      setQuery("");
    }
  }, [open]);

  const filtered = actions.filter((action) => {
    const haystack = `${action.label} ${action.description} ${action.group}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-[rgba(3,6,10,.72)] px-4 py-14 backdrop-blur-xl"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            initial={{ opacity: 0, y: 18, scale: 0.98 }}
            ref={dialogRef}
            role="dialog"
            aria-labelledby={titleId}
            aria-modal="true"
            tabIndex={-1}
            transition={springs.snappy}
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => handleDialogKeyDown(event, dialogRef, onClose)}
          >
            <Card className="w-[min(720px,calc(100vw-2rem))] overflow-hidden">
              <h2 id={titleId} className="sr-only">
                Command palette
              </h2>
              <div className="flex items-center gap-3 border-b border-white/10 px-4 py-4">
                <Command className="size-4 text-[var(--accent)]" />
                <Input
                  aria-label="Search commands"
                  ref={inputRef}
                  className="border-transparent bg-transparent px-0 shadow-none focus:border-transparent focus:bg-transparent focus:ring-0"
                  placeholder="Launch scenarios, export runs, jump to views..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>

              <div className="max-h-[65vh] overflow-y-auto p-3">
                {filtered.map((action) => (
                  <button
                    key={action.id}
                    className="flex w-full items-center gap-3 rounded-[1.2rem] px-3 py-3 text-left transition hover:bg-white/[0.06]"
                    onClick={() => {
                      action.onSelect();
                      onClose();
                    }}
                    type="button"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white">{action.label}</p>
                      <p className="text-xs text-[var(--text-secondary)]">{action.description}</p>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-[var(--text-muted)]">
                      <span>{action.group}</span>
                      {action.shortcut ? <span>{action.shortcut}</span> : <CornerDownLeft className="size-3" />}
                    </div>
                  </button>
                ))}

                {!filtered.length ? (
                  <div className="rounded-[1.3rem] border border-dashed border-white/10 p-6 text-center text-sm text-[var(--text-secondary)]">
                    No commands match this query.
                  </div>
                ) : null}
              </div>
            </Card>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
