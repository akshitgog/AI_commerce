"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ReceiptText } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { formatDateTime } from "@/lib/format";
import { humanTransactionLabel } from "@/lib/status";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MoneyText, TrustedTotal } from "@/components/shared/money";
import {
  AuthorizationStatusBadge,
  MerchantDecisionBadge,
  TransactionStatusBadge,
} from "@/components/shared/status-badge";
import { GateProgressView } from "@/components/shared/gate-progress";
import { AuditTimeline } from "@/components/shared/audit-timeline";
import { RecoveryPanel } from "@/components/shared/recovery-panel";
import { ProposalSummary } from "@/components/merchant/proposal-summary";
import { EmptyState } from "@/components/merchant/empty-state";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-right text-sm font-medium">{children}</dd>
    </div>
  );
}

export default function TransactionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { state, actions } = useCommerce();
  const [refreshing, setRefreshing] = useState(false);

  const txn = state.transactions[params.id];

  if (!txn) {
    return (
      <EmptyState
        icon={ReceiptText}
        title="Transaction not found"
        description="This transaction may not exist in the current session."
        action={
          <Button
            variant="outline"
            onClick={() => router.push("/merchant/transactions")}
          >
            Back to transactions
          </Button>
        }
      />
    );
  }

  const product = state.products.find((p) => p.id === txn.productId);
  const proposal = state.proposals[txn.proposalId];
  const authorization = Object.values(state.authorizations).find(
    (a) => a.proposalId === txn.proposalId
  );
  const decision = Object.values(state.decisions).find(
    (d) => d.proposalId === txn.proposalId
  );
  const auditEvents = state.audit[txn.id] ?? actions.getAudit(txn.id) ?? [];

  const recovering = txn.state === "UNKNOWN" || txn.state === "RECONCILING";

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await actions.refreshTransaction(txn!.id);
    } catch {
      // RecoveryPanel copy already explains uncertainty; state stays as-is.
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/merchant/transactions")}
        >
          <ArrowLeft aria-hidden />
          Transactions
        </Button>
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="tnum font-mono text-xs text-muted-foreground">
              {txn.id}
            </p>
            <h2 className="truncate text-lg font-semibold">
              {product?.title ?? txn.productId}
            </h2>
          </div>
          <TrustedTotal money={txn.amount} />
          <div aria-live="polite">
            <TransactionStatusBadge state={txn.state} />
          </div>
        </div>
        <p className="sr-only" aria-live="polite">
          Transaction status: {humanTransactionLabel(txn.state)}
        </p>
      </div>

      {/* Lifecycle */}
      <Card>
        <CardContent className="p-4 md:p-6">
          <GateProgressView state={txn.state} />
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Purchase Proposal */}
        <Card>
          <CardHeader>
            <CardTitle>Purchase Proposal</CardTitle>
            <CardDescription>
              The exact, backend-derived purchase the buyer authorized.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {proposal ? (
              <ProposalSummary proposal={proposal} product={product} />
            ) : (
              <p className="text-sm text-muted-foreground">
                Proposal details unavailable.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Buyer Authorization */}
        <Card>
          <CardHeader>
            <CardTitle>Buyer Authorization</CardTitle>
            <CardDescription>
              Buyer consent only — not merchant acceptance.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {authorization ? (
              <dl className="divide-y divide-border">
                <Row label="Status">
                  <AuthorizationStatusBadge status={authorization.status} />
                </Row>
                <Row label="Approved by">
                  {authorization.authorizedBy ?? (
                    <span className="text-muted-foreground">Not approved</span>
                  )}
                </Row>
                <Row label="Max amount">
                  <MoneyText money={authorization.maxAmount} />
                </Row>
                <Row label="Max quantity">
                  <span className="tnum">{authorization.maxQuantity}</span>
                </Row>
                <Row label="Expires">
                  <span className="tnum text-xs">
                    {formatDateTime(authorization.expiresAt)}
                  </span>
                </Row>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                No buyer authorization recorded.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Merchant Decision */}
        <Card>
          <CardHeader>
            <CardTitle>Merchant Decision</CardTitle>
            <CardDescription>
              Your independent acceptance, per your purchase policy.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {decision ? (
              <dl className="divide-y divide-border">
                <Row label="Decision">
                  <MerchantDecisionBadge
                    decision={decision.decision}
                    decidedBy={decision.decidedBy}
                  />
                </Row>
                <Row label="Decided by">
                  {decision.decidedBy === "POLICY"
                    ? "Merchant policy"
                    : "Merchant user"}
                </Row>
                <Row label="Reason code">
                  <span className="tnum font-mono text-xs">
                    {decision.reasonCode}
                  </span>
                </Row>
                <Row label="Policy version">
                  <span className="tnum font-mono text-xs">
                    v{decision.policyVersion}
                  </span>
                </Row>
                <Row label="Decided at">
                  <span className="tnum text-xs">
                    {formatDateTime(decision.createdAt)}
                  </span>
                </Row>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                No merchant decision recorded yet.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Payment */}
        <Card>
          <CardHeader>
            <CardTitle>Payment</CardTitle>
            <CardDescription>
              Provider-side payment phase. Only verified outcomes count as
              success.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <dl className="divide-y divide-border">
              <Row label="Provider">
                {txn.providerPhase ? (
                  txn.providerPhase.provider
                ) : (
                  <span className="text-muted-foreground">Not started</span>
                )}
              </Row>
              <Row label="Order state">
                {txn.providerPhase?.orderState ? (
                  <span className="tnum font-mono text-xs">
                    {txn.providerPhase.orderState}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </Row>
              <Row label="Payment state">
                {txn.providerPhase?.paymentState ? (
                  <span className="tnum font-mono text-xs">
                    {txn.providerPhase.paymentState}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </Row>
              <Row label="Last verified">
                {txn.providerPhase?.lastVerifiedAt ? (
                  <span className="tnum text-xs">
                    {formatDateTime(txn.providerPhase.lastVerifiedAt)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">Not verified</span>
                )}
              </Row>
            </dl>
            {txn.providerPhase?.orderState &&
            !txn.providerPhase?.lastVerifiedAt ? (
              <p className="rounded-md border bg-muted/50 p-2 text-xs text-muted-foreground">
                Provider order creation is not payment success.
              </p>
            ) : null}
          </CardContent>
        </Card>

        {/* Recovery */}
        {recovering ? (
          <RecoveryPanel
            transaction={txn}
            onRefresh={handleRefresh}
            refreshing={refreshing}
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Recovery</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">No recovery active.</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Audit */}
      <Card>
        <CardHeader>
          <CardTitle>Audit timeline</CardTitle>
          <CardDescription>
            Causal history of decisions and state changes for this transaction.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {auditEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No audit events recorded for this transaction.
            </p>
          ) : (
            <AuditTimeline events={auditEvents} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
