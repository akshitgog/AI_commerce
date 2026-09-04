"use client";

// Status badges. Every status carries an icon AND text — color is never the
// only signal. Labels/tones come from the canonical helpers in @/lib/status.

import type { ReactNode } from "react";
import {
  Ban,
  CheckCircle2,
  Clock,
  EyeOff,
  FileEdit,
  Globe,
  Loader2,
  RefreshCw,
  TimerOff,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  authorizationLabel,
  authorizationTone,
  humanTransactionLabel,
  merchantDecisionLabel,
  merchantDecisionTone,
  transactionTone,
  type StatusTone,
} from "@/lib/status";
import type {
  AuthorizationStatus,
  MerchantDecisionValue,
  ProductStatus,
  TransactionState,
} from "@/lib/types";

type BadgeVariant =
  | "default"
  | "secondary"
  | "outline"
  | "success"
  | "warning"
  | "recovery"
  | "destructive";

const TONE_TO_VARIANT: Record<StatusTone, BadgeVariant> = {
  neutral: "secondary",
  attention: "warning",
  recovery: "recovery",
  success: "success",
  destructive: "destructive",
};

/** Generic badge that maps a semantic StatusTone to a Badge variant. */
export function StatusBadge({
  tone,
  children,
  className,
}: {
  tone: StatusTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Badge
      variant={TONE_TO_VARIANT[tone]}
      className={cn("inline-flex items-center gap-1", className)}
    >
      {children}
    </Badge>
  );
}

const TRANSACTION_ICONS: Record<string, { icon: LucideIcon; spin?: boolean; slow?: boolean }> = {
  awaiting: { icon: Clock },
  processing: { icon: Loader2, spin: true },
  recovering: { icon: RefreshCw, slow: true },
  success: { icon: CheckCircle2 },
  failed: { icon: XCircle },
  cancelled: { icon: Ban },
  expired: { icon: TimerOff },
};

function transactionGroup(state: TransactionState): keyof typeof TRANSACTION_ICONS {
  switch (state) {
    case "PROPOSED":
    case "BUYER_AUTH_REQUIRED":
    case "MERCHANT_POLICY_PENDING":
    case "MERCHANT_REVIEW_REQUIRED":
      return "awaiting";
    case "EXECUTING":
    case "PAYMENT_PENDING":
    case "VERIFYING":
      return "processing";
    case "UNKNOWN":
    case "RECONCILING":
      return "recovering";
    case "SUCCEEDED":
    case "READY":
      return "success";
    case "FAILED":
      return "failed";
    case "CANCELLED":
      return "cancelled";
    case "EXPIRED":
      return "expired";
  }
}

/** Transaction state badge with the canonical human label (UNKNOWN/RECONCILING render as "Recovering"). */
export function TransactionStatusBadge({
  state,
  className,
}: {
  state: TransactionState;
  className?: string;
}) {
  const { icon: Icon, spin, slow } = TRANSACTION_ICONS[transactionGroup(state)];
  return (
    <StatusBadge tone={transactionTone(state)} className={className}>
      <Icon
        className={cn(
          "size-3",
          spin && "animate-spin",
          slow && "animate-[spin_2.5s_linear_infinite]",
        )}
        aria-hidden
      />
      {humanTransactionLabel(state)}
    </StatusBadge>
  );
}

const PRODUCT_META: Record<
  ProductStatus,
  { icon: LucideIcon; label: string; variant: BadgeVariant }
> = {
  DRAFT: { icon: FileEdit, label: "Draft", variant: "outline" },
  PUBLISHED: { icon: Globe, label: "Published", variant: "success" },
  UNPUBLISHED: { icon: EyeOff, label: "Unpublished", variant: "secondary" },
};

/** Product publication status badge. */
export function ProductStatusBadge({
  status,
  className,
}: {
  status: ProductStatus;
  className?: string;
}) {
  const meta = PRODUCT_META[status];
  const Icon = meta.icon;
  return (
    <Badge
      variant={meta.variant}
      className={cn("inline-flex items-center gap-1", className)}
    >
      <Icon className="size-3" aria-hidden />
      {meta.label}
    </Badge>
  );
}

const AUTHORIZATION_ICONS: Record<AuthorizationStatus, LucideIcon> = {
  REQUESTED: Clock,
  APPROVED: CheckCircle2,
  REVOKED: XCircle,
  EXPIRED: TimerOff,
};

/** Buyer-authorization badge — always kept separate from merchant decisions. */
export function AuthorizationStatusBadge({
  status,
  className,
}: {
  status: AuthorizationStatus;
  className?: string;
}) {
  const Icon = AUTHORIZATION_ICONS[status];
  return (
    <StatusBadge tone={authorizationTone(status)} className={className}>
      <Icon className="size-3" aria-hidden />
      {authorizationLabel(status)}
    </StatusBadge>
  );
}

const DECISION_ICONS: Record<MerchantDecisionValue, LucideIcon> = {
  ALLOW: CheckCircle2,
  DENY: XCircle,
  REVIEW_REQUIRED: Clock,
};

/** Merchant-acceptance badge — a separate gate from buyer authorization. */
export function MerchantDecisionBadge({
  decision,
  decidedBy,
  className,
}: {
  decision: MerchantDecisionValue;
  decidedBy: "POLICY" | "MERCHANT_USER";
  className?: string;
}) {
  const Icon = DECISION_ICONS[decision];
  return (
    <StatusBadge tone={merchantDecisionTone(decision)} className={className}>
      <Icon className="size-3" aria-hidden />
      {merchantDecisionLabel(decision, decidedBy)}
    </StatusBadge>
  );
}
