"use client";

import { useRouter } from "next/navigation";
import { ReceiptText, Download } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { formatRelativeTime } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MoneyText } from "@/components/shared/money";
import {
  AuthorizationStatusBadge,
  MerchantDecisionBadge,
  TransactionStatusBadge,
} from "@/components/shared/status-badge";
import { EmptyState } from "@/components/merchant/empty-state";
import { Button } from "@/components/ui/button";

function exportTransactionsCSV(
  transactions: any[],
  authorizations: any[],
  decisions: any[],
  productTitle: (id: string) => string
) {
  const headers = [
    "Transaction ID",
    "Product",
    "Amount (minor)",
    "Currency",
    "Buyer Auth Status",
    "Merchant Decision",
    "Transaction Status",
    "Updated At",
  ];

  const rows = transactions.map((txn) => {
    const auth = authorizations.find((a) => a.proposalId === txn.proposalId);
    const decision = decisions.find((d) => d.proposalId === txn.proposalId);

    return [
      txn.id,
      productTitle(txn.productId),
      txn.amount.amount_minor,
      txn.amount.currency,
      auth?.status || "—",
      decision?.decision || "—",
      txn.state,
      txn.updatedAt,
    ];
  });

  const csvContent = [
    headers.join(","),
    ...rows.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `transactions_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportTransactionsJSON(transactions: any[]) {
  const json = JSON.stringify(transactions, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `transactions_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function TransactionsPage() {
  const router = useRouter();
  const { state, actions } = useCommerce();

  const transactions = [...actions.listTransactions()].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  );

  const productTitle = (id: string) =>
    state.products.find((p) => p.id === id)?.title ?? "Unknown product";

  const authorizations = Object.values(state.authorizations);
  const decisions = Object.values(state.decisions);

  return (
    <>
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">Transactions</h2>
          <p className="text-sm text-muted-foreground">
            <span className="tnum">{transactions.length}</span> transactions.
            Buyer authorization and merchant decision are tracked independently.
          </p>
        </div>
        {transactions.length > 0 && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                exportTransactionsCSV(
                  transactions,
                  authorizations,
                  decisions,
                  productTitle
                )
              }
            >
              <Download className="h-4 w-4 mr-2" />
              CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportTransactionsJSON(transactions)}
            >
              <Download className="h-4 w-4 mr-2" />
              JSON
            </Button>
          </div>
        )}
      </div>

      {transactions.length === 0 ? (
        <EmptyState
          icon={ReceiptText}
          title="No transactions yet"
          description="Transactions appear here once an AI buyer creates a proposal for one of your published products."
        />
      ) : (
        <div className="overflow-x-auto rounded-md border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Transaction</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead className="hidden md:table-cell">Buyer Auth</TableHead>
                <TableHead className="hidden md:table-cell">
                  Merchant Decision
                </TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((txn) => {
                const authorization = authorizations.find(
                  (a) => a.proposalId === txn.proposalId
                );
                const decision = decisions.find(
                  (d) => d.proposalId === txn.proposalId
                );
                return (
                  <TableRow
                    key={txn.id}
                    tabIndex={0}
                    className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                    onClick={() =>
                      router.push(`/merchant/transactions/${txn.id}`)
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        router.push(`/merchant/transactions/${txn.id}`);
                      }
                    }}
                    aria-label={`View transaction ${txn.id}`}
                  >
                    <TableCell className="tnum font-mono text-xs">
                      {txn.id}
                    </TableCell>
                    <TableCell className="max-w-40 truncate">
                      {productTitle(txn.productId)}
                    </TableCell>
                    <TableCell>
                      <MoneyText money={txn.amount} />
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {authorization ? (
                        <AuthorizationStatusBadge
                          status={authorization.status}
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {decision ? (
                        <MerchantDecisionBadge
                          decision={decision.decision}
                          decidedBy={decision.decidedBy}
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <TransactionStatusBadge state={txn.state} />
                    </TableCell>
                    <TableCell className="tnum text-right text-xs text-muted-foreground">
                      {formatRelativeTime(txn.updatedAt)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  );
}
