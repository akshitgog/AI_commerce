import {
  type AuditEvent,
  type Authorization,
  type Merchant,
  type MerchantDecision,
  type Money,
  type Policy,
  type PolicyMode,
  type Product,
  type Proposal,
  type ReviewItem,
  type Transaction,
} from "../types";

import { ApiClient, ApiError } from "../api/client";

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
  decisions: Record<string, MerchantDecision>;
  transactions: Record<string, Transaction>;
  audit: Record<string, AuditEvent[]>;
  reviews: ReviewItem[];
  demoOutcome: DemoOutcome;
  initialized: boolean;
}

export interface CommerceActions {
  searchCatalog(input: { query?: string; category?: string; maxPriceMinor?: number; }): Promise<Product[]>;
  getProduct(productId: string): Promise<Product | undefined>;
  createProduct(input: any): Promise<Product>;
  updateProduct(productId: string, input: any): Promise<Product>;
  publishProduct(productId: string): Promise<Product>;
  unpublishProduct(productId: string): Promise<Product>;
  deleteDraft(productId: string): Promise<void>;
  addProductImage(productId: string, image: { url: string; alt: string }): Promise<Product>;
  removeProductImage(productId: string, imageId: string): Promise<Product>;
  reorderProductImages(productId: string, imageIds: string[]): Promise<Product>;
  extractDraft(text: string): Promise<any>;
  suggestDescription(productId: string): Promise<string>;
  updatePolicy(input: { mode: PolicyMode; maxAmount?: Money }): Promise<Policy>;
  createProposal(input: { productId: string; quantity: number; }): Promise<Proposal>;
  requestAndApproveAuthorization(proposalId: string): Promise<Authorization>;
  refreshMerchantDecision(proposalId: string): Promise<MerchantDecision>;
  cancelProposal(proposalId: string): Promise<void>;
  listReviews(): ReviewItem[];
  approveReview(proposalId: string): Promise<void>;
  denyReview(proposalId: string, reason: string): Promise<void>;
  executeTransaction(proposalId: string): Promise<Transaction>;
  refreshTransaction(transactionId: string): Promise<Transaction>;
  getTransaction(id: string): Transaction | undefined;
  listTransactions(): Transaction[];
  loadAudit(transactionId: string): Promise<void>;
    getAudit(transactionId: string): AuditEvent[];
  setDemoOutcome(o: DemoOutcome): void;
  playDemo(): void;
  demoReset(): void;
  chat(messages: { role: string; content: string }[]): Promise<any>;
    init(): Promise<void>;
}

export function createCommerceStore() {
  const apiClient = new ApiClient();

  let state: CommerceState = {
    merchant: { id: "mer_demo", name: "Demo Merchant" },
    buyerName: "Demo Buyer",
    products: [],
    policy: { mode: "MANUAL_ALL", maxAmount: null, version: 1 },
    proposals: {},
    authorizations: {},
    decisions: {},
    transactions: {},
    audit: {},
    reviews: [],
    demoOutcome: "auto_success" as DemoOutcome,
    initialized: false,
  };

  const listeners = new Set<() => void>();

  function notify() {
    listeners.forEach((l) => l());
  }

  function setState(patch: Partial<CommerceState>) {
    state = { ...state, ...patch };
    notify();
  }

  async function doInit(): Promise<void> {
    // 1. Cold Start Waiter (Poll Health)
    let isAwake = false;
    while (!isAwake) {
      try {
        const res = await fetch("/api/health/live", { cache: "no-store", signal: AbortSignal.timeout(2000) });
        if (res.ok) {
           isAwake = true;
        } else {
           setState({ _coldStartOverlay: true } as any);
           await new Promise(r => setTimeout(r, 3000));
        }
      } catch (e) {
        setState({ _coldStartOverlay: true } as any);
        await new Promise(r => setTimeout(r, 3000));
      }
    }
    setState({ _coldStartOverlay: false } as any);

    // 2. Safe Logins
    try {
      await apiClient.loginBuyer();
    } catch (e) {
      console.warn("Failed to login buyer:", e);
    }
    try {
      await apiClient.loginMerchant("mer_demo", "user_1");
    } catch (e) {
      console.warn("Failed to login merchant:", e);
    }

    const [productsResult, policyResult, reviewsResult, txsResult] = await Promise.allSettled([
      apiClient.listProducts("mer_demo"),
      apiClient.getPolicy("mer_demo"),
      apiClient.listReviews("mer_demo"),
      apiClient.listTransactions("mer_demo")
    ]);

    const products = productsResult.status === "fulfilled" ? productsResult.value : [];
    const policy = policyResult.status === "fulfilled" ? policyResult.value : state.policy;
    const reviews = reviewsResult.status === "fulfilled" ? reviewsResult.value : [];
    const txs = txsResult.status === "fulfilled" ? txsResult.value : [];
    const transactions = Object.fromEntries(txs.map(t => [t.id, t]));

    setState({ products, policy, reviews, transactions, initialized: true });
  }

  // Initialization is shared and idempotent: concurrent callers (provider mount,
  // StrictMode double-effects, or an early search) all await the same in-flight
  // promise instead of racing against an empty catalog snapshot.
  let initPromise: Promise<void> | null = null;

  function ensureInitialized(): Promise<void> {
    if (state.initialized) return Promise.resolve();
    if (!initPromise) {
      initPromise = doInit().catch((error) => {
        initPromise = null; // allow a later retry instead of caching a rejection
        throw error;
      });
    }
    return initPromise;
  }

  async function storeTransactionWithAudit(
    transaction: Transaction,
    proposalId?: string,
  ): Promise<Transaction> {
    const proposal = state.proposals[proposalId ?? transaction.proposalId];
    if (proposal) transaction.productId = proposal.productId;
    const events = await apiClient.getTransactionEvents(transaction.id);
    setState({
      transactions: { ...state.transactions, [transaction.id]: transaction },
      audit: { ...state.audit, [transaction.id]: events },
    });
    return transaction;
  }

  const actions: CommerceActions = {
    async chat(messages) {
      const response = await apiClient.chat(messages);
      const patch: Partial<CommerceState> = {};
      if (response.ingestedProposals?.length) {
        const newProposals = { ...state.proposals };
        response.ingestedProposals.forEach((p: any) => { newProposals[p.id] = p; });
        patch.proposals = newProposals;
      }
      if (response.ingestedProducts?.length) {
        const existingIds = new Set(state.products.map((p: any) => p.id));
        const novel = response.ingestedProducts.filter((p: any) => !existingIds.has(p.id));
        if (novel.length) patch.products = [...state.products, ...novel];
      }
      if (Object.keys(patch).length) setState(patch);
      return response;
    },
    async init() {
      await ensureInitialized();
    },
    async searchCatalog(input) {
      // The catalog is only populated by init(); never search an empty snapshot.
      await ensureInitialized();
      return state.products.filter(p => p.status === "PUBLISHED");
    },
    async getProduct(productId) {
      return state.products.find(p => p.id === productId);
    },
    async createProduct(input) {
      const p = await apiClient.createProduct("mer_demo", input);
      setState({ products: [...state.products, p] });
      return p;
    },
    async updateProduct(productId, input) {
      const idx = state.products.findIndex(p => p.id === productId);
      const p = await apiClient.updateProduct("mer_demo", productId, input, state.products[idx].version);
      const newProducts = [...state.products];
      newProducts[idx] = p;
      setState({ products: newProducts });
      return p;
    },
    async publishProduct(productId) {
      const idx = state.products.findIndex(p => p.id === productId);
      const p = await apiClient.publishProduct("mer_demo", productId, state.products[idx].version);
      const newProducts = [...state.products];
      newProducts[idx] = p;
      setState({ products: newProducts });
      return p;
    },
    async unpublishProduct(productId) {
      const idx = state.products.findIndex(p => p.id === productId);
      const p = await apiClient.unpublishProduct("mer_demo", productId, state.products[idx].version);
      const newProducts = [...state.products];
      newProducts[idx] = p;
      setState({ products: newProducts });
      return p;
    },
    async deleteDraft(productId) {
      setState({ products: state.products.filter(p => p.id !== productId) });
    },
    async addProductImage(productId, image) {
      await apiClient.addProductImage(
        "mer_demo",
        productId,
        image.file,
        image.alt,
        image.sortOrder || 0
      );
      // Reload product to get updated images
      const product = await apiClient.getProduct("mer_demo", productId);
      const idx = state.products.findIndex(p => p.id === productId);
      if (idx !== -1) {
        const newProducts = [...state.products];
        newProducts[idx] = product;
        setState({ products: newProducts });
      }
      return product;
    },
    async removeProductImage(productId, imageId) {
      await apiClient.deleteProductImage("mer_demo", productId, imageId);
      // Reload product
      const product = await apiClient.getProduct("mer_demo", productId);
      const idx = state.products.findIndex(p => p.id === productId);
      if (idx !== -1) {
        const newProducts = [...state.products];
        newProducts[idx] = product;
        setState({ products: newProducts });
      }
      return product;
    },
    async reorderProductImages(productId, imageIds) {
      // For now, reordering is not implemented on backend - just return current product
      return state.products.find(p => p.id === productId)!;
    },
    async extractDraft(text) {
      return await apiClient.extractDraft("mer_demo", text);
    },
    async suggestDescription(productId) {
      return await apiClient.suggestDescription("mer_demo", productId);
    },
    async updatePolicy(input) {
      const p = await apiClient.updatePolicy("mer_demo", state.policy.version, input);
      setState({ policy: p });
      return p;
    },
    async createProposal(input) {
      const proposal = await apiClient.createProposal(input);
      setState({ proposals: { ...state.proposals, [proposal.id]: proposal } });
      return proposal;
    },
    async requestAndApproveAuthorization(proposalId) {
      const p = state.proposals[proposalId];
      await apiClient.requestAuthorization(proposalId);
      const auth = await apiClient.approveAuthorization(proposalId, p);
      const decision = await apiClient.evaluateMerchantPolicy(proposalId);
      setState({
        authorizations: { ...state.authorizations, [proposalId]: auth },
        decisions: { ...state.decisions, [proposalId]: decision },
      });
      return auth;
    },
    async refreshMerchantDecision(proposalId) {
      const decision = await apiClient.evaluateMerchantPolicy(proposalId);
      setState({
        decisions: { ...state.decisions, [proposalId]: decision },
      });
      return decision;
    },
    async cancelProposal(proposalId) {
      const p = state.proposals[proposalId];
      if (p) {
        setState({
          proposals: { ...state.proposals, [proposalId]: { ...p, status: "CANCELLED" as any } },
        });
      }
    },
    listReviews() {
      return state.reviews;
    },
    async approveReview(proposalId) {
      const decision = await apiClient.recordMerchantDecision(
        state.merchant.id,
        proposalId,
        "ALLOW",
        "MERCHANT_APPROVED",
      );
      setState({
        decisions: { ...state.decisions, [proposalId]: decision },
        reviews: state.reviews.filter(
          (item) => item.proposal.id !== proposalId,
        ),
      });
    },
    async denyReview(proposalId, reason) {
      const decision = await apiClient.recordMerchantDecision(
        state.merchant.id,
        proposalId,
        "DENY",
        reason,
      );
      setState({
        decisions: { ...state.decisions, [proposalId]: decision },
        reviews: state.reviews.filter(
          (item) => item.proposal.id !== proposalId,
        ),
      });
    },
    async executeTransaction(proposalId) {
      try {
        const transaction = await apiClient.executeTransaction(proposalId);
        return await storeTransactionWithAudit(transaction, proposalId);
      } catch (error) {
        if (
          !(error instanceof ApiError) ||
          error.code !== "PROVIDER_OUTCOME_UNKNOWN" ||
          typeof error.details?.transaction_id !== "string"
        ) {
          throw error;
        }
        const transaction = await apiClient.getTransaction(
          error.details.transaction_id,
        );
        return await storeTransactionWithAudit(transaction, proposalId);
      }
    },
    async refreshTransaction(transactionId) {
      const t = await apiClient.getTransaction(transactionId);
      return await storeTransactionWithAudit(t);
    },
    getTransaction(id) {
      return state.transactions[id];
    },
    listTransactions() {
      return Object.values(state.transactions).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    },
    async loadAudit(transactionId: string) {
      if (state.audit[transactionId]) return;
      const events = await apiClient.getMerchantTransactionEvents("mer_demo", transactionId);
      setState({ audit: { ...state.audit, [transactionId]: events } });
    },
    getAudit(transactionId) {
      return state.audit[transactionId] ?? [];
    },
    setDemoOutcome(o) {
      setState({ demoOutcome: o });
    },
    playDemo() {},
    demoReset() {},
  };

  return {
    getState: () => state,
    subscribe: (listener: () => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    actions
  };
}
