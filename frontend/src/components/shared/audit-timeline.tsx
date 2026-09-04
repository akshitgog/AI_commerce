"use client";

// Causal audit timeline: actor, summary, reason, state change, time, plus an
// expandable "Technical details" section with correlation ID and the redacted
// (fictional) provider reference.

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatRelativeTime } from "@/lib/format";
import type { ActorType, AuditEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const ACTOR_META: Record<
  ActorType,
  { label: string; variant: "default" | "secondary" | "outline" }
> = {
  BUYER: { label: "Buyer", variant: "secondary" },
  MERCHANT_USER: { label: "Merchant", variant: "default" },
  PLATFORM: { label: "Platform", variant: "outline" },
  SYSTEM: { label: "Provider", variant: "outline" },
};

function AuditEventRow({ event, isLast }: { event: AuditEvent; isLast: boolean }) {
  const [open, setOpen] = useState(false);
  const actor = ACTOR_META[event.actorType];
  return (
    <li className="relative flex gap-3">
      {!isLast && (
        <span
          aria-hidden
          className="absolute left-[5px] top-4 h-[calc(100%-8px)] w-px bg-border"
        />
      )}
      <span
        aria-hidden
        className="relative z-10 mt-1.5 size-[11px] shrink-0 rounded-full border-2 border-border bg-white"
      />
      <div className={cn("min-w-0 flex-1 pb-5 text-sm", isLast && "pb-0")}>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={actor.variant} className="text-xs">
            {actor.label}
          </Badge>
          <span className="font-mono text-xs text-muted-foreground">
            {event.reasonCode}
          </span>
          <span className="tnum ml-auto text-xs text-muted-foreground">
            {formatRelativeTime(event.createdAt)}
          </span>
        </div>
        <p className="mt-1.5">{event.summary}</p>
        {event.previousState !== null && event.newState !== null && (
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {event.previousState} → {event.newState}
          </p>
        )}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-1.5 inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight
            className={cn(
              "size-3 transition-transform",
              open && "rotate-90",
            )}
            aria-hidden
          />
          Technical details
        </button>
        {open && (
          <dl className="mt-2 space-y-1 rounded-md border border-border bg-muted/40 p-3 font-mono text-xs text-muted-foreground">
            <div className="flex gap-2">
              <dt className="w-28 shrink-0">eventType</dt>
              <dd className="break-all">{event.eventType}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-28 shrink-0">correlationId</dt>
              <dd className="break-all">{event.correlationId}</dd>
            </div>
            {event.providerReferenceRedacted && (
              <div className="flex gap-2">
                <dt className="w-28 shrink-0">providerRef</dt>
                <dd className="break-all">
                  {event.providerReferenceRedacted}
                  <span className="mt-0.5 block font-sans text-[11px] italic">
                    Fictional demo reference — not real Razorpay evidence.
                  </span>
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
    </li>
  );
}

/** Vertical causal audit timeline for a transaction, oldest first. */
export function AuditTimeline({
  events,
  className,
}: {
  events: AuditEvent[];
  className?: string;
}) {
  if (events.length === 0) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        No audit events yet.
      </p>
    );
  }
  return (
    <ol className={cn("text-sm", className)} aria-label="Audit timeline">
      {events.map((event, index) => (
        <AuditEventRow
          key={event.id}
          event={event}
          isLast={index === events.length - 1}
        />
      ))}
    </ol>
  );
}
