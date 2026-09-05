"use client";

import { useState, useEffect } from "react";
import { ScrollText, Download } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AuditTimeline } from "@/components/shared/audit-timeline";
import { EmptyState } from "@/components/merchant/empty-state";
import { Button } from "@/components/ui/button";

function exportAuditCSV(events: any[], transactionId: string) {
  const headers = ["Timestamp", "Event Type", "Actor Type", "Actor ID", "Reason Code", "Previous State", "New State", "Correlation ID"];
  const rows = events.map((e) => [
    e.created_at || e.createdAt || "",
    e.event_type || e.eventType || "",
    e.actor_type || e.actorType || "",
    e.actor_id || e.actorId || "",
    e.reason_code || e.reasonCode || "",
    e.previous_state || e.previousState || "",
    e.new_state || e.newState || "",
    e.correlation_id || e.correlationId || "",
  ]);

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
  a.download = `audit_${transactionId}_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportAuditJSON(events: any[], transactionId: string) {
  const json = JSON.stringify(events, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit_${transactionId}_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AuditPage() {
  const { state, actions } = useCommerce();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const transactions = Object.values(state.transactions).sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  );

  const currentId = selectedId ?? transactions[0]?.id ?? null;
  const events = currentId ? (state.audit[currentId] ?? []) : [];

  useEffect(() => {
    if (currentId && !state.audit[currentId]) {
      actions.loadAudit(currentId).catch(console.error);
    }
  }, [currentId, state.audit, actions]);

  const productTitle = (id: string) =>
    state.products.find((p) => p.id === id)?.title ?? id;

  return (
    <>
      <div>
        <h2 className="text-lg font-semibold">Audit</h2>
        <p className="text-sm text-muted-foreground">
          A structured causal timeline per transaction — actor, action, reason,
          and state changes.
        </p>
      </div>

      {transactions.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="No audit history yet"
          description="Audit events are recorded once transactions exist. Each event keeps its correlation ID for support."
        />
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Transaction audit trail</CardTitle>
                <CardDescription>
                  Select a transaction to inspect its causal event history.
                </CardDescription>
              </div>
              {currentId && events.length > 0 && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportAuditCSV(events, currentId)}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    CSV
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportAuditJSON(events, currentId)}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    JSON
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-md space-y-2">
              <Label htmlFor="audit-txn">Transaction</Label>
              <Select
                value={currentId ?? undefined}
                onValueChange={(v) => setSelectedId(v)}
              >
                <SelectTrigger id="audit-txn" className="w-full">
                  <SelectValue placeholder="Select a transaction" />
                </SelectTrigger>
                <SelectContent>
                  {transactions.map((txn) => (
                    <SelectItem key={txn.id} value={txn.id}>
                      <span className="tnum font-mono text-xs">{txn.id}</span>
                      {" — "}
                      {productTitle(txn.productId)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {currentId ? (
              events.length === 0 ? (
                <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                  No audit events recorded for this transaction.
                </p>
              ) : (
                <AuditTimeline events={events} />
              )
            ) : null}
          </CardContent>
        </Card>
      )}
    </>
  );
}
