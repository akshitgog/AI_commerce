// Canonical backend state -> human label mapping.
// Rules from UI_REFERENCE.md / shared specs:
// - UNKNOWN and RECONCILING present to users as "Recovering" (technical state
//   only visible in detail areas).
// - Buyer authorization and merchant acceptance are never collapsed.
// - Payment initiation is never presented as success.

import type {
  AuthorizationStatus,
  MerchantDecisionValue,
  TransactionState,
} from "./types";

export function humanTransactionLabel(state: TransactionState): string {
  switch (state) {
    case "PROPOSED":
      return "Awaiting buyer approval";
    case "BUYER_AUTH_REQUIRED":
      return "Awaiting buyer approval";
    case "MERCHANT_POLICY_PENDING":
      return "Awaiting merchant approval";
    case "MERCHANT_REVIEW_REQUIRED":
      return "Awaiting merchant approval";
    case "READY":
      return "Ready";
    case "EXECUTING":
      return "Processing payment";
    case "PAYMENT_PENDING":
      return "Payment pending";
    case "VERIFYING":
      return "Verifying";
    case "UNKNOWN":
      return "Recovering";
    case "RECONCILING":
      return "Recovering";
    case "SUCCEEDED":
      return "Succeeded";
    case "FAILED":
      return "Failed";
    case "CANCELLED":
      return "Cancelled";
    case "EXPIRED":
      return "Expired";
  }
}

export type StatusTone =
  | "neutral"
  | "attention" // pending action
  | "recovery" // distinct from failure
  | "success"
  | "destructive";

export function transactionTone(state: TransactionState): StatusTone {
  switch (state) {
    case "SUCCEEDED":
      return "success";
    case "FAILED":
    case "CANCELLED":
    case "EXPIRED":
      return "destructive";
    case "UNKNOWN":
    case "RECONCILING":
      return "recovery";
    case "READY":
      return "success";
    case "PROPOSED":
    case "BUYER_AUTH_REQUIRED":
    case "MERCHANT_POLICY_PENDING":
    case "MERCHANT_REVIEW_REQUIRED":
    case "EXECUTING":
    case "PAYMENT_PENDING":
    case "VERIFYING":
      return "attention";
  }
}

export function authorizationLabel(status: AuthorizationStatus): string {
  switch (status) {
    case "REQUESTED":
      return "Approval required";
    case "APPROVED":
      return "Approved by buyer";
    case "REVOKED":
      return "Rejected";
    case "EXPIRED":
      return "Expired";
  }
}

export function authorizationTone(status: AuthorizationStatus): StatusTone {
  switch (status) {
    case "APPROVED":
      return "success";
    case "REVOKED":
    case "EXPIRED":
      return "destructive";
    case "REQUESTED":
      return "attention";
  }
}

export function merchantDecisionLabel(
  decision: MerchantDecisionValue,
  decidedBy: "POLICY" | "MERCHANT_USER",
): string {
  switch (decision) {
    case "ALLOW":
      return decidedBy === "POLICY"
        ? "Automatically accepted"
        : "Approved by merchant";
    case "DENY":
      return "Not accepted";
    case "REVIEW_REQUIRED":
      return "Merchant review required";
  }
}

export function merchantDecisionTone(decision: MerchantDecisionValue): StatusTone {
  switch (decision) {
    case "ALLOW":
      return "success";
    case "DENY":
      return "destructive";
    case "REVIEW_REQUIRED":
      return "attention";
  }
}

// Six-stage gate progression. Never collapse buyer auth + merchant acceptance.
export type GateStage =
  | "PROPOSAL"
  | "BUYER_AUTHORIZATION"
  | "MERCHANT_ACCEPTANCE"
  | "PAYMENT"
  | "VERIFICATION"
  | "COMPLETE";

export type GateStageStatus = "done" | "current" | "pending" | "recovering" | "failed";

export function gateStageLabel(stage: GateStage): string {
  switch (stage) {
    case "PROPOSAL":
      return "Proposal created";
    case "BUYER_AUTHORIZATION":
      return "Buyer authorized";
    case "MERCHANT_ACCEPTANCE":
      return "Merchant accepted";
    case "PAYMENT":
      return "Payment";
    case "VERIFICATION":
      return "Verification";
    case "COMPLETE":
      return "Complete";
  }
}

export function gateProgress(state: TransactionState): Record<GateStage, GateStageStatus> {
  const order: TransactionState[] = [
    "PROPOSED",
    "BUYER_AUTH_REQUIRED",
    "MERCHANT_POLICY_PENDING",
    "MERCHANT_REVIEW_REQUIRED",
    "READY",
    "EXECUTING",
    "PAYMENT_PENDING",
    "VERIFYING",
    "SUCCEEDED",
  ];
  const idx = order.indexOf(state);

  const r: Record<GateStage, GateStageStatus> = {
    PROPOSAL: "pending",
    BUYER_AUTHORIZATION: "pending",
    MERCHANT_ACCEPTANCE: "pending",
    PAYMENT: "pending",
    VERIFICATION: "pending",
    COMPLETE: "pending",
  };

  if (state === "FAILED" || state === "CANCELLED" || state === "EXPIRED") {
    r.PROPOSAL = "done";
    r.BUYER_AUTHORIZATION = "done";
    r.MERCHANT_ACCEPTANCE = "done";
    r.PAYMENT = "failed";
    r.VERIFICATION = "pending";
    r.COMPLETE = "pending";
    return r;
  }
  if (state === "UNKNOWN" || state === "RECONCILING") {
    r.PROPOSAL = "done";
    r.BUYER_AUTHORIZATION = "done";
    r.MERCHANT_ACCEPTANCE = "done";
    r.PAYMENT = "done";
    r.VERIFICATION = "recovering";
    r.COMPLETE = "pending";
    return r;
  }
  if (idx === -1) return r;

  r.PROPOSAL = "done";
  r.BUYER_AUTHORIZATION = idx >= order.indexOf("READY") ? "done" : state === "BUYER_AUTH_REQUIRED" ? "current" : "done";
  r.MERCHANT_ACCEPTANCE =
    idx >= order.indexOf("READY")
      ? "done"
      : state === "MERCHANT_POLICY_PENDING" || state === "MERCHANT_REVIEW_REQUIRED"
        ? "current"
        : "pending";
  r.PAYMENT =
    state === "EXECUTING" || state === "PAYMENT_PENDING"
      ? "current"
      : idx > order.indexOf("PAYMENT_PENDING")
        ? "done"
        : "pending";
  r.VERIFICATION = state === "VERIFYING" ? "current" : state === "SUCCEEDED" ? "done" : "pending";
  r.COMPLETE = state === "SUCCEEDED" ? "done" : "pending";
  return r;
}
