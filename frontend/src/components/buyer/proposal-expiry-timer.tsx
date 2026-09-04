"use client";

import { Clock, Timer } from "lucide-react";

import { useNow } from "@/lib/services/provider";
import { formatCountdown } from "@/lib/format";
import { cn } from "@/lib/utils";

const URGENT_THRESHOLD_MS = 2 * 60 * 1000;

interface ProposalExpiryTimerProps {
  expiresAt: string;
}

export function ProposalExpiryTimer({ expiresAt }: ProposalExpiryTimerProps) {
  const now = useNow(1000);
  const remaining = new Date(expiresAt).getTime() - now;

  if (remaining <= 0) {
    return (
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Clock className="size-3.5" aria-hidden />
        Proposal expired
      </p>
    );
  }

  const urgent = remaining < URGENT_THRESHOLD_MS;

  return (
    <p
      className={cn(
        "flex items-center gap-1.5 text-xs tnum",
        urgent ? "font-medium text-warning" : "text-muted-foreground",
      )}
    >
      {urgent ? (
        <Timer className="size-3.5" aria-hidden />
      ) : (
        <Clock className="size-3.5" aria-hidden />
      )}
      Proposal expires in {formatCountdown(expiresAt, now)}
    </p>
  );
}
