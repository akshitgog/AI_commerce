"use client";

import { CreditCard, Loader2, ShieldCheck } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { TrustedTotal } from "@/components/shared/money";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";

interface PaymentHandoffCardProps {
  proposalId: string;
  busy: boolean;
  onPay: () => void;
}

export function PaymentHandoffCard({
  proposalId,
  busy,
  onPay,
}: PaymentHandoffCardProps) {
  const { state } = useCommerce();
  const proposal = state.proposals[proposalId];
  if (!proposal) return null;

  const product = state.products.find((entry) => entry.id === proposal.productId);
  const transaction = Object.values(state.transactions).find(
    (entry) => entry.proposalId === proposalId,
  );
  const started = !!transaction && transaction.state !== "READY";

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-primary">
          <ShieldCheck className="size-3.5" aria-hidden />
          Secure payment
        </p>
        <p className="text-base font-medium leading-tight">
          {product?.title ?? "Product"}
        </p>
        <p className="text-sm text-muted-foreground">{state.merchant.name}</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 p-5 pt-0">
        <TrustedTotal money={proposal.total} />
        <p className="text-sm text-muted-foreground">
          You&apos;ll continue to Razorpay Test Mode to complete the payment.
        </p>
        {started ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Payment submitted — track the status below.
          </p>
        ) : (
          <div>
            <Button onClick={onPay} disabled={busy}>
              {busy ? (
                <Loader2 className="animate-spin" aria-hidden />
              ) : (
                <CreditCard aria-hidden />
              )}
              Continue to payment
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
