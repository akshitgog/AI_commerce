"use client";

import { useCommerce, useNow } from "@/lib/services/provider";
import { gateProgress } from "@/lib/status";
import { MoneyText, TrustedTotal } from "@/components/shared/money";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { BuyerAuthorizationCard } from "./buyer-authorization-card";
import { ExpiredProposalCard } from "./expired-proposal-card";
import { MerchantAcceptanceCard } from "./merchant-acceptance-card";
import { ProposalExpiryTimer } from "./proposal-expiry-timer";
import { ReadyForPaymentCard } from "./ready-for-payment-card";

interface ProposalCardProps {
  proposalId: string;
  closed?: "cancelled" | "expired";
  busy: boolean;
  onCancel: () => void;
  onApprove: () => void;
  onCreateNew: (productId: string) => void;
  onContinueToPayment: () => void;
}

export function ProposalCard({
  proposalId,
  closed,
  busy,
  onCancel,
  onApprove,
  onCreateNew,
  onContinueToPayment,
}: ProposalCardProps) {
  const { state } = useCommerce();
  const now = useNow(1000);

  const proposal = state.proposals[proposalId];
  if (!proposal) return null;

  const product = state.products.find((entry) => entry.id === proposal.productId);
  const transaction = Object.values(state.transactions).find(
    (entry) => entry.proposalId === proposalId,
  );
  const authorization = Object.values(state.authorizations)
    .filter((entry) => entry.proposalId === proposalId)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt))
    .at(-1);

  const approved =
    authorization?.status === "APPROVED" ||
    (transaction
      ? gateProgress(transaction.state).BUYER_AUTHORIZATION === "done"
      : false);

  const isCancelled =
    closed === "cancelled" ||
    proposal.status === "CANCELLED" ||
    transaction?.state === "CANCELLED";
  const timeExpired = !approved && new Date(proposal.expiresAt).getTime() <= now;
  const isExpired =
    !isCancelled &&
    (closed === "expired" ||
      proposal.status === "EXPIRED" ||
      transaction?.state === "EXPIRED" ||
      timeExpired);

  if (isCancelled) {
    return (
      <Card className="bg-muted/50">
        <CardHeader className="p-5 pb-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Purchase Proposal
          </p>
          <CardTitle className="text-base text-muted-foreground">
            Proposal cancelled
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-0 text-sm text-muted-foreground">
          This purchase proposal was cancelled. No payment was made.
        </CardContent>
      </Card>
    );
  }

  if (isExpired && !approved) {
    return (
      <ExpiredProposalCard
        busy={busy}
        onCreateNew={() => onCreateNew(proposal.productId)}
      />
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <Card className="border-2 border-primary/30 bg-card shadow-sm">
        <CardHeader className="p-5 pb-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-primary">
            Purchase Proposal
          </p>
          <CardTitle className="text-base">
            {product?.title ?? "Product"}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {state.merchant.name}
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-5 pt-0">
          <dl className="flex flex-col gap-1.5 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Quantity</dt>
              <dd className="tnum">{proposal.quantity}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Unit price</dt>
              <dd>
                <MoneyText money={proposal.unitPrice} />
              </dd>
            </div>
          </dl>
          <Separator />
          <TrustedTotal
            money={proposal.total}
            helper="Price derived from the merchant catalog"
          />
          {!approved ? (
            <ProposalExpiryTimer expiresAt={proposal.expiresAt} />
          ) : null}
          <Separator />
          <BuyerAuthorizationCard
            total={proposal.total}
            quantity={proposal.quantity}
            approved={approved}
            busy={busy}
            onApprove={onApprove}
            onCancel={onCancel}
          />
        </CardContent>
      </Card>

      {approved ? <MerchantAcceptanceCard proposalId={proposalId} /> : null}

      {transaction?.state === "READY" ? (
        <ReadyForPaymentCard
          total={proposal.total}
          busy={busy}
          onContinue={onContinueToPayment}
        />
      ) : null}
    </div>
  );
}
