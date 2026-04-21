"use client";

import { useEffect, useRef } from "react";

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
  const handlersRef = useRef(handlers);
  const enabledRef = useRef(enabled);

  useEffect(() => {
    handlersRef.current = handlers;
    enabledRef.current = enabled;
  }, [enabled, handlers]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!enabledRef.current) {
        return;
      }

      const currentHandlers = handlersRef.current;

      if (isCommandShortcut(event)) {
        event.preventDefault();
        currentHandlers.onCommandPalette();
        return;
      }

      if (isTypingTarget(event.target)) {
        if (event.key === "Escape") {
          currentHandlers.onEscape();
        }
        return;
      }

      if (event.key === "/" || event.key.toLowerCase() === "f") {
        event.preventDefault();
        currentHandlers.onFocusSearch();
        return;
      }

      if (event.key === "[") {
        currentHandlers.onToggleSidebar();
        return;
      }

      if (event.key.toLowerCase() === "e") {
        currentHandlers.onExport();
        return;
      }

      if (event.key.toLowerCase() === "s") {
        currentHandlers.onSuppress();
        return;
      }

      if (event.key === "j" || event.key === "ArrowDown") {
        event.preventDefault();
        currentHandlers.onNext();
        return;
      }

      if (event.key === "k" || event.key === "ArrowUp") {
        event.preventDefault();
        currentHandlers.onPrevious();
        return;
      }

      if (event.key === "1" || event.key === "2" || event.key === "3") {
        currentHandlers.onView(Number(event.key) as 1 | 2 | 3);
        return;
      }

      if (event.key === "Escape") {
        currentHandlers.onEscape();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}
