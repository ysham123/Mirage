import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "critical" | "suppressed";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "border-white/10 bg-white/6 text-[var(--text-secondary)]",
  success: "border-[rgba(70,255,196,.18)] bg-[rgba(70,255,196,.12)] text-[rgb(142,255,223)]",
  warning: "border-[rgba(255,173,61,.18)] bg-[rgba(255,173,61,.12)] text-[rgb(255,214,145)]",
  critical: "border-[rgba(255,90,124,.2)] bg-[rgba(255,90,124,.12)] text-[rgb(255,185,201)]",
  suppressed: "border-[rgba(111,231,255,.2)] bg-[rgba(111,231,255,.12)] text-[rgb(176,244,255)]",
};

export function Badge({
  className,
  children,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
