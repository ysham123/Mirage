import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "glass-panel rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,.08),rgba(255,255,255,.03))] shadow-[0_10px_40px_rgba(0,0,0,.25)]",
        className,
      )}
      {...props}
    />
  );
}
