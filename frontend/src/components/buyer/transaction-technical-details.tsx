"use client";

import { useCommerce } from "@/lib/services/provider";
import { formatDateTime } from "@/lib/format";

interface TransactionTechnicalDetailsProps {
  transactionId: string;
}

export function TransactionTechnicalDetails({
  transactionId,
}: TransactionTechnicalDetailsProps) {
  const { state } = useCommerce();
  const transaction = state.transactions[transactionId];
  if (!transaction) return null;

  const audit = state.audit[transactionId] ?? [];
  const lastEvent = audit.at(-1);

  const rows: Array<[string, string]> = [
    ["Transaction ID", transaction.id],
    ["Proposal reference", transaction.proposalId],
    ["Correlation ID", lastEvent?.correlationId ?? "—"],
    ["Platform state", transaction.state],
    ["Provider reference", lastEvent?.providerReferenceRedacted ?? "Redacted"],
    ["Last updated", formatDateTime(transaction.updatedAt)],
  ];

  return (
    <div className="rounded-md border border-border bg-muted p-3">
      <dl className="flex flex-col gap-1.5 text-xs">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-start justify-between gap-4">
            <dt className="shrink-0 text-muted-foreground">{label}</dt>
            <dd className="break-all text-right font-mono tnum">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
