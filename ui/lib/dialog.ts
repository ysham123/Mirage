import type { KeyboardEvent, RefObject } from "react";
import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

function getFocusableElements(container: HTMLElement | null) {
  if (!container) {
    return [];
  }

  return [...container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)].filter((element) => {
    const style = window.getComputedStyle(element);
    return !element.hasAttribute("disabled") && style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length > 0;
  });
}

export function handleDialogKeyDown(
  event: KeyboardEvent<HTMLElement>,
  containerRef: RefObject<HTMLElement | null>,
  onClose: () => void,
) {
  if (event.key === "Escape") {
    event.preventDefault();
    onClose();
    return;
  }

  if (event.key !== "Tab") {
    return;
  }

  const container = containerRef.current;
  const focusable = getFocusableElements(container);
  if (!focusable.length) {
    event.preventDefault();
    container?.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement as HTMLElement | null;
  const activeInside = !!active && !!container?.contains(active);

  if (event.shiftKey) {
    if (!activeInside || active === first) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (!activeInside || active === last) {
    event.preventDefault();
    first.focus();
  }
}

export function useDialogFocus(
  open: boolean,
  containerRef: RefObject<HTMLElement | null>,
  initialFocusRef?: RefObject<HTMLElement | null>,
) {
  const returnFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    returnFocusRef.current = document.activeElement as HTMLElement | null;
    const frame = window.requestAnimationFrame(() => {
      const nextFocus = initialFocusRef?.current ?? getFocusableElements(containerRef.current)[0] ?? containerRef.current;
      nextFocus?.focus();
    });

    return () => {
      window.cancelAnimationFrame(frame);
      returnFocusRef.current?.focus();
    };
  }, [containerRef, initialFocusRef, open]);
}
