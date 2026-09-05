import type {
  Money,
  Product,
  Policy,
  PolicyMode,
  Proposal,
  Authorization,
  MerchantDecision,
  Transaction,
  ReviewItem,
  AuditEvent,
} from "../types";

export class ApiError extends Error {
  code: string;
  details: any;
  correlationId: string;
  constructor(payload: any) {
    super(payload.error?.message || "API Error");
    this.name = "ApiError";
    this.code = payload.error?.code || "UNKNOWN";
    this.details = payload.error?.details || {};
    this.correlationId = payload.correlation_id || "";
  }
}

export class ApiClient {
  private buyerToken?: string;
  private merchantToken?: string;

  private buyerHeaders() {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.buyerToken) {
      h["Authorization"] = "Bearer " + this.buyerToken;
    }
    return h;
  }

  private merchantHeaders() {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.merchantToken) {
      h["Authorization"] = "Bearer " + this.merchantToken;
    }
    return h;
  }

  private async request(url: string, options: RequestInit) {
    const res = await fetch("/api" + url, options);
    if (!res.ok) {
        let err;
        try { err = await res.json(); } catch(e) { throw new Error(res.statusText); }
        throw new ApiError(err);
    }
    return res.json();
  }

  // --- Buyer Auth ---
  async loginBuyer() {
    const res = await fetch("/api/e2e/buyer-session", {
        method: "POST",
    });
    if (!res.ok) throw new Error("Buyer login failed");
    const data = await res.json();
    this.buyerToken = data.session_token;
  }

  // --- Merchant Auth ---
  async loginMerchant(merchantId: string, userId: string) {
    const res = await fetch("/api/merchants/" + merchantId + "/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId })
    });
    if (!res.ok) throw new Error("Merchant login failed");
    const data = await res.json();
    this.merchantToken = data.session_token;
  }

  // --- Catalog ---
  async listProducts(merchantId: string): Promise<Product[]> {
    const data = await this.request("/merchants/" + merchantId + "/products?limit=100", {
        headers: this.merchantHeaders()
    });
    return data.items.map(this.mapProduct);
  }

  async getProduct(merchantId: string, productId: string): Promise<Product> {
    const data = await this.request("/merchants/" + merchantId + "/products/" + productId, {
        headers: this.merchantHeaders()
    });
    return this.mapProduct(data);
  }

  async createProduct(merchantId: string, input: any): Promise<Product> {
    const data = await this.request("/merchants/" + merchantId + "/products", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
            sku: input.sku,
            title: input.title,
            description: input.description,
            category: input.category || null,
            price: input.price,
            available_quantity: input.availableQuantity,
            idempotency_key: crypto.randomUUID()
        })
    });
    return this.mapProduct(data);
  }

  async updateProduct(merchantId: string, productId: string, input: any, expectedVersion: number): Promise<Product> {
    const data = await this.request("/merchants/" + merchantId + "/products/" + productId, {
        method: "PATCH",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
            sku: input.sku,
            title: input.title,
            description: input.description,
            category: input.category || null,
            price: input.price,
            available_quantity: input.availableQuantity,
            expected_version: expectedVersion,
            idempotency_key: crypto.randomUUID()
        })
    });
    return this.mapProduct(data);
  }

  async publishProduct(merchantId: string, productId: string, expectedVersion: number): Promise<Product> {
    const confirm = await this.request("/merchants/" + merchantId + "/products/" + productId + "/publication-confirmations", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({ expected_version: expectedVersion, action: "PUBLISH" })
    });
    const data = await this.request("/merchants/" + merchantId + "/products/" + productId + "/publish", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
            expected_version: expectedVersion,
            confirmation_token: confirm.confirmation_token,
            idempotency_key: crypto.randomUUID()
        })
    });
    return this.mapProduct(data);
  }

  async unpublishProduct(merchantId: string, productId: string, expectedVersion: number): Promise<Product> {
    const confirm = await this.request("/merchants/" + merchantId + "/products/" + productId + "/publication-confirmations", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({ expected_version: expectedVersion, action: "UNPUBLISH" })
    });
    const data = await this.request("/merchants/" + merchantId + "/products/" + productId + "/unpublish", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
            expected_version: expectedVersion,
            confirmation_token: confirm.confirmation_token,
            idempotency_key: crypto.randomUUID()
        })
    });
    return this.mapProduct(data);
  }

  async addProductImage(
    merchantId: string,
    productId: string,
    file: File,
    altText?: string,
    sortOrder: number = 0
  ): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    if (altText) formData.append("alt_text", altText);
    formData.append("sort_order", sortOrder.toString());
    formData.append("idempotency_key", crypto.randomUUID());

    const headers = this.merchantHeaders();
    // Remove Content-Type header - browser will set it with boundary for multipart
    delete headers["Content-Type"];

    const res = await fetch(
      `/api/merchants/${merchantId}/products/${productId}/images`,
      {
        method: "POST",
        headers,
        body: formData,
      }
    );

    if (!res.ok) {
      let err;
      try {
        err = await res.json();
      } catch (e) {
        throw new Error(res.statusText);
      }
      throw new ApiError(err);
    }

    return res.json();
  }

  async deleteProductImage(
    merchantId: string,
    productId: string,
    imageId: string
  ): Promise<void> {
    const headers = {
      ...this.merchantHeaders(),
      "X-Idempotency-Key": crypto.randomUUID(),
    };

    const res = await fetch(
      `/api/merchants/${merchantId}/products/${productId}/images/${imageId}`,
      {
        method: "DELETE",
        headers,
      }
    );

    if (!res.ok) {
      let err;
      try {
        err = await res.json();
      } catch (e) {
        throw new Error(res.statusText);
      }
      throw new ApiError(err);
    }
  }

  async deleteProduct(merchantId: string, productId: string): Promise<void> {
    const headers = {
      ...this.merchantHeaders(),
      "X-Idempotency-Key": crypto.randomUUID(),
    };

    const res = await fetch(
      `/api/merchants/${merchantId}/products/${productId}`,
      {
        method: "DELETE",
        headers,
      }
    );

    if (!res.ok) {
      let err;
      try {
        err = await res.json();
      } catch (e) {
        throw new Error(res.statusText);
      }
      throw new ApiError(err);
    }
  }

    async extractDraft(merchantId: string, text: string): Promise<any> {
    const res = await this.request("/merchants/" + merchantId + "/products/extract-draft", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({ text })
    });
    return res.draft;
  }

  async suggestDescription(merchantId: string, productId: string): Promise<string> {
    const data = await this.request("/merchants/" + merchantId + "/products/" + productId, {
        headers: this.merchantHeaders()
    });
    const res = await this.request("/merchants/" + merchantId + "/products/extract-draft", {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({ text: data.description + " improved" }) // Mocking extraction
    });
    return res.draft.description;
  }

  // --- Policy ---
  async getPolicy(merchantId: string): Promise<Policy> {
    const data = await this.request("/merchants/" + merchantId + "/policy", {
        headers: this.merchantHeaders()
    });
    return this.mapPolicy(data);
  }

  async updatePolicy(merchantId: string, expectedVersion: number, input: { mode: PolicyMode; maxAmount?: Money }): Promise<Policy> {
    const data = await this.request("/merchants/" + merchantId + "/policy", {
        method: "PUT",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
            mode: input.mode,
            auto_accept_max: input.maxAmount,
            expected_version: expectedVersion,
            idempotency_key: crypto.randomUUID()
        })
    });
    return this.mapPolicy(data);
  }

  // --- Buyer Purchase ---
  async createProposal(input: { productId: string; quantity: number }): Promise<Proposal> {
    const data = await this.request("/v1/buyer/purchase-proposals", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
            merchant_id: "mer_demo", // defaulting to demo merchant
            product_id: input.productId,
            quantity: input.quantity
        })
    });
    return this.mapProposal(data);
  }

  async requestAuthorization(proposalId: string): Promise<void> {
    await this.request("/v1/buyer/purchase-proposals/" + proposalId + "/authorization-requests", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: "{}"
    });
  }

  async approveAuthorization(proposalId: string, proposal: Proposal): Promise<Authorization> {
    const data = await this.request("/v1/buyer/purchase-proposals/" + proposalId + "/approvals", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
            proposal_hash: proposal.proposalHash,
            max_quantity: proposal.quantity,
            max_amount_minor: proposal.total.amount_minor,
            currency: proposal.total.currency,
            expires_at: proposal.expiresAt
        })
    });
    return this.mapAuthorization(data);
  }

  async evaluateMerchantPolicy(proposalId: string): Promise<MerchantDecision> {
    const data = await this.request("/v1/buyer/purchase-proposals/" + proposalId + "/merchant-evaluations", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: "{}"
    });
    return this.mapDecision(data);
  }

  async recordMerchantDecision(
    merchantId: string,
    proposalId: string,
    decision: "ALLOW" | "DENY",
    reasonCode: string,
  ): Promise<MerchantDecision> {
    const data = await this.request(
      "/merchants/" + merchantId + "/reviews/" + proposalId + "/decisions",
      {
        method: "POST",
        headers: this.merchantHeaders(),
        body: JSON.stringify({
          decision,
          reason_code: reasonCode,
          expires_at: null,
          idempotency_key: crypto.randomUUID(),
        }),
      },
    );
    return this.mapDecision(data);
  }

  async executeTransaction(proposalId: string): Promise<Transaction> {
    const data = await this.request("/v1/buyer/transactions", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
            proposal_id: proposalId
        })
    });
    // The backend returns TransactionView, but we need product_id!
    // The frontend mapTransaction will add a dummy product_id or we patch it in the store
    return this.mapTransaction(data);
  }

  async verifyCheckout(transactionId: string, razorpayOrderId: string, razorpayPaymentId: string, razorpaySignature: string): Promise<Transaction> {
    const res = await fetch("/api/checkout/razorpay/verify", {
        method: "POST",
        headers: this.buyerHeaders(),
        body: JSON.stringify({
            transaction_id: transactionId,
            razorpay_order_id: razorpayOrderId,
            razorpay_payment_id: razorpayPaymentId,
            razorpay_signature: razorpaySignature
        })
    });
    const data = await res.json();
    if (!res.ok) {
        throw new ApiError(data.error ? data : { error: { message: data.detail || "Verification request failed", code: "VERIFICATION_FAILED" } });
    }
    return this.mapTransaction(data);
  }

  async getTransaction(transactionId: string): Promise<Transaction> {
    const data = await this.request("/v1/buyer/transactions/" + transactionId, {
        headers: this.buyerHeaders()
    });
    return this.mapTransaction(data);
  }

  async getMerchantTransactionEvents(merchantId: string, transactionId: string): Promise<AuditEvent[]> {
    const data = await this.request("/merchants/" + merchantId + "/transactions/" + transactionId + "/audit", {
        headers: this.merchantHeaders()
    });
    return data.items.map((item: any) => this.mapAuditEvent(item));
  }

  async getTransactionEvents(transactionId: string): Promise<AuditEvent[]> {
    const data = await this.request("/v1/buyer/transactions/" + transactionId + "/events", {
        headers: this.buyerHeaders()
    });
    return data.items.map(this.mapAuditEvent);
  }

  async listReviews(merchantId: string): Promise<ReviewItem[]> {
    const data = await this.request("/merchants/" + merchantId + "/reviews", {
        headers: this.merchantHeaders()
    });
    return Promise.all(data.items.map(async (item: any) => {
        const product = await this.getProduct(merchantId, item.proposal.product_id);
        return {
            proposal: this.mapProposal(item.proposal),
            authorization: this.mapAuthorization(item.authorization),
            product,
            reviewReason: item.review_reason
        };
    }));
  }

  async listTransactions(merchantId: string): Promise<Transaction[]> {
    try {
        const data = await this.request("/merchants/" + merchantId + "/transactions", {
            headers: this.merchantHeaders()
        });
        return data.items.map((item: any) => this.mapTransaction(item));
    } catch (e: any) {
        if (e?.error?.code === "NOT_IMPLEMENTED") return [];
        throw e;
    }
  }

  async chat(messages: { role: string; content: string }[]): Promise<any> {
    const data = await this.request("/v1/buyer/chat", {
        method: "POST",
        headers: { ...this.buyerHeaders(), "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ messages })
    });
    const ingestedProposals = data.tool_results
        ?.filter((tr: any) => tr.tool === "create_purchase_proposal" && tr.result)
        ?.map((tr: any) => this.mapProposal(tr.result)) || [];
    const ingestedProducts = data.tool_results
        ?.filter((tr: any) => tr.tool === "search_catalog" && tr.result?.items)
        ?.flatMap((tr: any) => tr.result.items.map((p: any) => this.mapProduct(p))) || [];
    return { ...data, ingestedProposals, ingestedProducts };
  }

  // --- Mappers (snake_case -> camelCase) ---
  private mapProduct(data: any): Product {
    return {
        id: data.id,
        merchantId: data.merchant_id,
        sku: data.sku,
        title: data.title,
        description: data.description,
        category: data.category,
        price: data.price,
        availableQuantity: data.available_quantity,
        status: data.status,
        version: data.version,
        images: (data.images || [])
            .sort((a: any, b: any) => (a.sort_order || 0) - (b.sort_order || 0))
            .map((img: any, i: number) => ({
                id: img.id, url: img.url, alt: img.alt_text, position: img.sort_order, isPrimary: i === 0
            })),
        updatedAt: new Date().toISOString() // Not returned by backend, use current date
    };
  }

  private mapPolicy(data: any): Policy {
    return {
        mode: data.mode,
        maxAmount: data.auto_accept_max,
        version: data.version
    };
  }

  private mapProposal(data: any): Proposal {
    return {
        id: data.id,
        buyerId: data.buyer_id,
        merchantId: data.merchant_id,
        productId: data.product_id,
        productVersion: data.product_version,
        quantity: data.quantity,
        unitPrice: data.unit_price,
        total: data.total,
        proposalHash: data.proposal_hash,
        status: data.status,
        nextRequiredGate: data.next_required_gate,
        expiresAt: data.expires_at,
        createdAt: data.created_at
    };
  }

  private mapAuthorization(data: any): Authorization {
    return {
        id: data.id,
        buyerId: data.buyer_id,
        proposalId: data.proposal_id,
        proposalHash: data.proposal_hash,
        maxQuantity: data.max_quantity,
        maxAmount: data.max_amount,
        authorizedBy: data.authorized_by,
        status: data.status,
        expiresAt: data.expires_at,
        createdAt: data.created_at
    };
  }

  private mapDecision(data: any): MerchantDecision {
    return {
        id: data.id,
        proposalId: data.proposal_id,
        merchantId: data.merchant_id,
        policyVersion: data.policy_version,
        decision: data.decision,
        reasonCode: data.reason_code,
        decidedBy: data.decided_by.startsWith("policy:") ? "POLICY" : "MERCHANT_USER",
        createdAt: data.created_at
    };
  }

  private mapTransaction(data: any): Transaction {
    return {
        id: data.id,
        proposalId: data.proposal_id,
        merchantId: data.merchant_id,
        buyerId: data.buyer_id,
        productId: "", // Need to attach this in store logic from proposal!
        amount: data.amount,
        state: data.state,
        providerPhase: data.provider_phase ? {
            provider: data.provider_phase.provider,
            providerOrderId: data.provider_phase.provider_order_id,
            orderState: data.provider_phase.order_state,
            paymentState: data.provider_phase.payment_state,
            lastVerifiedAt: data.provider_phase.last_verified_at,
        } : null,
        createdAt: data.created_at,
        updatedAt: data.updated_at
    };
  }

  private mapAuditEvent(data: any): AuditEvent {
    // transactionEventView has NO summary string - we generate it
    let summary = data.event_type;
    if (data.previous_state && data.new_state) {
        summary = `Transitioned from ${data.previous_state} to ${data.new_state}`;
    }
    if (data.reason_code && data.reason_code !== "UNKNOWN") {
        summary += ` due to ${data.reason_code}`;
    }

    return {
        id: data.id,
        transactionId: data.transaction_id,
        eventType: data.event_type,
        actorType: data.actor_type,
        actorId: data.actor_id,
        reasonCode: data.reason_code,
        previousState: data.previous_state ?? null,
        newState: data.new_state ?? null,
        correlationId: data.correlation_id,
        providerReferenceRedacted: data.provider_reference_redacted,
        summary,
        createdAt: data.created_at
    };
  }
}
