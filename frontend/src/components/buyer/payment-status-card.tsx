"use client";

import { useEffect, useState, useRef } from "react";
import { CheckCircle2, Circle, Loader2, RefreshCw } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TransactionStatusBadge } from "@/components/shared/status-badge";
import { RecoveryPanel } from "@/components/shared/recovery-panel";
import { Button } from "@/components/ui/button";
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
  const { state, actions } = useCommerce();
  const transaction = state.transactions[transactionId];
  const [timedOut, setTimedOut] = useState(false);
  const checkoutOpened = useRef(false);

  // Poll for completion
  useEffect(() => {
    if (!transaction) return;
    if (transaction.state !== "PAYMENT_PENDING" && transaction.state !== "VERIFYING") return;
    if (timedOut) return;

    let attempts = 0;
    const maxAttempts = 24; // 24 attempts * 2.5 seconds = 60 seconds limit for UI checkout

    const timer = setInterval(() => {
      attempts++;
      if (attempts >= maxAttempts) {
        setTimedOut(true);
        clearInterval(timer);
      } else {
        onRefresh();
      }
    }, 2500);

    return () => clearInterval(timer);
  }, [transaction?.state, onRefresh, timedOut]);

  // Open Razorpay Checkout popup
  useEffect(() => {
    if (!transaction || checkoutOpened.current) return;
    
    // Only open if state is PAYMENT_PENDING and we have a Razorpay order ID
    if (transaction.state === "PAYMENT_PENDING" && transaction.providerPhase?.providerOrderId) {
      checkoutOpened.current = true;
      
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => {
        const options = {
          key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "[REDACTED]",
          amount: transaction.amount.amount_minor.toString(),
          currency: transaction.amount.currency,
          name: "AI Commerce Demo",
          description: "Test Transaction",
          order_id: transaction.providerPhase!.providerOrderId,
          handler: function (response: any) {
            console.log("Razorpay payment successful", response);
            actions.verifyCheckout(
              transactionId,
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            ).then(() => {
              onRefresh();
            }).catch((err) => {
              console.error("Verification failed", err);
              onRefresh();
            });
          },
          prefill: {
            name: "Test Buyer",
            email: "buyer@example.com",
            contact: "9999999999"
          },
          theme: {
            color: "#3399cc"
          }
        };
        // @ts-ignore
        const rzp = new window.Razorpay(options);
        rzp.on('payment.failed', function (response: any) {
          console.error("Payment failed", response.error);
          onRefresh();
        });
        rzp.open();
      };
      document.body.appendChild(script);
    }
  }, [transaction, onRefresh]);

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

  if (timedOut) {
    return (
      <Card className="border-destructive/30 bg-destructive/5">
        <CardContent className="flex flex-col items-center justify-center gap-3 p-6">
          <p className="text-sm text-center font-medium">
            Payment confirmation timed out
          </p>
          <p className="text-sm text-center text-muted-foreground">
            The payment provider took too long to respond (60s limit reached). The payment may have failed or is stuck in pending.
          </p>
          <Button 
            variant="outline"
            onClick={() => { setTimedOut(false); checkoutOpened.current = false; onRefresh(); }}
            disabled={refreshing}
          >
            {refreshing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {refreshing ? "Checking status..." : "Check status again"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="text-base">
          {verifying ? "Verifying payment" : "Payment submitted"}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {verifying
            ? "We're confirming the payment provider's authoritative result."
            : "Please complete the Razorpay checkout to finish your payment."}
        </p>
      </CardHeader>
      <CardContent className="p-5 pt-0">
        <PaymentSteps current={verifying ? 1 : 0} />
      </CardContent>
    </Card>
  );
}
