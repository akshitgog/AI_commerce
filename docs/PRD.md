# Product requirements — AI Commerce Gateway v1

## Objective

Make a participating merchant safely transactable by an AI buyer end to end using Razorpay Test Mode. The system must visibly satisfy the Track 1 bar: money actions are explainable, bounded, gated and auditable, and at least one failure is handled gracefully.

## Personas

### Merchant operator

Publishes products without building an agent integration, controls merchant acceptance policy and investigates orders and failures.

### Human buyer

Expresses intent, sees the exact proposal and provides explicit approval or a bounded mandate. The human buyer—not the AI—owns spending consent.

### AI buyer

Uses narrow tools to discover and propose. It cannot establish trusted prices, approve its own request or access provider credentials.

### Platform operator

Configures the Razorpay Test Mode integration, observes technical failures and gathers reproducible submission evidence.

## P0 user journeys

### Merchant publication

1. Demo merchant signs in.
2. Merchant creates a product manually or imports validated CSV.
3. Optional AI enrichment suggests non-financial metadata.
4. Merchant reviews commercial fields and publishes the product.
5. Only the published version becomes visible in Reference Buyer Chat through the buyer API.
6. Separately, the same published version may be discovered by a compatible external AI application
   through the Remote MCP Server.

### AI-buyer purchase

1. Human asks Reference Buyer Chat for a product.
2. AI searches the demonstrated merchant catalog.
3. Backend returns structured current results.
4. AI asks the backend to create a proposal for product and quantity.
5. Backend snapshots product version and derives total.
6. Human buyer approves that proposal or a matching active mandate is found.
7. Merchant policy returns `ALLOW`, `DENY` or `REVIEW_REQUIRED`.
8. If required, a merchant operator records manual acceptance.
9. Backend revalidates all gates, price, product version and stock.
10. Backend creates or reuses the single provider attempt and returns checkout initiation data.
11. Human completes Razorpay Test Mode checkout.
12. Backend verifies provider truth and records the final state.

### External MCP interoperability

1. A compatible external AI application connects to the Remote MCP Server.
2. It discovers the same published catalog and may create a proposal through the same application
   services and trust boundaries.
3. This separate interoperability proof does not replace or gate the Reference Buyer Chat journey.

### Failure recovery

1. Provider request is dispatched.
2. Response is lost or times out.
3. Backend records `UNKNOWN` and blocks blind re-execution.
4. Reconciliation queries provider truth using stored references/fingerprint.
5. Transaction resolves to `PAYMENT_PENDING`, `SUCCEEDED` or `FAILED` with an audit reason.

## Functional requirements

### Merchant and catalog

- Demo authentication with merchant-scoped authorization.
- Product create, edit, publish, unpublish and CSV import.
- Structured SKU, title, description, category, price, currency, available quantity, status and version.
- Merchant policy configuration and manual-review queue.
- A second merchant test fixture that is inaccessible to the demonstrated merchant.

### Proposal and buyer authorization

- Immutable proposal snapshot with server-calculated total and expiry.
- Buyer authorization bound to buyer, proposal hash, merchant, product, quantity, amount, currency and expiry.
- MCP can request authorization but cannot mark it approved.
- Approval is captured through an authenticated human-controlled surface.

### Merchant gate

- Policy decision is independent from buyer authorization.
- V1 policies: deny; allow at/below configured maximum; require manual review above maximum or for every order.
- Manual merchant acceptance is recorded separately from buyer approval.

### Transaction and provider

- Persisted lifecycle with validated transitions.
- Durable idempotency across retries, concurrency and restart.
- Razorpay Test Mode provider-order creation and checkout handoff.
- Verified payment/capture completion rule.
- Verified and deduplicated webhooks plus provider lookup.
- Explicit unknown outcome and reconciliation path.

### Audit and UI

- Structured reason for every allow, deny, review, execution and transition.
- Merchant dashboard displays products, policy, review queue, transactions, provider phase, failure reason and event timeline.
- Raw chat is not required to reconstruct financial history.

## Non-functional requirements

- Integer minor units for money and explicit ISO currency.
- Durable relational storage for correctness-critical state.
- Secrets excluded from client responses, audit metadata and application logs.
- Deterministic API errors and correlation identifiers.
- Local one-command startup for the core product plus separately documented MCP client configuration
  for interoperability evidence.

## Acceptance criteria

V1 is complete only when the scenarios in `EVALUATION.md` pass with evidence in `TESTED.md`, including a real Razorpay Test Mode payment flow, duplicate suppression, tenant isolation and timeout reconciliation.

## Non-goals

Multiple production merchants, merchant aggregation, open-web shopping, recommendation systems, campaigns, multiple payment providers, multiple client integrations and production certification are not required for v1.
