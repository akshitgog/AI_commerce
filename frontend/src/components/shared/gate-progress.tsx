"use client";

// Six-stage trust progression view. Buyer authorization and merchant
// acceptance are ALWAYS separate rows — the gates are never collapsed.

import {
  CheckCircle2,
  Circle,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import {
  gateProgress,
  gateStageLabel,
  type GateStage,
  type GateStageStatus,
} from "@/lib/status";
import type { TransactionState } from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGE_ORDER: GateStage[] = [
  "PROPOSAL",
  "BUYER_AUTHORIZATION",
  "MERCHANT_ACCEPTANCE",
  "PAYMENT",
  "VERIFICATION",
  "COMPLETE",
];

function StageIcon({ status }: { status: GateStageStatus }) {
  switch (status) {
    case "done":
      return <CheckCircle2 className="size-4 text-emerald-600" aria-hidden />;
    case "current":
      return (
        <Loader2 className="size-4 animate-spin text-foreground" aria-hidden />
      );
    case "recovering":
      return (
        <RefreshCw
          className="size-4 animate-[spin_2.5s_linear_infinite] text-amber-600"
          aria-hidden
        />
      );
    case "failed":
      return <XCircle className="size-4 text-destructive" aria-hidden />;
    case "pending":
      return <Circle className="size-4 text-muted-foreground/40" aria-hidden />;
  }
}

/** Vertical 6-stage purchase progress list driven by gateProgress(state). */
export function GateProgressView({
  state,
  className,
}: {
  state: TransactionState;
  className?: string;
}) {
  const progress = gateProgress(state);
  return (
    <div className={cn("text-sm", className)}>
      <div className="mb-3 text-sm font-medium">Purchase progress</div>
      <ol className="space-y-0" aria-label="Purchase progress">
        {STAGE_ORDER.map((stage, index) => {
          const status = progress[stage];
          const isLast = index === STAGE_ORDER.length - 1;
          return (
            <li key={stage} className="relative flex gap-3">
              {!isLast && (
                <span
                  aria-hidden
                  className="absolute left-[7px] top-5 h-[calc(100%-12px)] w-px bg-border"
                />
              )}
              <span className="relative z-10 mt-0.5 flex size-4 shrink-0 items-center justify-center bg-white">
                <StageIcon status={status} />
              </span>
              <div className={cn("pb-4", isLast && "pb-0")}>
                <span
                  className={cn(
                    status === "pending" && "text-muted-foreground",
                    status === "current" && "font-medium",
                    status === "recovering" && "font-medium text-amber-700",
                    status === "failed" && "text-destructive",
                  )}
                >
                  {gateStageLabel(stage)}
                </span>
                {status === "recovering" && (
                  <span className="ml-2 text-xs text-amber-700">
                    Recovering — checking provider
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
