"use client";

// Recovery treatment for UNKNOWN/RECONCILING ("Recovering"). Communicates that
// the provider result is temporarily uncertain, that the authoritative result
// is being checked, and that no duplicate payment will be attempted.
// NEVER renders Pay Again / Retry Payment.

import { RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/format";
import { useNow } from "@/lib/services/provider";
import type { Transaction } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Calm recovery panel with a safe "Check status" action (never a retry). */
export function RecoveryPanel({
  transaction,
  onRefresh,
  refreshing,
  className,
}: {
  transaction: Transaction;
  onRefresh: () => void;
  refreshing: boolean;
  className?: string;
}) {
  // Re-render periodically so the "Last checked" relative time stays fresh.
  useNow(5000);
  const lastChecked =
    transaction.providerPhase?.lastVerifiedAt ?? transaction.updatedAt;

  return (
    <Alert variant="recovery" className={className} role="status">
      <RefreshCw className="size-4" aria-hidden />
      <AlertTitle>Recovering payment status</AlertTitle>
      <AlertDescription>
        <p>
          The payment provider&apos;s result is temporarily uncertain.
          We&apos;re checking the provider for the authoritative result. No
          duplicate payment will be attempted.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span className="tnum text-xs">
            Last checked: {formatRelativeTime(lastChecked)}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={refreshing}
          >
            <RefreshCw
              className={cn("size-3.5", refreshing && "animate-spin")}
              aria-hidden
            />
            {refreshing ? "Checking…" : "Check status"}
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
