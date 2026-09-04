"use client";

import { useState } from "react";
import { Check, Clock, Eye, Inbox, Package, X } from "lucide-react";

import { useCommerce, useNow } from "@/lib/services/provider";
import type { ReviewItem } from "@/lib/types";
import { formatCountdown } from "@/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { MoneyText } from "@/components/shared/money";
import { AuthorizationStatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/merchant/empty-state";
import { ConfirmDialog } from "@/components/merchant/confirm-dialog";
import { ProposalSummary } from "@/components/merchant/proposal-summary";

function ReviewCard({
  item,
  onApprove,
  onDeny,
  busy,
  onView,
}: {
  item: ReviewItem;
  onApprove: () => void;
  onDeny: (reason: string) => void;
  busy: "approve" | "deny" | null;
  onView: () => void;
}) {
  const now = useNow(1000);
  const [denyOpen, setDenyOpen] = useState(false);
  const [denyReason, setDenyReason] = useState("");

  const expired = new Date(item.proposal.expiresAt).getTime() <= now;
  const actionable = !expired && busy === null;

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-4 lg:flex-row lg:items-center">
        {/* Product */}
        <div className="flex min-w-0 items-center gap-3 lg:w-56">
          {item.product.images[0] ? (
            // eslint-disable-next-line @next/next/no-img-element -- prototype: merchant-provided URLs
            <img
              src={item.product.images[0].url}
              alt={item.product.images[0].alt}
              className="size-12 shrink-0 rounded-md border object-cover"
            />
          ) : (
            <div className="flex size-12 shrink-0 items-center justify-center rounded-md border bg-muted">
              <Package className="size-5 text-muted-foreground" aria-hidden />
            </div>
          )}
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{item.product.title}</p>
            <p className="tnum text-xs text-muted-foreground">
              Qty {item.proposal.quantity}
            </p>
          </div>
        </div>

        {/* Facts */}
        <div className="grid flex-1 grid-cols-2 gap-3 text-sm md:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Buyer reference</p>
            <p className="tnum truncate font-mono text-xs">
              {item.authorization.buyerId}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Proposal expires</p>
            {expired ? (
              <Badge variant="destructive" className="mt-0.5">
                Expired
              </Badge>
            ) : (
              <p className="tnum flex items-center gap-1 font-medium">
                <Clock className="size-3 text-muted-foreground" aria-hidden />
                {formatCountdown(item.proposal.expiresAt, now)}
              </p>
            )}
          </div>
          <div className="col-span-2 md:col-span-1">
            <p className="text-xs text-muted-foreground">Review reason</p>
            <p className="text-xs">{item.reviewReason}</p>
          </div>
        </div>

        {/* Trusted total + buyer authorization (separate from decision) */}
        <div className="flex items-center gap-4 lg:w-64 lg:justify-end">
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Trusted total</p>
            <MoneyText money={item.proposal.total} size="lg" />
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Buyer authorization</p>
            <AuthorizationStatusBadge status={item.authorization.status} />
          </div>
        </div>

        {/* Merchant decision controls — visually separated from buyer auth */}
        <div className="flex items-center gap-2 border-t pt-3 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
          <Button variant="ghost" size="sm" onClick={onView}>
            <Eye aria-hidden />
            View details
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!actionable}
            onClick={() => setDenyOpen(true)}
          >
            <X aria-hidden />
            {busy === "deny" ? "Denying…" : "Deny"}
          </Button>
          <Button
            size="sm"
            disabled={!actionable}
            onClick={onApprove}
          >
            <Check aria-hidden />
            {busy === "approve" ? "Approving…" : "Approve"}
          </Button>
        </div>
      </CardContent>

      <ConfirmDialog
        open={denyOpen}
        onOpenChange={setDenyOpen}
        title="Deny this purchase?"
        description="The buyer will be notified that the merchant did not accept this proposal."
        confirmLabel="Deny purchase"
        destructive
        busy={busy === "deny"}
        confirmDisabled={denyReason.trim() === ""}
        onConfirm={() => onDeny(denyReason.trim())}
      >
        <div className="space-y-2">
          <Label htmlFor={`deny-reason-${item.proposal.id}`}>
            Reason for denial
          </Label>
          <Textarea
            id={`deny-reason-${item.proposal.id}`}
            value={denyReason}
            onChange={(e) => setDenyReason(e.target.value)}
            placeholder="e.g. Out of stock, suspicious activity…"
            rows={3}
          />
        </div>
      </ConfirmDialog>
    </Card>
  );
}

export default function ReviewQueuePage() {
  const { actions } = useCommerce();
  const [busy, setBusy] = useState<Record<string, "approve" | "deny" | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [detail, setDetail] = useState<ReviewItem | null>(null);

  const reviews = actions.listReviews();

  function setItemBusy(id: string, value: "approve" | "deny" | null) {
    setBusy((b) => ({ ...b, [id]: value }));
  }

  async function handleApprove(item: ReviewItem) {
    setError(null);
    setItemBusy(item.proposal.id, "approve");
    try {
      await actions.approveReview(item.proposal.id);
      setAnnouncement(`Approved proposal for ${item.product.title}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed.");
    } finally {
      setItemBusy(item.proposal.id, null);
    }
  }

  async function handleDeny(item: ReviewItem, reason: string) {
    setError(null);
    setItemBusy(item.proposal.id, "deny");
    try {
      await actions.denyReview(item.proposal.id, reason);
      setAnnouncement(`Denied proposal for ${item.product.title}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deny failed.");
    } finally {
      setItemBusy(item.proposal.id, null);
    }
  }

  return (
    <>
      <div>
        <h2 className="text-lg font-semibold">Review Queue</h2>
        <p className="text-sm text-muted-foreground">
          Proposals the buyer authorized that still need your independent
          merchant decision.
        </p>
      </div>

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {error ? (
        <Alert variant="destructive" role="alert">
          <AlertTitle>Action failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {reviews.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No proposals awaiting review"
          description="When a buyer-authorized purchase needs your decision, it will appear here with the trusted total and expiry."
        />
      ) : (
        <div className="space-y-3">
          {reviews.map((item) => (
            <ReviewCard
              key={item.proposal.id}
              item={item}
              busy={busy[item.proposal.id] ?? null}
              onApprove={() => void handleApprove(item)}
              onDeny={(reason) => void handleDeny(item, reason)}
              onView={() => setDetail(item)}
            />
          ))}
        </div>
      )}

      <Dialog open={detail !== null} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Proposal details</DialogTitle>
          </DialogHeader>
          {detail ? (
            <div className="space-y-4">
              <ProposalSummary
                proposal={detail.proposal}
                product={detail.product}
              />
              <Separator />
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">
                    Buyer authorization
                  </p>
                  <AuthorizationStatusBadge
                    status={detail.authorization.status}
                  />
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    Buyer reference
                  </p>
                  <p className="tnum font-mono text-xs">
                    {detail.authorization.buyerId}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Buyer authorization is buyer consent only — approving or
                denying here is your independent merchant decision.
              </p>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
