"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

import type { Money } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { Button } from "@/components/ui/button";

interface BuyerAuthorizationCardProps {
  total: Money;
  quantity: number;
  approved: boolean;
  busy: boolean;
  onApprove: () => void;
  onCancel: () => void;
}

export function BuyerAuthorizationCard({
  total,
  quantity,
  approved,
  busy,
  onApprove,
  onCancel,
}: BuyerAuthorizationCardProps) {
  if (approved) {
    return (
      <div
        className="flex items-start gap-2 rounded-md bg-success p-3"
        role="status"
      >
        <CheckCircle2
          className="mt-0.5 size-4 shrink-0 text-success"
          aria-hidden
        />
        <div>
          <p className="text-sm font-medium text-success">Approved by you</p>
          <p className="text-sm text-success tnum">
            {formatMoney(total)} · Quantity {quantity}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Buyer authorization
        </p>
        <div className="mt-1.5 flex items-center gap-2">
          <Circle className="size-4 text-warning" aria-hidden />
          <p className="text-sm font-medium">Approval required</p>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          This purchase has not been authorized yet.
        </p>
      </div>
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button size="sm" onClick={onApprove} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" aria-hidden /> : null}
          Approve {formatMoney(total)}
        </Button>
      </div>
    </div>
  );
}
