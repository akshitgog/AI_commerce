"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, XCircle } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { formatMoney } from "@/lib/format";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MerchantAcceptanceCardProps {
  proposalId: string;
}

function StatusRow({
  icon,
  title,
  tone,
  children,
}: {
  icon: ReactNode;
  title: string;
  tone: "success" | "attention" | "destructive" | "neutral";
  children: ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <span
        className={cn(
          "mt-0.5 shrink-0",
          tone === "success" && "text-success",
          tone === "attention" && "text-warning",
          tone === "destructive" && "text-destructive",
          tone === "neutral" && "text-muted-foreground",
        )}
        aria-hidden
      >
        {icon}
      </span>
      <div>
        <p
          className={cn(
            "text-sm font-medium",
            tone === "success" && "text-success",
            tone === "attention" && "text-warning",
            tone === "destructive" && "text-destructive",
          )}
        >
          {title}
        </p>
        <div className="mt-0.5 text-sm text-muted-foreground">{children}</div>
      </div>
    </div>
  );
}

export function MerchantAcceptanceCard({
  proposalId,
}: MerchantAcceptanceCardProps) {
  const { state } = useCommerce();
  const decision = state.decisions[proposalId];
  const proposal = state.proposals[proposalId];
  const merchantName = state.merchant.name;

  let body: ReactNode;

  if (!decision) {
    body = (
      <StatusRow
        icon={<Circle className="size-4" />}
        title="Awaiting merchant decision"
        tone="neutral"
      >
        {merchantName} is evaluating this purchase against its current policy.
      </StatusRow>
    );
  } else if (decision.decision === "ALLOW" && decision.decidedBy === "POLICY") {
    const limit = state.policy.maxAmount
      ? formatMoney(state.policy.maxAmount)
      : null;
    body = (
      <StatusRow
        icon={<CheckCircle2 className="size-4" />}
        title="Automatically accepted"
        tone="success"
      >
        <p>
          {merchantName} automatically accepts eligible purchases
          {limit ? ` up to ${limit}` : ""}.
          {proposal ? ` This purchase: ${formatMoney(proposal.total)}.` : ""}
        </p>
      </StatusRow>
    );
  } else if (decision.decision === "ALLOW") {
    body = (
      <StatusRow
        icon={<CheckCircle2 className="size-4" />}
        title="Approved by merchant"
        tone="success"
      >
        <p>{merchantName} approved this purchase.</p>
      </StatusRow>
    );
  } else if (decision.decision === "REVIEW_REQUIRED") {
    body = (
      <StatusRow
        icon={<Circle className="size-4" />}
        title="Merchant review required"
        tone="attention"
      >
        <p>
          {merchantName} needs to review this purchase. We&apos;ll update this
          transaction when the merchant responds.
        </p>
        <p className="mt-1 text-xs">
          Switch to the{" "}
          <Link
            href="/merchant/review"
            className="font-medium underline underline-offset-2"
          >
            Merchant dashboard → Review Queue
          </Link>{" "}
          to approve.
        </p>
      </StatusRow>
    );
  } else {
    body = (
      <StatusRow
        icon={<XCircle className="size-4" />}
        title="Not accepted"
        tone="destructive"
      >
        <p>The merchant&apos;s current policy does not allow this purchase.</p>
      </StatusRow>
    );
  }

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Merchant acceptance
        </p>
      </CardHeader>
      <CardContent className="p-5 pt-0">{body}</CardContent>
    </Card>
  );
}
