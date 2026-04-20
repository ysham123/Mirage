"use client";

import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SideEffect } from "@/types/console";

interface SuppressActionProps {
  effect: SideEffect;
  disabled?: boolean;
  onSuppress: (effect: SideEffect) => void;
}

export function SuppressAction({ effect, disabled, onSuppress }: SuppressActionProps) {
  if (effect.suppressed) {
    return (
      <div className="flex items-center gap-2">
        <Badge tone="suppressed">suppressed</Badge>
        <span className="text-xs text-[var(--text-muted)]">{effect.suppression?.reason}</span>
      </div>
    );
  }

  return (
    <Button
      disabled={disabled}
      size="sm"
      variant="outline"
      onClick={(event) => {
        event.stopPropagation();
        onSuppress(effect);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.stopPropagation();
        }
      }}
    >
      <Sparkles className="size-3.5" />
      {disabled ? "Suppressing" : "Suppress"}
    </Button>
  );
}
