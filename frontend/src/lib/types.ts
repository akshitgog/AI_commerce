// Shared domain types for the AI Commerce Gateway frontend.
// Mirrors the backend contracts (src/ai_commerce_gateway/contracts/models.py).
// Money is always integer minor units + explicit currency. The UI formats
// server-provided values; it never derives authoritative totals client-side.

export interface Money {
  amount_minor: number;
  currency: string; // ISO 4217, e.g. "INR"
}

export type ProductStatus = "DRAFT" | "PUBLISHED" | "UNPUBLISHED";

export interface ProductImage {
  id: string;
  url: string;
  alt: string;
  isPrimary: boolean;
  position: number;
}

export interface Product {
  id: string;
  merchantId: string;
  sku: string;
  title: string;
  description: string;
  category: string | null;
  price: Money;
  availableQuantity: number;
  status: ProductStatus;
  version: number;
  images: ProductImage[];
  updatedAt: string; // ISO datetime
}

export interface Merchant {
  id: string;
  name: string;
}

export type PolicyMode = "MANUAL_ALL" | "AUTO_BELOW_LIMIT" | "DENY_ALL";

export interface Policy {
  mode: PolicyMode;
  maxAmount: Money | null; // only for AUTO_BELOW_LIMIT
  version: number;
}

export type ProposalStatus = "PROPOSED" | "EXPIRED" | "CANCELLED";

export type NextRequiredGate =
  | "BUYER_AUTH_REQUIRED"
  | "MERCHANT_POLICY_PENDING"
  | "MERCHANT_REVIEW_REQUIRED"
  | "READY";

export interface Proposal {
  id: string;
  buyerId: string;
  merchantId: string;
  productId: string;
  productVersion: number;
  quantity: number;
  unitPrice: Money;
  total: Money; // trusted, backend-derived
  proposalHash: string;
  status: ProposalStatus;
  nextRequiredGate: NextRequiredGate;
  expiresAt: string; // ISO datetime
  createdAt: string;
}

export type AuthorizationStatus = "REQUESTED" | "APPROVED" | "REVOKED" | "EXPIRED";

export interface Authorization {
  id: string;
  buyerId: string;
  proposalId: string;
  proposalHash: string;
  maxQuantity: number;
  maxAmount: Money;
  authorizedBy: string | null;
  status: AuthorizationStatus;
  expiresAt: string;
  createdAt: string;
}

export type MerchantDecisionValue = "ALLOW" | "DENY" | "REVIEW_REQUIRED";

export interface MerchantDecision {
  id: string;
  proposalId: string;
  merchantId: string;
  policyVersion: number;
  decision: MerchantDecisionValue;
  reasonCode: string;
  decidedBy: "POLICY" | "MERCHANT_USER";
  createdAt: string;
}

export type TransactionState =
  | "PROPOSED"
  | "BUYER_AUTH_REQUIRED"
  | "MERCHANT_POLICY_PENDING"
  | "MERCHANT_REVIEW_REQUIRED"
  | "READY"
  | "EXECUTING"
  | "PAYMENT_PENDING"
  | "UNKNOWN"
  | "VERIFYING"
  | "RECONCILING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "EXPIRED";

export interface ProviderPhase {
  provider: "RAZORPAY";
  providerOrderId: string | null;
  orderState: string | null;
  paymentState: string | null;
  lastVerifiedAt: string | null;
}

export interface Transaction {
  id: string;
  proposalId: string;
  merchantId: string;
  buyerId: string;
  productId: string;
  amount: Money;
  state: TransactionState;
  providerPhase: ProviderPhase | null;
  createdAt: string;
  updatedAt: string;
}

export type ActorType = "PLATFORM" | "MERCHANT_USER" | "BUYER" | "SYSTEM";

export interface AuditEvent {
  id: string;
  transactionId: string;
  eventType: string;
  actorType: ActorType;
  actorId: string | null;
  reasonCode: string;
  previousState: TransactionState | null;
  newState: TransactionState | null;
  correlationId: string;
  providerReferenceRedacted: string | null;
  summary: string; // human-readable causal summary
  createdAt: string;
}

export interface ReviewItem {
  proposal: Proposal;
  authorization: Authorization;
  product: Product;
  reviewReason: string;
}
