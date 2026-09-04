"use client";

import { CheckCircle2 } from "lucide-react";

import type { Money } from "@/lib/types";
import { TrustedTotal } from "@/components/shared/money";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface ReadyForPaymentCardProps {
  total: Money;
  busy: boolean;
  onContinue: () => void;
}

export function ReadyForPaymentCard({
  total,
  busy,
  onContinue,
}: ReadyForPaymentCardProps) {
  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="text-base">Ready for payment</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 p-5 pt-0">
        <div className="flex flex-col gap-1.5">
          <p className="flex items-center gap-2 text-sm text-success">
            <CheckCircle2 className="size-4" aria-hidden />
            Buyer authorized
          </p>
          <p className="flex items-center gap-2 text-sm text-success">
            <CheckCircle2 className="size-4" aria-hidden />
            Merchant accepted
          </p>
        </div>
        <Separator />
        <TrustedTotal money={total} />
        <div>
          <Button onClick={onContinue} disabled={busy}>
            Continue to secure payment
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
