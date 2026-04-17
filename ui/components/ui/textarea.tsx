import * as React from "react";

import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-24 w-full resize-none rounded-[1.4rem] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,.05)] outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:bg-white/[0.05] focus:ring-2 focus:ring-[rgba(111,231,255,.24)]",
        className,
      )}
      {...props}
    />
  ),
);

Textarea.displayName = "Textarea";
