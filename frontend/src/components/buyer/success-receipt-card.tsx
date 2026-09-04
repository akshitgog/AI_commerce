"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { MoneyText } from "@/components/shared/money";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { TransactionTechnicalDetails } from "./transaction-technical-details";

interface SuccessReceiptCardProps {
  transactionId: string;
}

export function SuccessReceiptCard({ transactionId }: SuccessReceiptCardProps) {
  const { state } = useCommerce();
  const [showDetails, setShowDetails] = useState(false);

  const transaction = state.transactions[transactionId];
  if (!transaction) return null;

  const product = state.products.find(
    (entry) => entry.id === transaction.productId,
  );

  return (
    <div aria-live="assertive">
      <Card className="bg-success">
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-success" aria-hidden />
            <CardTitle className="text-base text-success">
              Payment verified
            </CardTitle>
          </div>
          <p className="text-sm text-muted-foreground">
            Purchase completed successfully.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-5 pt-0">
          <div>
            <p className="text-sm font-medium">{product?.title ?? "Product"}</p>
            <p className="text-sm text-muted-foreground">
              {state.merchant.name}
            </p>
          </div>
          <Separator />
          <dl className="flex flex-col gap-1.5 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Total paid</dt>
              <dd>
                <MoneyText money={transaction.amount} size="lg" />
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Transaction</dt>
              <dd className="font-mono text-xs tnum">{transaction.id}</dd>
            </div>
          </dl>
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDetails((open) => !open)}
              aria-expanded={showDetails}
            >
              {showDetails
                ? "Hide transaction details"
                : "View transaction details"}
            </Button>
          </div>
          {showDetails ? (
            <TransactionTechnicalDetails transactionId={transactionId} />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
