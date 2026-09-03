# Master Development Plan

## Purpose and authority

This document is the execution map for parallel AI-assisted development. Read it before assigning feature work, then give an agent only its relevant workstream document and canonical contracts.

`ARCHITECTURE.md` remains authoritative for system boundaries. In particular:

> Reference Buyer Chat is the primary guaranteed buyer demo path.

> Remote MCP Server is the external AI interoperability proof.

Both are adapters over the same commerce application services. Neither owns financial business logic.

## 1. Project objective

> Make a participating merchant safely transactable by an AI buyer end to end using Razorpay Test Mode.

The main demo uses one merchant end to end. A second merchant is a fixture for tenant-isolation proof only.

This is not a marketplace, Amazon/Blinkit clone, cross-merchant ranking engine, recommendation or campaign system, generic payment gateway, or multi-provider platform.

## 2. Complete architecture

```text
                            AI COMMERCE GATEWAY

MERCHANT SIDE                         PRIMARY BUYER PATH
Nontechnical Merchant                 Nontechnical Buyer
        |                                      |
        v                                      v
Merchant Dashboard                    Reference Buyer Chat
        |                                      |
        | Catalog / Images / Policy            v
        | Review / Orders / Audit       AI / Tool-calling Layer
        |                                      |
        v                                      v
Commerce Application Services <------- Buyer Adapter
        ^
        |
        |                              EXTERNAL INTEROPERABILITY
        +----------------------------- MCP Adapter
                                               ^
                                               |
                                       Remote MCP Server
                                               ^
                                               |
                                  MCP-capable External AI App

Commerce Application Services
        |-- Identity / Tenant Guard
        |-- Catalog Service
        |-- Proposal Service
        |-- Buyer Authorization
        |-- Merchant Policy / Review
        |-- Transaction Authority
        |-- Durable Idempotency
        `-- Structured Audit
                 |
                 v
           Razorpay Adapter
                 |
                 v
          Razorpay Test Mode
          /       |        \
   Checkout    Webhook    Provider Lookup
          \       |        /
                 v
       Verification / Reconciliation
                 |
                 v
              Final State
                 |
                 v
           Audit Timeline
```

The system is a modular monolith with a relational database. HTTP, dashboard, reference chat and MCP are interfaces. The application/domain layers are the authority.

> The system has many interfaces but only one financial authority.

```text
Merchant Dashboard --\
Reference Buyer Chat ---+--> Commerce Application Services
Remote MCP Server -----/              |
                                      v
                             Transaction Authority
                                      |
                                      v
                                  Razorpay
```

No UI, AI agent, MCP tool or HTTP controller may implement a second transaction engine.

## 3. Trusted financial invariants

1. Store money as integer minor units with explicit currency.
2. Never trust an AI/client-supplied price or total.
3. Derive proposal totals from trusted, merchant-owned catalog state.
4. An AI may request authorization but cannot approve itself.
5. Buyer consent and merchant acceptance are independent gates.
6. AI surfaces never call Razorpay directly.
7. AI surfaces never force transaction state.
8. Razorpay order creation is not payment success.
9. `SUCCEEDED` requires independently verified provider truth.
10. Idempotency is durable and database-enforced.
11. One logical transaction maps to at most one unambiguously live provider order.
12. Unknown dispatch outcomes follow `EXECUTING -> UNKNOWN -> RECONCILING -> provider lookup -> PAYMENT_PENDING | SUCCEEDED | FAILED`.
13. Never blindly retry provider creation after an unknown outcome.
14. Every consequential transaction-state change emits a structured financial audit event.
15. Every merchant-scoped operation enforces tenant isolation.

## 4. Canonical transaction flow

```text
Published Product
        v
Buyer Search
        v
Purchase Proposal (PROPOSED)
        v
BUYER_AUTH_REQUIRED
        v
Buyer Authorization
        v
MERCHANT_POLICY_PENDING
        |
        +--> ALLOW ----------------------+
        +--> REVIEW_REQUIRED             |
        |       v                        |
        |   MERCHANT_REVIEW_REQUIRED ----+
        `--> DENY --> FAILED             |
                                         v
                                       READY
                                         v
                                     EXECUTING
                                      /      \
                         PAYMENT_PENDING    UNKNOWN
                                |              v
                                v          RECONCILING
                            VERIFYING          |
                                \             /
                                 v           v
                              SUCCEEDED | FAILED
```

Eligible pre-success states may also become `CANCELLED` or `EXPIRED`. These are platform states. Provider-order, payment and capture states remain separate.

## 5. Workstreams and boundaries

| # | Workstream | Owns | Does not own |
|---|---|---|---|
| 01 | Merchant Experience | Dashboard UX, catalog/image/policy/review/orders/audit screens | Financial transitions, provider calls, authorization or idempotency algorithms |
| 02 | Catalog & Merchant Domain | Merchant, catalog, publication, stock, images metadata, search, tenant-scoped catalog services | Transaction execution or provider logic |
| 03 | Transaction Core | Proposals, authorization, policy integration, transaction state, idempotency, audit semantics | Razorpay SDK/API calls |
| 04 | Razorpay & Recovery | Provider adapter, checkout/webhooks/lookups, payment attempts, reconciliation | Buyer chat, MCP or independent platform policy |
| 05 | Buyer AI + MCP | Reference chat, tool orchestration, buyer adapter, remote MCP adapter and schemas | Trusted money, consent, policy, state, provider calls or reconciliation |
| 06 | Data & Infrastructure | PostgreSQL, migrations, auth infrastructure, object storage, config, deployment, observability foundations | Domain decisions or UI workflows |
| 07 | Testing, Evidence & Demo | Cross-system/E2E/adversarial/reliability tests, evidence, pitch validation | Replacing feature-owned tests or fabricating evidence |

Each feature workstream writes its own unit, module-integration and contract tests. Workstream 07 owns the seams and full journeys.

## 6. Three execution lanes

```text
                           INTEGRATOR
          Architecture / contracts / merges / evidence / pitch
                                |
               +----------------+----------------+
               |                |                |
               v                v                v
            AGENT A          AGENT B          AGENT C
       Merchant/Catalog   Transaction Core   Buyer Interface
        Experience +       + Razorpay /      + MCP + E2E
        Images + DB          Recovery +        Harness
```

Recommended initial branch groups:

- `merchant/catalog`: workstreams 01 and 02 plus bounded image-storage integration from 06.
- `transaction/core`: workstreams 03 and 04 plus transaction migrations from 06.
- `buyer/agent-interface`: workstream 05 plus the cross-system harness from 07; uses frozen contracts/mocks until dependencies exist.

The solo developer remains architecture owner, shared-contract owner, integration/merge reviewer, final evidence reviewer and pitch owner.

## 7. Shared contracts to freeze before feature work

Milestone 0 freeze status: **IMPLEMENTED on 2026-09-04**. The executable contract baseline is `src/ai_commerce_gateway/contracts/`, with method-name contract tests in `tests/contract/`. Future changes follow the approval process below.

### Entities

`Merchant`, `Product`, `ProductImage`, `MerchantPolicy`, `PurchaseProposal`, `BuyerAuthorization`, `MerchantDecision`, `Transaction`, `PaymentAttempt`, `TransactionEvent`.

### Application services

```text
catalog.search
catalog.get_product
proposal.create
authorization.request
authorization.approve
merchant_policy.evaluate
merchant_policy.record_manual_decision
transaction.create
transaction.execute
transaction.get_status
transaction.reconcile
transaction.get_audit
```

### Provider abstraction

```text
provider.create_order
provider.verify_checkout
provider.handle_webhook
provider.lookup_order
provider.lookup_payment
```

### Storage abstraction

```text
storage.upload_product_image
storage.delete_product_image
storage.get_public_url
```

Every lane consumes these contracts. To change one: document the request and reason, identify affected workstreams, update canonical API/data docs, obtain integrator approval, then change implementation. No lane silently changes a shared contract.

## 8. Database ownership

| Record/table | Logical owner | Notes |
|---|---|---|
| `Merchant`, `MerchantUser` | 02 | Tenant and membership domain; auth plumbing is supported by 06 |
| `Product`, `ProductMetadata`, `ProductImage`, `MerchantPolicy` | 02 | Image bytes live in object storage, not PostgreSQL |
| `Buyer` | 03 | Identity plumbing is supported by 06 |
| `PurchaseProposal`, `BuyerAuthorization`, `MerchantDecision` | 03 | Immutable/bounded financial gates |
| `Transaction`, `IdempotencyRecord`, `TransactionEvent` | 03 | Durable transaction authority and audit |
| `PaymentAttempt`, `ProviderWebhook` | 04 | Provider evidence and deduplication |

Workstream 06 owns migration mechanics, constraints, connections and deployment, but not domain meaning. PostgreSQL is correctness-critical; transaction state, idempotency and audit cannot be memory-only.

## 9. Product image plan

```text
Merchant -> Create Product -> Upload 1-3 Images -> Storage Service
         -> Public/signed URL -> ProductImage row -> Publish Product

Catalog Search -> Product -> image URL metadata -> Reference Buyer Chat display
```

`ProductImage` stores `id`, `merchant_id`, `product_id`, `storage_path`, `public_url`, `alt_text`, `sort_order`, `created_at`. Actual image bytes use object storage, preferably Supabase Storage behind the storage abstraction. MCP catalog responses may return safe image URL metadata, but MCP owns no storage business logic.

V1 excludes background removal, generation, computer vision, complex CDN behavior and a full moderation pipeline. Only basic file validation required for demo safety is in scope.

## 10. Testing during development

> Feature implementation is incomplete without tests.

Feature workstreams own unit, module-integration and exposed-interface contract tests. Workstream 07 owns cross-workstream integration, E2E, concurrency/restart, adversarial, Razorpay evidence and scenario-ledger execution.

Required checks include:

- catalog publication visibility and cross-tenant denial;
- server-derived immutable proposals;
- missing or mismatched buyer consent rejection;
- `MANUAL_ALL`, `AUTO_BELOW_LIMIT` and `DENY_ALL` merchant policy;
- repeat/concurrent execution producing one logical provider attempt;
- order creation not implying success, signature verification and webhook deduplication;
- timeout-after-dispatch entering `UNKNOWN`, no immediate retry and provider-truth reconciliation;
- catalog text/prompt injection unable to alter trusted price, permissions or authorization;
- complete reconstruction from structured audit events.

Scenario IDs remain aligned with `EVALUATION.md`, including the external MCP interoperability scenario. `TESTED.md` changes only after a reproducible run with inspectable evidence.

## 11. Integration milestones

| Gate | Exit condition |
|---|---|
| M0 Foundation | Repo layout, DB connection, migrations, frozen schemas/interfaces, errors, IDs, tests and environment template |
| M1 Merchant publication | Merchant creates product, uploads image, sets price/stock, publishes; buyer API sees it |
| M2 Proposal + gates | Buyer searches, proposes, approves; policy evaluates; transaction reaches `READY` |
| M3 Provider execution | `READY` creates/reuses one provider attempt and starts checkout; provider state is separate |
| M4 Verified completion | Trusted provider evidence alone permits `SUCCEEDED` |
| M5 Reliability | Duplicate/concurrent/restart safety, timeout recovery and webhook deduplication proven |
| M6 AI surfaces | Reference chat works end to end; MCP proves external catalog/proposal interoperability over the same semantics |
| M7 Submission evidence | Evaluation cases run, evidence captured, `TESTED.md` updated and pitch rehearsed |

## 12. Dependency graph

```text
                    SHARED CONTRACTS
                          |
          +---------------+----------------+
          v               v                v
Merchant / Catalog   Transaction Core   Buyer Chat / MCP
          |               |                |
          |               v                |
          |       Razorpay / Recovery      |
          |               |                |
          +---------------+----------------+
                          v
                     Integration
                          v
                       E2E Tests
                          v
                    Demo / Evidence
```

Parallel feature work is safe only after M0 freezes shared contracts. Contract mocks must match the frozen definitions and be replaced by contract tests at integration.

## 13. Agent and merge rules

Every assigned agent must:

1. read `AGENT.md` and this plan;
2. read only its relevant `workstreams/.../WORKSTREAM.md` plus linked canonical API/data/security docs;
3. inspect the current branch, status and recent log;
4. stay within directory/workstream ownership unless a shared-contract change is approved;
5. write tests with implementation;
6. update `progress.md` with the exact branch;
7. update `technical-questions.md` when evidence changes understanding;
8. update `TESTED.md` only from an actual reproducible run;
9. never fabricate Razorpay evidence;
10. submit small, reviewable changes and call out migrations/contracts explicitly.

Integration order follows the dependency graph, not whichever UI finishes first. The integrator resolves cross-lane conflicts and validates contract compatibility before merge.

## 14. Scope isolation

An agent assigned transaction core should normally need only `AGENT.md`, this plan, workstream 03, `DATA_MODEL.md`, `API.md`, `SECURITY.md`, and relevant code/tests. It should not need merchant UI or MCP internals. The same rule applies in reverse: merchant UI does not need webhook internals, and buyer/MCP does not implement transaction rules.

Workstream documents are local execution briefs; this master plan and canonical contracts remain the cross-cutting references.

## 15. Unresolved questions and escalation triggers

- Which exact Razorpay Test Mode payment/capture evidence permits platform `SUCCEEDED`? Resolve in the provider spike.
- Which product-image URL model is used for the demo: public URLs or expiring signed URLs? Freeze before implementing the buyer display contract.
- How does a connected MCP client obtain a stable, buyer-bound idempotency key without allowing identity substitution? Freeze before implementing mutating MCP calls.

Escalate any proposed change to canonical states, financial invariants, entity/service signatures, tenant model, or provider success semantics. Do not solve these independently inside an adapter.

## 16. Deliberate non-changes

This plan does not claim runtime implementation, change `flow.md`, mark any `TESTED.md` scenario as passing, add microservices, add payment providers, or make MCP the main demo. It creates implementation boundaries only.
