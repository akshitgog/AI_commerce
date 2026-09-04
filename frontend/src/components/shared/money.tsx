"use client";

// Money presentation. Values always come from the service layer; these
// components only format server-provided minor-unit amounts.

import { formatMoney } from "@/lib/format";
import type { Money } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Formatted money with tabular numerals; size "lg" for prominent totals. */
export function MoneyText({
  money,
  className,
  size = "sm",
}: {
  money: Money;
  className?: string;
  size?: "sm" | "lg";
}) {
  return (
    <span
      className={cn(
        "tnum tabular-nums",
        size === "lg" && "text-2xl font-semibold tracking-tight",
        className,
      )}
    >
      {formatMoney(money)}
    </span>
  );
}

/** Labelled trusted-total block; signals the amount is backend-derived. */
export function TrustedTotal({
  money,
  helper = "Price derived from merchant catalog",
  className,
}: {
  money: Money;
  helper?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border border-border bg-white p-4 shadow-sm",
        className,
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Trusted total
      </div>
      <MoneyText money={money} size="lg" className="mt-1 block" />
      {helper ? (
        <div className="mt-1 text-xs text-muted-foreground">{helper}</div>
      ) : null}
    </div>
  );
}
