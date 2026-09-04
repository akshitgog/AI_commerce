"use client";

import { useState } from "react";
import { XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TransactionTechnicalDetails } from "./transaction-technical-details";

interface FailureCardProps {
  transactionId: string;
}

export function FailureCard({ transactionId }: FailureCardProps) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div aria-live="assertive">
      <Card className="bg-destructive">
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center gap-2">
            <XCircle className="size-5 text-destructive" aria-hidden />
            <CardTitle className="text-base text-destructive">
              Payment unsuccessful
            </CardTitle>
          </div>
          <p className="text-sm text-muted-foreground">
            The payment was not completed. No successful payment was recorded
            for this transaction.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-5 pt-0">
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDetails((open) => !open)}
              aria-expanded={showDetails}
            >
              {showDetails ? "Hide details" : "View details"}
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
