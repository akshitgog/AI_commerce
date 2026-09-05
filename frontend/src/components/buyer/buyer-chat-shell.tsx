"use client";

import { useEffect, useRef, useState } from "react";
import { Store } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import type { Transaction } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { GateProgressView } from "@/components/shared/gate-progress";
import { AuditTimeline } from "@/components/shared/audit-timeline";
import { TransactionStatusBadge } from "@/components/shared/status-badge";

import { AssistantMessage } from "./assistant-message";
import { BuyerComposer } from "./buyer-composer";
import { BuyerMessage } from "./buyer-message";
import { CatalogSearchState } from "./catalog-search-state";
import { PaymentHandoffCard } from "./payment-handoff-card";
import { PaymentStatusCard } from "./payment-status-card";
import { ProductResultCard } from "./product-result-card";
import { ProposalCard } from "./proposal-card";

export type ChatItem =
  | { id: string; kind: "buyer-message"; text: string }
  | { id: string; kind: "assistant-message"; text: string }
  | { id: string; kind: "searching" }
  | { id: string; kind: "search-error"; query: string }
  | { id: string; kind: "product-result"; productId: string }
  | { id: string; kind: "proposal"; proposalId: string }
  | { id: string; kind: "payment-handoff"; proposalId: string }
  | { id: string; kind: "payment-status"; transactionId: string };

const SUGGESTED_PROMPT = "Find me a USB-C charger under ₹1,000.";

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `chat-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
export function BuyerChatShell() {
  const { state, actions } = useCommerce();

  const [items, setItems] = useState<ChatItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [lastProductId, setLastProductId] = useState<string | null>(null);
  const [activeProposalId, setActiveProposalId] = useState<string | null>(null);
  const [closed, setClosed] = useState<Record<string, "cancelled" | "expired">>({});
  const [refreshingIds, setRefreshingIds] = useState<Record<string, boolean>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeTransaction: Transaction | undefined = activeProposalId
    ? Object.values(state.transactions).find(
        (entry) => entry.proposalId === activeProposalId,
      )
    : undefined;

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [items.length, activeTransaction?.state]);

  const push = (item: ChatItem) => setItems((prev) => [...prev, item]);

  // Creates a purchase proposal only. This never authorizes or pays.
  const handleBuy = async (productId: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const proposal = await actions.createProposal({ productId, quantity: 1 });
      push({
        id: newId(),
        kind: "assistant-message",
        text: `I've prepared a purchase proposal from ${state.merchant.name}. Review it and approve below — nothing is paid without your approval.`,
      });
      push({ id: newId(), kind: "proposal", proposalId: proposal.id });
      setActiveProposalId(proposal.id);
      setLastProductId(productId);
    } catch {
      push({
        id: newId(),
        kind: "assistant-message",
        text: "I couldn't create a purchase proposal right now. Please try again.",
      });
    } finally {
      setBusy(false);
    }
  };

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || busy || !state.initialized) return;

    const searchId = newId();
    push({ id: newId(), kind: "buyer-message", text: trimmed });
    push({ id: searchId, kind: "searching" });
    setBusy(true);

    try {
      const history = [
        { role: "system", content: `You are assisting a customer shopping at merchant ID: ${state.merchant.id}. Always use this merchant_id for tool calls.` },
        ...items
          .filter((i) => i.kind === "buyer-message" || i.kind === "assistant-message")
          .map((i) => ({
            role: i.kind === "buyer-message" ? "user" : "assistant",
            content: i.text,
          }))
      ];
      history.push({ role: "user", content: trimmed });

      const response = await actions.chat(history);
      
      setItems((prev) => prev.filter((item) => item.id !== searchId));

      if (response.text) {
        push({ id: newId(), kind: "assistant-message", text: response.text });
      }

      const toolCalls = response.tool_calls || [];

      if (toolCalls.includes("search_catalog")) {
        const results = response.tool_results?.find((tr: any) => tr.tool === "search_catalog")?.result?.items || [];
        for (const product of results) {
          push({ id: newId(), kind: "product-result", productId: product.id });
        }
        if (results.length > 0) {
          setLastProductId(results[results.length - 1].id);
        }
      }

      if (toolCalls.includes("create_purchase_proposal")) {
        const proposal = response.tool_results?.find((tr: any) => tr.tool === "create_purchase_proposal")?.result;
        if (proposal) {
          push({ id: newId(), kind: "proposal", proposalId: proposal.id });
          setActiveProposalId(proposal.id);
          setLastProductId(proposal.product_id);
        }
      }

    } catch (error) {
      setItems((prev) =>
        prev.map((item) =>
          item.id === searchId
            ? { id: searchId, kind: "search-error", query: trimmed }
            : item,
        ),
      );
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async (proposalId: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await actions.cancelProposal(proposalId);
      setClosed((prev) => ({ ...prev, [proposalId]: "cancelled" }));
    } catch {
      push({
        id: newId(),
        kind: "assistant-message",
        text: "We couldn't cancel this proposal. Please try again.",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async (proposalId: string) => {
    if (busy) return;
    setBusy(true);
    try {
      await actions.requestAndApproveAuthorization(proposalId);
    } catch (error) {
      if ((error as any)?.code === "PROPOSAL_STALE" || (error instanceof Error && error.message === "PROPOSAL_EXPIRED")) {
        // Never silently reuse a stale proposal — surface the expired state.
        setClosed((prev) => ({ ...prev, [proposalId]: "expired" }));
      } else {
        push({
          id: newId(),
          kind: "assistant-message",
          text: "We couldn't record your approval. Nothing was authorized — please try again.",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const handleHandoff = (proposalId: string) => {
    setItems((prev) => {
      if (
        prev.some(
          (item) => item.kind === "payment-handoff" && item.proposalId === proposalId,
        )
      ) {
        return prev;
      }
      return [...prev, { id: newId(), kind: "payment-handoff", proposalId }];
    });
  };

  const handleExecute = async (proposalId: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const transaction = await actions.executeTransaction(proposalId);
      push({
        id: newId(),
        kind: "payment-status",
        transactionId: transaction.id,
      });
    } catch {
      push({
        id: newId(),
        kind: "assistant-message",
        text: "We couldn't start the payment. No payment was taken — please try again.",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleRefresh = async (transactionId: string) => {
    if (refreshingIds[transactionId]) return;
    setRefreshingIds((prev) => ({ ...prev, [transactionId]: true }));
    try {
      await actions.refreshTransaction(transactionId);
    } catch {
      // Recovery stays calm — the panel remains and can be refreshed again.
    } finally {
      setRefreshingIds((prev) => ({ ...prev, [transactionId]: false }));
    }
  };

  const renderItem = (item: ChatItem) => {
    switch (item.kind) {
      case "buyer-message":
        return <BuyerMessage key={item.id} text={item.text} />;
      case "assistant-message":
        return <AssistantMessage key={item.id} text={item.text} />;
      case "searching":
        return (
          <CatalogSearchState
            key={item.id}
            state="searching"
            merchantName={state.merchant.name}
          />
        );
      case "search-error":
        return (
          <CatalogSearchState
            key={item.id}
            state="error"
            merchantName={state.merchant.name}
            onRetry={() => void send(item.query)}
          />
        );
      case "product-result":
        return (
          <ProductResultCard
            key={item.id}
            productId={item.productId}
            busy={busy}
            onBuy={() => void handleBuy(item.productId)}
          />
        );
      case "proposal":
        return (
          <ProposalCard
            key={item.id}
            proposalId={item.proposalId}
            closed={closed[item.proposalId]}
            busy={busy}
            onCancel={() => void handleCancel(item.proposalId)}
            onApprove={() => void handleApprove(item.proposalId)}
            onCreateNew={(productId) => void handleBuy(productId)}
            onContinueToPayment={() => handleHandoff(item.proposalId)}
          />
        );
      case "payment-handoff":
        return (
          <PaymentHandoffCard
            key={item.id}
            proposalId={item.proposalId}
            busy={busy}
            onPay={() => void handleExecute(item.proposalId)}
          />
        );
      case "payment-status": {
        const events = state.audit[item.transactionId] ?? [];
        return (
          <div key={item.id} className="flex flex-col gap-3">
            <PaymentStatusCard
              transactionId={item.transactionId}
              refreshing={!!refreshingIds[item.transactionId]}
              onRefresh={() => void handleRefresh(item.transactionId)}
            />
            {events.length > 0 ? (
              <Card className="p-4">
                <h3 className="mb-3 text-sm font-semibold">
                  Transaction audit trail
                </h3>
                <AuditTimeline events={events} />
              </Card>
            ) : null}
          </div>
        );
      }
    }
  };

  const progressPanel = activeTransaction ? (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Purchase progress
        </p>
        <TransactionStatusBadge state={activeTransaction.state} />
      </div>
      <div className="mt-3">
        <GateProgressView state={activeTransaction.state} />
      </div>
    </>
  ) : null;

  return (
    <div className="flex h-full flex-col bg-background text-foreground">
      <header className="shrink-0 border-b border-border bg-card">
        <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4">
          <span className="text-sm font-semibold tracking-tight">
            AI Commerce Gateway
          </span>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium">
              <Store className="size-3.5" aria-hidden />
              {state.merchant.name}
            </span>
            <Badge variant="warning">Test Mode</Badge>
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div ref={scrollRef} className="min-w-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-2xl px-4 py-6">
            {items.length === 0 ? (
              <div className="flex flex-col items-start gap-3 py-10">
                <h1 className="text-xl font-semibold tracking-tight">
                  Shop with AI
                </h1>
                <p className="text-sm text-muted-foreground">
                  Tell me what you&apos;re looking for from{" "}
                  {state.merchant.name}.
                </p>
                <button
                  type="button"
                  onClick={() => send(SUGGESTED_PROMPT)}
                  className="rounded-full border border-border bg-card px-4 py-2 text-sm shadow-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  {SUGGESTED_PROMPT}
                </button>
              </div>
            ) : null}

            <div aria-live="polite" className="flex flex-col gap-4">
              {items.map(renderItem)}
            </div>

            {progressPanel ? (
              <Card className="mt-6 p-4 lg:hidden">{progressPanel}</Card>
            ) : null}
          </div>
        </div>

        {progressPanel ? (
          <aside
            className="hidden w-80 shrink-0 overflow-y-auto border-l border-border bg-card p-5 lg:block"
            aria-label="Purchase progress"
          >
            {progressPanel}
          </aside>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-border bg-card">
        <div className="mx-auto w-full max-w-2xl px-4 py-3">
          <p className="mb-2 text-center text-xs text-muted-foreground">
            AI proposes — you approve. Nothing is paid without your approval.
          </p>
          <BuyerComposer
            disabled={busy || !state.initialized}
            initialized={state.initialized}
            onSend={send}
          />
        </div>
      </div>
    </div>
  );
}
