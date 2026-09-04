"use client";

import Link from "next/link";
import { Check, Inbox, Loader, Package, RefreshCw } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import type { Transaction } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MoneyText } from "@/components/shared/money";
import { TransactionStatusBadge } from "@/components/shared/status-badge";
import { cn } from "@/lib/utils";

const PROCESSING_STATES: Transaction["state"][] = [
  "EXECUTING",
  "PAYMENT_PENDING",
  "VERIFYING",
];
const RECOVERING_STATES: Transaction["state"][] = ["UNKNOWN", "RECONCILING"];

function MetricCard({
  href,
  label,
  value,
  hint,
  icon: Icon,
  recovery,
}: {
  href: string;
  label: string;
  value: number;
  hint: string;
  icon: typeof Package;
  recovery?: boolean;
}) {
  const active = recovery && value > 0;
  return (
    <Link
      href={href}
      className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      <Card
        className={cn(
          "h-full transition-colors hover:border-input",
          active && "border-recovery bg-recovery"
        )}
      >
        <CardContent className="flex items-start justify-between gap-2 p-4">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className="tnum text-2xl font-semibold">{value}</p>
            <p className="text-xs text-muted-foreground">{hint}</p>
          </div>
          <Icon
            className={cn(
              "size-4 shrink-0",
              active ? "text-recovery" : "text-muted-foreground"
            )}
            aria-hidden
          />
        </CardContent>
      </Card>
    </Link>
  );
}

export default function MerchantOverviewPage() {
  const { state, actions } = useCommerce();

  const publishedCount = state.products.filter(
    (p) => p.status === "PUBLISHED"
  ).length;
  const reviews = actions.listReviews();
  const transactions = actions.listTransactions();
  const processing = transactions.filter((t) =>
    PROCESSING_STATES.includes(t.state)
  );
  const recovering = transactions.filter((t) =>
    RECOVERING_STATES.includes(t.state)
  );
  const recent = [...transactions]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 5);

  const productTitle = (id: string) =>
    state.products.find((p) => p.id === id)?.title ?? "Unknown product";

  const needsAttention = reviews.length > 0 || recovering.length > 0;

  return (
    <>
      {/* Operations metrics */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          href="/merchant/products"
          label="Published Products"
          value={publishedCount}
          hint="Discoverable by AI buyers"
          icon={Package}
        />
        <MetricCard
          href="/merchant/review"
          label="Awaiting Review"
          value={reviews.length}
          hint="Proposals needing your decision"
          icon={Inbox}
        />
        <MetricCard
          href="/merchant/transactions"
          label="Processing"
          value={processing.length}
          hint="Payment in flight or verifying"
          icon={Loader}
        />
        <MetricCard
          href="/merchant/transactions"
          label="Recovering"
          value={recovering.length}
          hint="Provider result being confirmed"
          icon={RefreshCw}
          recovery
        />
      </div>

      {/* Needs attention */}
      <Card>
        <CardHeader>
          <CardTitle>Needs attention</CardTitle>
          <CardDescription>
            Merchant decisions and payment recovery that require follow-up.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!needsAttention ? (
            <div className="flex items-center gap-3 rounded-md border border-dashed px-4 py-6">
              <div className="flex size-8 items-center justify-center rounded-full bg-muted">
                <Check className="size-4 text-muted-foreground" aria-hidden />
              </div>
              <p className="text-sm text-muted-foreground">
                Nothing needs attention right now.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border" aria-live="polite">
              {reviews.map((item) => (
                <li
                  key={item.proposal.id}
                  className="flex flex-wrap items-center gap-3 py-3"
                >
                  <Badge variant="warning">
                    <Inbox aria-hidden />
                    Review
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {item.product.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Buyer <span className="tnum font-mono">{item.authorization.buyerId}</span>
                      {" · "}
                      {item.reviewReason}
                    </p>
                  </div>
                  <MoneyText money={item.proposal.total} />
                  <Button asChild size="sm" variant="outline">
                    <Link href="/merchant/review">Review</Link>
                  </Button>
                </li>
              ))}
              {recovering.map((txn) => (
                <li
                  key={txn.id}
                  className="flex flex-wrap items-center gap-3 py-3"
                >
                  <Badge variant="recovery">
                    <RefreshCw aria-hidden />
                    Recovering
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {productTitle(txn.productId)}
                    </p>
                    <p className="tnum font-mono text-xs text-muted-foreground">
                      {txn.id}
                    </p>
                  </div>
                  <MoneyText money={txn.amount} />
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/merchant/transactions/${txn.id}`}>View</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
          <CardDescription>Latest transactions across all states.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {recent.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-muted-foreground">
              No transactions yet. Transactions appear here once a buyer
              proposal is created.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Transaction</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent.map((txn) => (
                  <TableRow key={txn.id}>
                    <TableCell>
                      <Link
                        href={`/merchant/transactions/${txn.id}`}
                        className="tnum font-mono text-xs text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {txn.id}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-48 truncate">
                      {productTitle(txn.productId)}
                    </TableCell>
                    <TableCell>
                      <MoneyText money={txn.amount} />
                    </TableCell>
                    <TableCell>
                      <TransactionStatusBadge state={txn.state} />
                    </TableCell>
                    <TableCell className="tnum text-right text-xs text-muted-foreground">
                      {formatRelativeTime(txn.updatedAt)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
