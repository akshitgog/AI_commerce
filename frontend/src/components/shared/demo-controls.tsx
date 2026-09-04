"use client";

// Fixed demo tooling panel. Visually distinct from the product UI (dashed
// border, muted surface) so it never reads as part of the real experience.

import { useState } from "react";
import { FlaskConical, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCommerce } from "@/lib/services/provider";
import type { DemoOutcome } from "@/lib/services/store";
import { cn } from "@/lib/utils";

const OUTCOMES: { value: DemoOutcome; label: string }[] = [
  { value: "auto_success", label: "Auto-accept + success" },
  { value: "manual_review", label: "Manual review" },
  { value: "recovery_success", label: "Recovery → success" },
  { value: "payment_failed", label: "Payment failed" },
];

/** Collapsible bottom-right panel to steer the simulated backend outcome. */
export function DemoControls() {
  const { state, actions } = useCommerce();
  const [open, setOpen] = useState(true);

  return (
    <div className="fixed bottom-4 right-4 z-50 w-72 rounded-md border border-dashed border-muted-foreground/40 bg-muted/80 shadow-sm backdrop-blur">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <FlaskConical className="size-3.5" aria-hidden />
        Demo controls
        <span className="ml-auto text-[11px]">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-dashed border-muted-foreground/40 px-3 py-3">
          <p className="text-[11px] text-muted-foreground">
            Prototype only — simulates backend outcomes.
          </p>
          <div
            className="grid grid-cols-2 gap-1.5"
            role="group"
            aria-label="Simulated outcome"
          >
            {OUTCOMES.map((o) => {
              const active = state.demoOutcome === o.value;
              return (
                <Button
                  key={o.value}
                  type="button"
                  size="sm"
                  variant={active ? "default" : "outline"}
                  aria-pressed={active}
                  onClick={() => actions.setDemoOutcome(o.value)}
                  className={cn("h-auto whitespace-normal px-2 py-1.5 text-xs")}
                >
                  {o.label}
                </Button>
              );
            })}
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => actions.demoReset()}
            className="w-full border-destructive/40 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            <RotateCcw className="size-3.5" aria-hidden />
            Reset demo
          </Button>
        </div>
      )}
    </div>
  );
}
