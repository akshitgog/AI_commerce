import type { Product, Proposal } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { MoneyText, TrustedTotal } from "@/components/shared/money";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-right">{children}</dd>
    </div>
  );
}

/**
 * Display-only rendering of the trusted, backend-derived proposal.
 * Money values come straight from the proposal — never derived client-side.
 */
export function ProposalSummary({
  proposal,
  product,
}: {
  proposal: Proposal;
  product?: Product;
}) {
  return (
    <dl className="divide-y divide-border">
      <Row label="Product">{product?.title ?? proposal.productId}</Row>
      <Row label="Product version">
        <span className="tnum">v{proposal.productVersion}</span>
      </Row>
      <Row label="Quantity">
        <span className="tnum">{proposal.quantity}</span>
      </Row>
      <Row label="Unit price">
        <MoneyText money={proposal.unitPrice} />
      </Row>
      <Row label="Trusted total">
        <TrustedTotal money={proposal.total} />
      </Row>
      <Row label="Proposal hash">
        <span className="tnum font-mono text-xs" title={proposal.proposalHash}>
          {proposal.proposalHash.slice(0, 16)}…
        </span>
      </Row>
      <Row label="Expires">{formatDateTime(proposal.expiresAt)}</Row>
    </dl>
  );
}
