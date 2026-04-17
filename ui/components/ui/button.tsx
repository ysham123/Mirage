"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "ghost" | "outline" | "danger";
type ButtonSize = "sm" | "md" | "icon";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[linear-gradient(135deg,rgba(40,239,255,.24),rgba(0,140,255,.16))] text-white shadow-[0_0_0_1px_rgba(111,231,255,.18),0_18px_50px_rgba(0,161,255,.24)] hover:shadow-[0_0_0_1px_rgba(111,231,255,.3),0_20px_60px_rgba(0,161,255,.32)]",
  ghost:
    "bg-transparent text-[var(--text-secondary)] hover:bg-white/6 hover:text-white",
  outline:
    "border border-white/10 bg-white/[0.03] text-white hover:border-[var(--border-strong)] hover:bg-white/[0.06]",
  danger:
    "border border-[rgba(255,107,129,.24)] bg-[rgba(255,107,129,.12)] text-[rgb(255,188,199)] hover:bg-[rgba(255,107,129,.18)]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-[11px]",
  md: "h-11 px-4 text-[12px]",
  icon: "size-10 px-0",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-medium uppercase tracking-[0.16em] transition duration-200 ease-out disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(111,231,255,.4)] focus-visible:ring-offset-2 focus-visible:ring-offset-black",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = "Button";
