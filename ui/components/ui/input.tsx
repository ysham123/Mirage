import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-[1.1rem] border border-white/10 bg-white/[0.03] px-4 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,.05)] outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:bg-white/[0.05] focus:ring-2 focus:ring-[rgba(111,231,255,.24)]",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
