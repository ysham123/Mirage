"use client";

import { CheckCircle2, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SideEffect } from "@/types/console";

interface SuppressActionProps {
  effect: SideEffect;
  onSuppress: (effect: SideEffect) => void;
}

export function SuppressAction({ effect, onSuppress }: SuppressActionProps) {
  if (effect.suppressed) {
    return (
      <div className="flex items-center gap-2">
        <Badge tone="suppressed">suppressed</Badge>
        <span className="text-xs text-[var(--text-muted)]">{effect.suppression?.reason}</span>
      </div>
    );
  }

  return (
    <Button size="sm" variant="outline" onClick={() => onSuppress(effect)}>
      <Sparkles className="size-3.5" />
      Suppress
    </Button>
  );
}
