// Framework-free mock "trusted backend" for the AI Commerce Gateway prototype.
// In-memory state + subscribe/notify + simulated latency on every async action.
//
// Trust rules encoded here:
// - Money is integer minor units; totals are derived backend-side (here) from
//   the current catalog snapshot, never by the UI.
// - Buyer authorization and merchant acceptance are SEPARATE gates.
// - Provider-order creation is initiation, never success.
// - UNKNOWN/RECONCILING ("Recovering") is a first-class active state, never
//   presented as failure, and never offers "Pay again".

import type {
  ActorType,
  AuditEvent,
  Authorization,
  Merchant,
  MerchantDecision,
  Money,
  Policy,
  PolicyMode,
  Product,
  ProductImage,
  Proposal,
  ReviewItem,
  Transaction,
  TransactionState,
} from "../types";
import { formatMoney } from "../format";
import {
  DEMO_BUYER_ID,
  DEMO_BUYER_NAME,
  initialCatalog,
  initialMerchant,
  initialPolicy,
} from "../mock/fixtures";

export type DemoOutcome =
  | "auto_success"
  | "manual_review"
  | "recovery_success"
  | "payment_failed";

export interface CommerceState {
  merchant: Merchant;
  buyerName: string;
  products: Product[];
  policy: Policy;
  proposals: Record<string, Proposal>;
  authorizations: Record<string, Authorization>;
  decisions: Record<string, MerchantDecision>; // keyed by proposalId
  transactions: Record<string, Transaction>;
  audit: Record<string, AuditEvent[]>; // keyed by transactionId
  demoOutcome: DemoOutcome;
  /**
   * Presentation-only signal for the buyer chat auto-play demo. Incremented by
   * playDemo(); the buyer shell watches it and simulates the buyer's clicks.
   * Never used by any commerce logic.
   */
  autoPlaySignal: number;
}

export interface CreateProductInput {
  sku: string;
  title: string;
  description: string;
  category: string | null;
  price: Money;
  availableQuantity: number;
}

export interface UpdateProductInput extends Partial<CreateProductInput> {
  version: number;
}

export interface CommerceActions {
  /** Buyer-visible catalog search; PUBLISHED products only. */
  searchCatalog(input: {
    query?: string;
    category?: string;
    maxPriceMinor?: number;
  }): Promise<Product[]>;
  /** Fetch a single product by id. */
  getProduct(productId: string): Promise<Product | undefined>;
  /** Create a new DRAFT product at version 1. */
  createProduct(input: CreateProductInput): Promise<Product>;
  /** Version-checked update; throws Error("VERSION_CONFLICT") on stale version. */
  updateProduct(productId: string, input: UpdateProductInput): Promise<Product>;
  /** Publish a product; throws Error("NOT_READY:<fields>") listing missing fields. */
  publishProduct(productId: string): Promise<Product>;
  /** Move a PUBLISHED product to UNPUBLISHED (no longer buyer-discoverable). */
  unpublishProduct(productId: string): Promise<Product>;
  /** Delete a DRAFT product; throws Error("NOT_DRAFT") otherwise. */
  deleteDraft(productId: string): Promise<void>;
  /** Attach an image (max 3 per product). */
  addProductImage(
    productId: string,
    image: { url: string; alt: string },
  ): Promise<Product>;
  /** Remove an image; remaining images are re-positioned, first is primary. */
  removeProductImage(productId: string, imageId: string): Promise<Product>;
  /** Reorder images by id; first entry becomes the primary image. */
  reorderProductImages(productId: string, imageIds: string[]): Promise<Product>;
  /** AI description suggestion; descriptive only — never mutates price/stock/status. */
  suggestDescription(productId: string): Promise<string>;
  /** Save merchant acceptance policy; bumps policy version. */
  updatePolicy(input: { mode: PolicyMode; maxAmount?: Money }): Promise<Policy>;
  /** Create an expiring proposal snapshot plus its linked transaction. */
  createProposal(input: {
    productId: string;
    quantity: number;
  }): Promise<Proposal>;
  /** Buyer approves the exact proposal, then merchant policy is evaluated. */
  requestAndApproveAuthorization(proposalId: string): Promise<Authorization>;
  /** Buyer cancels an active proposal; linked transaction is cancelled. */
  cancelProposal(proposalId: string): Promise<void>;
  /** Proposals awaiting manual merchant review. */
  listReviews(): ReviewItem[];
  /** Merchant approves a review item; transaction becomes READY. */
  approveReview(proposalId: string): Promise<void>;
  /** Merchant denies a review item with a reason; transaction is cancelled. */
  denyReview(proposalId: string, reason: string): Promise<void>;
  /** Execute a READY transaction; starts the async payment simulation. */
  executeTransaction(proposalId: string): Promise<Transaction>;
  /** Manual status check during Recovering; accelerates reconciliation. */
  refreshTransaction(transactionId: string): Promise<Transaction>;
  /** Current snapshot of a transaction (no latency). */
  getTransaction(id: string): Transaction | undefined;
  /** All transactions, newest first (no latency). */
  listTransactions(): Transaction[];
  /** Causal audit timeline for a transaction, oldest first (no latency). */
  getAudit(transactionId: string): AuditEvent[];
  /** Select the simulated backend outcome for the next execution. */
  setDemoOutcome(o: DemoOutcome): void;
  /** Signal the buyer chat to auto-play the full demo journey (presentation only). */
  playDemo(): void;
  /** Reset all state back to the initial demo fixtures. */
  demoReset(): void;
}

const PROPOSAL_TTL_MS = 10 * 60 * 1000; // 10-minute proposal expiry
const MAX_IMAGES = 3;

function nowIso(): string {
  return new Date().toISOString();
}

/** Simulated backend latency: 350–700ms. */
function latency(): Promise<void> {
  return new Promise((resolve) =>
    setTimeout(resolve, 350 + Math.random() * 350),
  );
}

/** Simulated provider/verification step delay: 1.2–2s. */
function stepDelay(): number {
  return 1200 + Math.random() * 800;
}

function randomHex(len: number): string {
  let s = "";
  for (let i = 0; i < len; i++) {
    s += "0123456789abcdef"[Math.floor(Math.random() * 16)];
  }
  return s;
}

function id(prefix: string): string {
  return `${prefix}_${randomHex(12)}`;
}

/** Clearly fictional redacted provider reference, e.g. "rzp_order_••••3F2A". */
function redactedProviderRef(): string {
  return `rzp_order_••••${randomHex(4).toUpperCase()}`;
}

interface PaymentStep {
  run: () => void;
}

/** Create the in-memory mock commerce store (simulated trusted backend). */
export function createCommerceStore(): {
  getState(): CommerceState;
  subscribe(cb: () => void): () => void;
  actions: CommerceActions;
} {
  function buildInitialState(): CommerceState {
    return {
      merchant: initialMerchant(),
      buyerName: DEMO_BUYER_NAME,
      products: initialCatalog(),
      policy: initialPolicy(),
      proposals: {},
      authorizations: {},
      decisions: {},
      transactions: {},
      audit: {},
      demoOutcome: "auto_success",
      autoPlaySignal: autoPlayNonce,
    };
  }

  // Monotonic nonce so repeated play/reset cycles always produce a new signal.
  let autoPlayNonce = 0;

  let state: CommerceState = buildInitialState();
  const listeners = new Set<() => void>();

  // Payment simulation bookkeeping (not part of renderable state).
  const stepQueues = new Map<string, PaymentStep[]>();
  const timers = new Map<string, ReturnType<typeof setTimeout>>();

  function commit(): void {
    // Replace the top-level reference so useSyncExternalStore re-renders.
    state = { ...state };
    listeners.forEach((cb) => cb());
  }

  function appendAudit(
    transactionId: string,
    event: Omit<AuditEvent, "id" | "transactionId" | "createdAt">,
  ): void {
    const list = state.audit[transactionId] ?? [];
    list.push({
      id: id("evt"),
      transactionId,
      createdAt: nowIso(),
      ...event,
    });
    state.audit[transactionId] = list;
  }

  function transitionTransaction(
    txn: Transaction,
    newState: TransactionState,
    audit: {
      eventType: string;
      actorType: ActorType;
      actorId?: string | null;
      reasonCode: string;
      summary: string;
      providerReferenceRedacted?: string | null;
      providerPhase?: Transaction["providerPhase"];
    },
  ): void {
    const previousState = txn.state;
    txn.state = newState;
    txn.updatedAt = nowIso();
    if (audit.providerPhase !== undefined) {
      txn.providerPhase = audit.providerPhase;
    }
    appendAudit(txn.id, {
      eventType: audit.eventType,
      actorType: audit.actorType,
      actorId: audit.actorId ?? null,
      reasonCode: audit.reasonCode,
      previousState,
      newState,
      correlationId: `cor_${randomHex(12)}`,
      providerReferenceRedacted: audit.providerReferenceRedacted ?? null,
      summary: audit.summary,
    });
    commit();
  }

  function requireProduct(productId: string): Product {
    const product = state.products.find((p) => p.id === productId);
    if (!product) throw new Error("PRODUCT_NOT_FOUND");
    return product;
  }

  function requireProposal(proposalId: string): Proposal {
    const proposal = state.proposals[proposalId];
    if (!proposal) throw new Error("PROPOSAL_NOT_FOUND");
    return proposal;
  }

  function requireTransaction(transactionId: string): Transaction {
    const txn = state.transactions[transactionId];
    if (!txn) throw new Error("TRANSACTION_NOT_FOUND");
    return txn;
  }

  function transactionForProposal(proposalId: string): Transaction {
    const txn = Object.values(state.transactions).find(
      (t) => t.proposalId === proposalId,
    );
    if (!txn) throw new Error("TRANSACTION_NOT_FOUND");
    return txn;
  }

  function normalizeImagePositions(product: Product): void {
    product.images.forEach((img, index) => {
      img.position = index;
      img.isPrimary = index === 0;
    });
  }

  // ---------------------------------------------------------------------------
  // Payment simulation
  // ---------------------------------------------------------------------------

  function scheduleNextStep(transactionId: string, delayMs: number): void {
    const timer = setTimeout(() => {
      timers.delete(transactionId);
      const queue = stepQueues.get(transactionId);
      if (!queue || queue.length === 0) return;
      const step = queue.shift();
      if (!step) return;
      step.run();
      if (queue.length > 0) scheduleNextStep(transactionId, stepDelay());
    }, delayMs);
    timers.set(transactionId, timer);
  }

  /** Build the ordered provider/verification steps for the configured outcome. */
  function buildPaymentSteps(txnId: string, outcome: DemoOutcome): PaymentStep[] {
    const providerRef = redactedProviderRef();

    const markSucceeded = (): PaymentStep => ({
      run: () => {
        const txn = state.transactions[txnId];
        if (!txn) return;
        transitionTransaction(txn, "SUCCEEDED", {
          eventType: "PAYMENT_CAPTURED",
          actorType: "PLATFORM",
          reasonCode: "PAYMENT_CAPTURED",
          summary: "Provider confirmed payment captured",
          providerReferenceRedacted: providerRef,
          providerPhase: {
            provider: "RAZORPAY",
            orderState: "created",
            paymentState: "captured",
            lastVerifiedAt: nowIso(),
          },
        });
      },
    });

    const verifyThenSucceed: PaymentStep[] = [
      {
        run: () => {
          const txn = state.transactions[txnId];
          if (!txn) return;
          transitionTransaction(txn, "VERIFYING", {
            eventType: "VERIFICATION_STARTED",
            actorType: "PLATFORM",
            reasonCode: "VERIFICATION_STARTED",
            summary: "Verifying payment result with provider",
            providerReferenceRedacted: providerRef,
          });
        },
      },
      markSucceeded(),
    ];

    const branches: Record<DemoOutcome, PaymentStep[]> = {
      auto_success: verifyThenSucceed,
      manual_review: verifyThenSucceed,
      payment_failed: [
        {
          run: () => {
            const txn = state.transactions[txnId];
            if (!txn) return;
            transitionTransaction(txn, "VERIFYING", {
              eventType: "VERIFICATION_STARTED",
              actorType: "PLATFORM",
              reasonCode: "VERIFICATION_STARTED",
              summary: "Verifying payment result with provider",
              providerReferenceRedacted: providerRef,
            });
          },
        },
        {
          run: () => {
            const txn = state.transactions[txnId];
            if (!txn) return;
            transitionTransaction(txn, "FAILED", {
              eventType: "PAYMENT_FAILED",
              actorType: "PLATFORM",
              reasonCode: "PAYMENT_FAILED",
              summary: "Provider confirmed payment failed",
              providerReferenceRedacted: providerRef,
              providerPhase: {
                provider: "RAZORPAY",
                orderState: "created",
                paymentState: "failed",
                lastVerifiedAt: nowIso(),
              },
            });
          },
        },
      ],
      recovery_success: [
        {
          run: () => {
            const txn = state.transactions[txnId];
            if (!txn) return;
            transitionTransaction(txn, "UNKNOWN", {
              eventType: "PROVIDER_RESPONSE_UNCERTAIN",
              actorType: "SYSTEM",
              reasonCode: "PROVIDER_RESPONSE_UNCERTAIN",
              summary: "Provider response uncertain — reconciliation started",
              providerReferenceRedacted: providerRef,
            });
          },
        },
        {
          run: () => {
            const txn = state.transactions[txnId];
            if (!txn) return;
            transitionTransaction(txn, "RECONCILING", {
              eventType: "RECONCILIATION_STARTED",
              actorType: "SYSTEM",
              reasonCode: "RECONCILIATION_STARTED",
              summary:
                "Checking the provider for the authoritative payment result",
              providerReferenceRedacted: providerRef,
            });
          },
        },
        {
          run: () => {
            const txn = state.transactions[txnId];
            if (!txn) return;
            transitionTransaction(txn, "VERIFYING", {
              eventType: "VERIFICATION_STARTED",
              actorType: "PLATFORM",
              reasonCode: "VERIFICATION_STARTED",
              summary: "Provider responded — verifying captured payment",
              providerReferenceRedacted: providerRef,
            });
          },
        },
        markSucceeded(),
      ],
    };

    return [
      {
        run: () => {
          const txn = state.transactions[txnId];
          if (!txn) return;
          // Provider order creation is initiation, never success.
          transitionTransaction(txn, "PAYMENT_PENDING", {
            eventType: "PROVIDER_ORDER_CREATED",
            actorType: "SYSTEM",
            reasonCode: "PROVIDER_ORDER_CREATED",
            summary:
              "Provider order created — payment initiated, awaiting provider result",
            providerReferenceRedacted: providerRef,
            providerPhase: {
              provider: "RAZORPAY",
              orderState: "created",
              paymentState: null,
              lastVerifiedAt: null,
            },
          });
        },
      },
      ...branches[outcome],
    ];
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const actions: CommerceActions = {
    async searchCatalog(input) {
      await latency();
      const query = input.query?.trim().toLowerCase() ?? "";
      const category = input.category?.trim().toLowerCase() ?? "";
      return state.products.filter((p) => {
        if (p.status !== "PUBLISHED") return false; // drafts never discoverable
        if (category && (p.category ?? "").toLowerCase() !== category) {
          return false;
        }
        if (
          input.maxPriceMinor !== undefined &&
          p.price.amount_minor > input.maxPriceMinor
        ) {
          return false;
        }
        if (query) {
          const haystack = [p.title, p.description, p.category ?? ""]
            .join(" ")
            .toLowerCase();
          if (!haystack.includes(query)) return false;
        }
        return true;
      });
    },

    async getProduct(productId) {
      await latency();
      return state.products.find((p) => p.id === productId);
    },

    async createProduct(input) {
      await latency();
      const product: Product = {
        id: id("prod"),
        merchantId: state.merchant.id,
        sku: input.sku,
        title: input.title,
        description: input.description,
        category: input.category,
        price: input.price,
        availableQuantity: input.availableQuantity,
        status: "DRAFT",
        version: 1,
        images: [],
        updatedAt: nowIso(),
      };
      state.products.push(product);
      commit();
      return product;
    },

    async updateProduct(productId, input) {
      await latency();
      const product = requireProduct(productId);
      if (input.version !== product.version) {
        throw new Error("VERSION_CONFLICT");
      }
      const fields = Object.fromEntries(
        Object.entries(input).filter(([key]) => key !== "version"),
      );
      Object.assign(product, fields);
      product.version += 1;
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async publishProduct(productId) {
      await latency();
      const product = requireProduct(productId);
      const missing: string[] = [];
      if (!product.title.trim()) missing.push("title");
      if (product.price.amount_minor <= 0) missing.push("price");
      if (product.availableQuantity < 0) missing.push("stock");
      if (product.images.length < 1) missing.push("image");
      if (missing.length > 0) {
        throw new Error(`NOT_READY:${missing.join(",")}`);
      }
      product.status = "PUBLISHED";
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async unpublishProduct(productId) {
      await latency();
      const product = requireProduct(productId);
      product.status = "UNPUBLISHED";
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async deleteDraft(productId) {
      await latency();
      const product = requireProduct(productId);
      if (product.status !== "DRAFT") throw new Error("NOT_DRAFT");
      state.products = state.products.filter((p) => p.id !== productId);
      commit();
    },

    async addProductImage(productId, image) {
      await latency();
      const product = requireProduct(productId);
      if (product.images.length >= MAX_IMAGES) throw new Error("MAX_IMAGES");
      const entry: ProductImage = {
        id: id("img"),
        url: image.url,
        alt: image.alt,
        isPrimary: product.images.length === 0,
        position: product.images.length,
      };
      product.images.push(entry);
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async removeProductImage(productId, imageId) {
      await latency();
      const product = requireProduct(productId);
      product.images = product.images.filter((img) => img.id !== imageId);
      normalizeImagePositions(product);
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async reorderProductImages(productId, imageIds) {
      await latency();
      const product = requireProduct(productId);
      const byId = new Map(product.images.map((img) => [img.id, img]));
      const reordered: ProductImage[] = [];
      imageIds.forEach((imageId) => {
        const img = byId.get(imageId);
        if (img) {
          reordered.push(img);
          byId.delete(imageId);
        }
      });
      byId.forEach((img) => reordered.push(img)); // keep any unmentioned images
      product.images = reordered;
      normalizeImagePositions(product);
      product.updatedAt = nowIso();
      commit();
      return product;
    },

    async suggestDescription(productId) {
      await latency();
      const product = requireProduct(productId);
      // Descriptive metadata only — price, stock and status are never touched.
      const categoryNote = product.category
        ? ` A dependable addition to our ${product.category.toLowerCase()} range.`
        : "";
      return (
        `${product.title} — built for everyday use with quality materials and ` +
        `reliable performance.${categoryNote} ` +
        `(AI suggestion, descriptive only; price and availability unchanged.)`
      );
    },

    async updatePolicy(input) {
      await latency();
      const maxAmount =
        input.mode === "AUTO_BELOW_LIMIT"
          ? (input.maxAmount ?? state.policy.maxAmount)
          : null;
      if (input.mode === "AUTO_BELOW_LIMIT" && !maxAmount) {
        throw new Error("POLICY_LIMIT_REQUIRED");
      }
      state.policy = {
        mode: input.mode,
        maxAmount,
        version: state.policy.version + 1,
      };
      commit();
      return state.policy;
    },

    async createProposal(input) {
      await latency();
      const product = requireProduct(input.productId);
      if (product.status !== "PUBLISHED") throw new Error("PRODUCT_UNAVAILABLE");
      if (!Number.isInteger(input.quantity) || input.quantity <= 0) {
        throw new Error("INVALID_QUANTITY");
      }
      if (input.quantity > product.availableQuantity) {
        throw new Error("INSUFFICIENT_STOCK");
      }

      const created = nowIso();
      // Trusted totals are derived here (this mock plays the backend role).
      const total: Money = {
        amount_minor: product.price.amount_minor * input.quantity,
        currency: product.price.currency,
      };
      const proposal: Proposal = {
        id: id("prop"),
        buyerId: DEMO_BUYER_ID,
        merchantId: state.merchant.id,
        productId: product.id,
        productVersion: product.version,
        quantity: input.quantity,
        unitPrice: { ...product.price },
        total,
        proposalHash: randomHex(64),
        status: "PROPOSED",
        nextRequiredGate: "BUYER_AUTH_REQUIRED",
        expiresAt: new Date(Date.now() + PROPOSAL_TTL_MS).toISOString(),
        createdAt: created,
      };
      state.proposals[proposal.id] = proposal;

      const txn: Transaction = {
        id: id("txn"),
        proposalId: proposal.id,
        merchantId: state.merchant.id,
        buyerId: DEMO_BUYER_ID,
        productId: product.id,
        amount: { ...total },
        state: "BUYER_AUTH_REQUIRED",
        providerPhase: null,
        createdAt: created,
        updatedAt: created,
      };
      state.transactions[txn.id] = txn;
      appendAudit(txn.id, {
        eventType: "PROPOSAL_CREATED",
        actorType: "BUYER",
        actorId: DEMO_BUYER_ID,
        reasonCode: "PROPOSAL_CREATED",
        previousState: "PROPOSED",
        newState: "BUYER_AUTH_REQUIRED",
        correlationId: `cor_${randomHex(12)}`,
        providerReferenceRedacted: null,
        summary: `Proposal created for ${product.title} × ${input.quantity} — total ${formatMoney(total)}`,
      });
      commit();
      return proposal;
    },

    async requestAndApproveAuthorization(proposalId) {
      await latency();
      const proposal = requireProposal(proposalId);
      const txn = transactionForProposal(proposalId);

      // Idempotent: an existing approved authorization is returned as-is.
      const existing = Object.values(state.authorizations).find(
        (a) => a.proposalId === proposalId && a.status === "APPROVED",
      );
      if (existing) return existing;

      if (proposal.status === "CANCELLED") throw new Error("PROPOSAL_CANCELLED");
      const expired =
        proposal.status === "EXPIRED" ||
        new Date(proposal.expiresAt).getTime() <= Date.now();
      if (expired) {
        proposal.status = "EXPIRED";
        proposal.nextRequiredGate = "BUYER_AUTH_REQUIRED";
        transitionTransaction(txn, "EXPIRED", {
          eventType: "PROPOSAL_EXPIRED",
          actorType: "PLATFORM",
          reasonCode: "PROPOSAL_EXPIRED",
          summary: "Proposal expired before buyer authorization",
        });
        throw new Error("PROPOSAL_EXPIRED");
      }

      // Gate 1: buyer authorization binds the buyer to this exact proposal.
      const authorization: Authorization = {
        id: id("auth"),
        buyerId: DEMO_BUYER_ID,
        proposalId: proposal.id,
        proposalHash: proposal.proposalHash,
        maxQuantity: proposal.quantity,
        maxAmount: { ...proposal.total },
        authorizedBy: state.buyerName,
        status: "APPROVED",
        expiresAt: proposal.expiresAt,
        createdAt: nowIso(),
      };
      state.authorizations[authorization.id] = authorization;
      transitionTransaction(txn, "MERCHANT_POLICY_PENDING", {
        eventType: "BUYER_AUTHORIZED",
        actorType: "BUYER",
        actorId: DEMO_BUYER_ID,
        reasonCode: "BUYER_AUTHORIZED",
        summary: `Buyer authorized proposal for ${formatMoney(proposal.total)}`,
      });

      // Gate 2: merchant acceptance via policy — a separate decision record.
      const policy = state.policy;
      const recordDecision = (
        decision: MerchantDecision,
        next: TransactionState,
        summary: string,
      ): void => {
        state.decisions[proposal.id] = decision;
        transitionTransaction(txn, next, {
          eventType: "MERCHANT_DECISION",
          actorType: "PLATFORM",
          reasonCode: decision.reasonCode,
          summary,
        });
      };

      const baseDecision = {
        id: id("dec"),
        proposalId: proposal.id,
        merchantId: state.merchant.id,
        policyVersion: policy.version,
        decidedBy: "POLICY" as const,
        createdAt: nowIso(),
      };

      if (policy.mode === "DENY_ALL") {
        recordDecision(
          { ...baseDecision, decision: "DENY", reasonCode: "POLICY_DENY_ALL" },
          "CANCELLED",
          "Merchant policy DENY_ALL rejected the proposal",
        );
      } else if (policy.mode === "MANUAL_ALL") {
        recordDecision(
          {
            ...baseDecision,
            decision: "REVIEW_REQUIRED",
            reasonCode: "POLICY_MANUAL_ALL",
          },
          "MERCHANT_REVIEW_REQUIRED",
          "Merchant policy requires manual review for every proposal",
        );
      } else {
        const limit = policy.maxAmount;
        const within =
          limit !== null && proposal.total.amount_minor <= limit.amount_minor;
        if (within && limit) {
          recordDecision(
            {
              ...baseDecision,
              decision: "ALLOW",
              reasonCode: "POLICY_AUTO_ACCEPT",
            },
            "READY",
            `Merchant policy AUTO_BELOW_LIMIT automatically accepted ${formatMoney(proposal.total)} (limit ${formatMoney(limit)})`,
          );
        } else {
          recordDecision(
            {
              ...baseDecision,
              decision: "REVIEW_REQUIRED",
              reasonCode: "POLICY_ABOVE_LIMIT",
            },
            "MERCHANT_REVIEW_REQUIRED",
            limit
              ? `Amount ${formatMoney(proposal.total)} exceeds auto-accept limit ${formatMoney(limit)} — merchant review required`
              : "Auto-accept limit unavailable — merchant review required",
          );
        }
      }

      return authorization;
    },

    async cancelProposal(proposalId) {
      await latency();
      const proposal = requireProposal(proposalId);
      if (proposal.status !== "PROPOSED") throw new Error("PROPOSAL_NOT_ACTIVE");
      proposal.status = "CANCELLED";
      const txn = transactionForProposal(proposalId);
      transitionTransaction(txn, "CANCELLED", {
        eventType: "PROPOSAL_CANCELLED",
        actorType: "BUYER",
        actorId: DEMO_BUYER_ID,
        reasonCode: "PROPOSAL_CANCELLED",
        summary: "Buyer cancelled the proposal",
      });
    },

    listReviews() {
      const items: ReviewItem[] = [];
      Object.values(state.proposals).forEach((proposal) => {
        const decision = state.decisions[proposal.id];
        if (!decision || decision.decision !== "REVIEW_REQUIRED") return;
        const authorization = Object.values(state.authorizations).find(
          (a) => a.proposalId === proposal.id && a.status === "APPROVED",
        );
        const product = state.products.find((p) => p.id === proposal.productId);
        if (!authorization || !product) return;
        items.push({
          proposal,
          authorization,
          product,
          reviewReason: decision.reasonCode,
        });
      });
      return items.sort((a, b) =>
        b.proposal.createdAt.localeCompare(a.proposal.createdAt),
      );
    },

    async approveReview(proposalId) {
      await latency();
      requireProposal(proposalId);
      const decision = state.decisions[proposalId];
      if (!decision || decision.decision !== "REVIEW_REQUIRED") {
        throw new Error("REVIEW_NOT_PENDING");
      }
      state.decisions[proposalId] = {
        ...decision,
        id: id("dec"),
        decision: "ALLOW",
        reasonCode: "MERCHANT_APPROVED",
        decidedBy: "MERCHANT_USER",
        createdAt: nowIso(),
      };
      const txn = transactionForProposal(proposalId);
      transitionTransaction(txn, "READY", {
        eventType: "MERCHANT_DECISION",
        actorType: "MERCHANT_USER",
        actorId: state.merchant.id,
        reasonCode: "MERCHANT_APPROVED",
        summary: `Merchant approved ${formatMoney(txn.amount)} after manual review`,
      });
    },

    async denyReview(proposalId, reason) {
      await latency();
      requireProposal(proposalId);
      const decision = state.decisions[proposalId];
      if (!decision || decision.decision !== "REVIEW_REQUIRED") {
        throw new Error("REVIEW_NOT_PENDING");
      }
      state.decisions[proposalId] = {
        ...decision,
        id: id("dec"),
        decision: "DENY",
        reasonCode: "MERCHANT_DENIED",
        decidedBy: "MERCHANT_USER",
        createdAt: nowIso(),
      };
      const txn = transactionForProposal(proposalId);
      transitionTransaction(txn, "CANCELLED", {
        eventType: "MERCHANT_DECISION",
        actorType: "MERCHANT_USER",
        actorId: state.merchant.id,
        reasonCode: "MERCHANT_DENIED",
        summary: `Merchant denied the proposal: ${reason}`,
      });
    },

    async executeTransaction(proposalId) {
      await latency();
      const txn = transactionForProposal(proposalId);
      if (txn.state !== "READY") throw new Error("TXN_NOT_READY");
      transitionTransaction(txn, "EXECUTING", {
        eventType: "EXECUTION_STARTED",
        actorType: "PLATFORM",
        reasonCode: "EXECUTION_STARTED",
        summary: "Payment execution started",
      });
      // "manual_review" behaves like auto_success at payment time; it is handled
      // by sharing the same step branch in buildPaymentSteps.
      stepQueues.set(txn.id, buildPaymentSteps(txn.id, state.demoOutcome));
      scheduleNextStep(txn.id, stepDelay());
      return txn;
    },

    async refreshTransaction(transactionId) {
      await latency();
      const txn = requireTransaction(transactionId);
      if (txn.state === "UNKNOWN" || txn.state === "RECONCILING") {
        appendAudit(txn.id, {
          eventType: "RECONCILIATION_REFRESH",
          actorType: "PLATFORM",
          actorId: null,
          reasonCode: "MANUAL_REFRESH",
          previousState: txn.state,
          newState: txn.state,
          correlationId: `cor_${randomHex(12)}`,
          providerReferenceRedacted: null,
          summary: "Status check requested — reconciliation accelerated",
        });
        const pending = timers.get(txn.id);
        if (pending) clearTimeout(pending);
        timers.delete(txn.id);
        // Re-check the provider soon; the pending steps continue from where
        // the simulation left off (no state is skipped, VERIFYING still runs).
        scheduleNextStep(txn.id, 500);
        commit();
      }
      return txn;
    },

    getTransaction(idArg) {
      return state.transactions[idArg];
    },

    listTransactions() {
      return Object.values(state.transactions).sort((a, b) =>
        b.createdAt.localeCompare(a.createdAt),
      );
    },

    getAudit(transactionId) {
      return state.audit[transactionId] ?? [];
    },

    setDemoOutcome(o) {
      state.demoOutcome = o;
      commit();
    },

    demoReset() {
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
      stepQueues.clear();
      state = buildInitialState();
      listeners.forEach((cb) => cb());
    },
  };

  return {
    getState: () => state,
    subscribe(cb) {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    actions,
  };
}
