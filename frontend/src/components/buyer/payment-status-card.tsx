"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TransactionStatusBadge } from "@/components/shared/status-badge";
import { RecoveryPanel } from "@/components/shared/recovery-panel";
import { cn } from "@/lib/utils";
import { FailureCard } from "./failure-card";
import { SuccessReceiptCard } from "./success-receipt-card";

interface PaymentStatusCardProps {
  transactionId: string;
  refreshing: boolean;
  onRefresh: () => void;
}

const STEPS = ["Payment submitted", "Verification", "Final confirmation"];

function PaymentSteps({ current }: { current: number }) {
  return (
    <ol className="flex flex-col gap-1.5">
      {STEPS.map((label, index) => {
        const done = index < current;
        const active = index === current;
        return (
          <li key={label} className="flex items-center gap-2 text-sm">
            {done ? (
              <CheckCircle2 className="size-4 text-success" aria-hidden />
            ) : active ? (
              <Loader2
                className="size-4 animate-spin text-primary"
                aria-hidden
              />
            ) : (
              <Circle className="size-4 text-muted-foreground" aria-hidden />
            )}
            <span
              className={cn(
                done && "text-success",
                active && "font-medium",
                !done && !active && "text-muted-foreground",
              )}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function PaymentStatusCard({
  transactionId,
  refreshing,
  onRefresh,
}: PaymentStatusCardProps) {
  const { state } = useCommerce();
  const transaction = state.transactions[transactionId];
  if (!transaction) return null;

  if (
    transaction.state === "UNKNOWN" ||
    transaction.state === "RECONCILING"
  ) {
    return (
      <RecoveryPanel
        transaction={transaction}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />
    );
  }

  if (transaction.state === "SUCCEEDED") {
    return <SuccessReceiptCard transactionId={transactionId} />;
  }

  if (transaction.state === "FAILED") {
    return <FailureCard transactionId={transactionId} />;
  }

  if (
    transaction.state === "CANCELLED" ||
    transaction.state === "EXPIRED"
  ) {
    return (
      <Card className="bg-muted/50">
        <CardContent className="flex items-center justify-between gap-3 p-4">
          <p className="text-sm text-muted-foreground">
            This transaction is no longer active. No payment was completed.
          </p>
          <TransactionStatusBadge state={transaction.state} />
        </CardContent>
      </Card>
    );
  }

  const verifying = transaction.state === "VERIFYING";

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="text-base">
          {verifying ? "Verifying payment" : "Payment submitted"}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {verifying
            ? "We're confirming the payment provider's authoritative result."
            : "We're waiting for payment confirmation."}
        </p>
      </CardHeader>
      <CardContent className="p-5 pt-0">
        <PaymentSteps current={verifying ? 1 : 0} />
      </CardContent>
    </Card>
  );
}
