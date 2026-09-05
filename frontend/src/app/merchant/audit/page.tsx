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
import { TransactionStatusBadge } from "@/components/shared/status-badge";

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
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportAuditJSON(events: any[], transactionId: string) {
  const json = JSON.stringify(events, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit_${transactionId}_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function AuditPage() {
  const { state, actions } = useCommerce();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const allTransactions = Object.values(state.transactions).sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  );

  const uniqueStatuses = Array.from(new Set(allTransactions.map(t => t.state)));

  const transactions = statusFilter === "ALL" 
    ? allTransactions 
    : allTransactions.filter(t => t.state === statusFilter);

  const currentId = selectedId ?? transactions[0]?.id ?? null;
  const events = currentId ? (state.audit[currentId] ?? []) : [];

  useEffect(() => {
    if (currentId && !state.audit[currentId]) {
      actions.loadAudit(currentId).catch(console.error);
    }
  }, [currentId, state.audit, actions]);

  // Reset selected events when the transaction ID changes
  useEffect(() => {
    setSelectedEventIds(new Set());
  }, [currentId]);

  const productTitle = (id: string) =>
    state.products.find((p) => p.id === id)?.title ?? id;

  const allSelected = events.length > 0 && selectedEventIds.size === events.length;
  const toggleAll = () => {
    if (allSelected) {
      setSelectedEventIds(new Set());
    } else {
      setSelectedEventIds(new Set(events.map((e: any, i: number) => e.id || String(i))));
    }
  };

  const toggleEvent = (eventId: string, checked: boolean) => {
    const next = new Set(selectedEventIds);
    if (checked) next.add(eventId);
    else next.delete(eventId);
    setSelectedEventIds(next);
  };

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
            <div className="flex flex-col sm:flex-row gap-4 max-w-2xl">
              <div className="flex-1 space-y-2">
                <Label htmlFor="audit-filter">Filter Status</Label>
                <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setSelectedId(null); }}>
                  <SelectTrigger id="audit-filter">
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Statuses</SelectItem>
                    {uniqueStatuses.map(s => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-[2] space-y-2">
                <Label htmlFor="audit-txn">Transaction</Label>
                <Select
                  value={currentId ?? undefined}
                  onValueChange={(v) => setSelectedId(v)}
                  disabled={transactions.length === 0}
                >
                  <SelectTrigger id="audit-txn" className="w-full">
                    <SelectValue placeholder={transactions.length > 0 ? "Select a transaction" : "No transactions match"} />
                  </SelectTrigger>
                  <SelectContent>
                    {transactions.map((txn) => (
                      <SelectItem key={txn.id} value={txn.id}>
                        <span className="tnum font-mono text-xs">{txn.id}</span>
                        {" — "}
                        {productTitle(txn.productId)}
                        <span className="ml-2 text-xs text-muted-foreground">({txn.state})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {currentId ? (
              events.length === 0 ? (
                <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                  No audit events recorded for this transaction.
                </p>
              ) : (
                <div className="space-y-6">
                  {/* Selectable Event List */}
                  <div className="space-y-4">
                    {/* Selection Toolbar */}
                    {selectedEventIds.size > 0 && (
                      <div className="flex items-center justify-between p-3 bg-muted rounded-md border">
                        <span className="text-sm font-medium">{selectedEventIds.size} selected</span>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => exportAuditCSV(events.filter((e: any, i: number) => selectedEventIds.has(e.id || String(i))), currentId)}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Selected CSV
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => exportAuditJSON(events.filter((e: any, i: number) => selectedEventIds.has(e.id || String(i))), currentId)}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Selected JSON
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Table-like List View */}
                    <div className="rounded-md border divide-y">
                      <div className="flex items-center p-3 bg-muted/30">
                        <input
                          type="checkbox"
                          checked={allSelected}
                          onChange={toggleAll}
                          className="mr-3 h-4 w-4 rounded border-gray-300"
                          aria-label="Select all events"
                        />
                        <span className="text-sm font-medium">Select All</span>
                      </div>
                      {events.map((e: any, i: number) => {
                        const eventId = e.id || String(i);
                        return (
                          <div key={eventId} className="flex items-center p-3 hover:bg-muted/10">
                            <input
                              type="checkbox"
                              checked={selectedEventIds.has(eventId)}
                              onChange={(ev) => toggleEvent(eventId, ev.target.checked)}
                              className="mr-3 h-4 w-4 rounded border-gray-300"
                              aria-label={`Select event`}
                            />
                            <div className="flex-1 flex gap-4 items-center text-sm">
                              <span className="font-mono text-xs text-muted-foreground">
                                {e.created_at || e.createdAt || "Unknown date"}
                              </span>
                              <span className="font-medium">{e.event_type || e.eventType || "Unknown event"}</span>
                              <span className="px-2 py-0.5 rounded-full bg-secondary text-xs">
                                {e.actor_type || e.actorType || "System"}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Existing Timeline */}
                  <AuditTimeline events={events} />
                </div>
              )
            ) : null}
          </CardContent>
        </Card>
      )}
    </>
  );
}
