"use client";

import { useEffect, useEffectEvent } from "react";

export function isTypingTarget(target: EventTarget | null) {
  const element = target as HTMLElement | null;
  if (!element) {
    return false;
  }
  const tag = element.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || element.isContentEditable;
}

export function isCommandShortcut(event: KeyboardEvent) {
  return (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
}

interface ShortcutHandlers {
  onCommandPalette: () => void;
  onFocusSearch: () => void;
  onToggleSidebar: () => void;
  onExport: () => void;
  onSuppress: () => void;
  onNext: () => void;
  onPrevious: () => void;
  onView: (viewIndex: 1 | 2 | 3) => void;
  onEscape: () => void;
}

export function useConsoleShortcuts(handlers: ShortcutHandlers, enabled = true) {
  const onKeyDown = useEffectEvent((event: KeyboardEvent) => {
    if (!enabled) {
      return;
    }

    if (isCommandShortcut(event)) {
      event.preventDefault();
      handlers.onCommandPalette();
      return;
    }

    if (isTypingTarget(event.target)) {
      if (event.key === "Escape") {
        handlers.onEscape();
      }
      return;
    }

    if (event.key === "/" || event.key.toLowerCase() === "f") {
      event.preventDefault();
      handlers.onFocusSearch();
      return;
    }

    if (event.key === "[") {
      handlers.onToggleSidebar();
      return;
    }

    if (event.key.toLowerCase() === "e") {
      handlers.onExport();
      return;
    }

    if (event.key.toLowerCase() === "s") {
      handlers.onSuppress();
      return;
    }

    if (event.key === "j" || event.key === "ArrowDown") {
      event.preventDefault();
      handlers.onNext();
      return;
    }

    if (event.key === "k" || event.key === "ArrowUp") {
      event.preventDefault();
      handlers.onPrevious();
      return;
    }

    if (event.key === "1" || event.key === "2" || event.key === "3") {
      handlers.onView(Number(event.key) as 1 | 2 | 3);
      return;
    }

    if (event.key === "Escape") {
      handlers.onEscape();
    }
  });

  useEffect(() => {
    if (!enabled) {
      return;
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [enabled, onKeyDown]);
}
