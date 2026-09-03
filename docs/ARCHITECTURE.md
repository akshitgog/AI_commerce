# Architecture — trusted transaction authority

## System context

```text
                           AI COMMERCE GATEWAY

MERCHANT SIDE
─────────────
Nontechnical Merchant
        │
        ▼
Merchant Dashboard
        │
        ├── Catalog management
        ├── Merchant policy
        ├── Manual review
        └── Orders / audit
        │
        ▼
Commerce Application Services


PRIMARY BUYER PATH
──────────────────
Nontechnical Buyer
        │
        ▼
Reference Buyer Chat
        │
        ▼
AI / Tool-calling Layer
        │
        ▼
Buyer Adapter
        │
        └──────────────────────────────┐
                                       │

EXTERNAL INTEROPERABILITY PATH         │
──────────────────────────────         │
MCP-capable External AI Application    │
        │                              │
        ▼                              │
Remote MCP Server                      │
        │                              │
        ▼                              │
MCP Adapter                            │
        │                              │
        └──────────────────────────────┤
                                       ▼
                           Commerce Application Services
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
            Catalog Service      Proposal / Gates     Transaction Authority
                                      │                    │
                         ┌────────────┴────────────┐       │
                         ▼                         ▼       │
               Buyer Authorization        Merchant Policy │
                                                     / Review
                                                           │
                                                           ▼
                                                  Razorpay Adapter
                                                           │
                                                           ▼
                                                  Razorpay Test Mode
                                                           │
                                 ┌─────────────────────────┼──────────────────────┐
                                 ▼                         ▼                      ▼
                              Checkout                  Webhook             Provider Lookup
                                 └─────────────────────────┼──────────────────────┘
                                                           ▼
                                                Verify / Reconcile / Audit
```

The reference chat is the guaranteed buyer-facing demo surface. MCP is a separate interoperability adapter for compatible external AI applications. Both paths converge on the same application services **before** any financial business logic.

There is one trusted transaction system, not separate logic for chat and MCP.

The application is a modular monolith backed by a relational database. MCP and HTTP are adapters over common application services; neither contains separate financial business logic.

## Interface boundaries

### Reference buyer chat

The reference chat owns conversational presentation and tool orchestration only. It may interpret intent and invoke narrow buyer tools, but it does not own trusted money, authorization, merchant policy, transaction state, provider calls or payment truth.

### Remote MCP server

The remote MCP server exposes the same narrow commerce operations to MCP-capable external AI applications. The MCP adapter translates protocol/tool calls into the same application-service commands used by the reference chat and HTTP API.

The MCP layer must never independently:

- derive authoritative price or total;
- grant buyer authorization;
- decide merchant acceptance;
- mutate transaction state outside application services;
- call Razorpay outside the provider adapter/transaction authority;
- bypass idempotency or reconciliation;
- mark a transaction successful.

### Shared backend

Reference chat, HTTP and MCP are adapters. Correctness-critical behavior lives in the application/domain layers and durable database.

## Trust boundaries

Untrusted until validated:

- natural-language input and AI output;
- MCP and HTTP request fields;
- catalog descriptions and AI-enriched metadata;
- checkout-return parameters and webhook payloads;
- any client-supplied amount, currency, provider identifier or state.

Trusted only after server-side validation:

- authenticated actor and merchant membership;
- merchant-owned structured commercial fields;
- persisted proposal and authorization state;
- policy evaluation against persisted inputs;
- valid transaction transitions;
- cryptographically verified provider messages and independently queried provider state.

## Component responsibilities

- **Identity and tenant guard:** authenticates actors and checks merchant ownership on every scoped operation.
- **Catalog service:** validates commercial fields, versions products and exposes only published products.
- **Proposal service:** snapshots product version and derives totals.
- **Buyer-authorization service:** captures explicit approval or checks a bounded mandate.
- **Merchant-policy service:** evaluates acceptance rules and manages manual decisions.
- **Transaction authority:** checks readiness, locks execution, controls state and emits events.
- **Razorpay adapter:** isolates SDK/API operations, validates signatures and translates provider states.
- **Reconciliation worker/service:** resolves `UNKNOWN` using stored provider identifiers and lookups.
- **Audit store:** persists append-only causal events distinct from operational logs.

## Canonical transaction lifecycle

```text
PROPOSED
 ├─→ BUYER_AUTH_REQUIRED ─→ MERCHANT_POLICY_PENDING
 └────────────────────────→ MERCHANT_POLICY_PENDING

MERCHANT_POLICY_PENDING
 ├─→ MERCHANT_REVIEW_REQUIRED ─→ READY
 ├─→ READY
 └─→ FAILED (policy denial)

READY → EXECUTING
          ├─→ PAYMENT_PENDING → VERIFYING → SUCCEEDED | FAILED
          └─→ UNKNOWN → RECONCILING → PAYMENT_PENDING | SUCCEEDED | FAILED

Eligible pre-success states → CANCELLED | EXPIRED
```

States describe the platform transaction. Provider-order and payment states are stored separately and never collapsed into `SUCCEEDED` prematurely.

## Execution algorithm

Within a database transaction, execution:

1. locks the logical transaction;
2. verifies state is `READY` or returns the existing compatible result;
3. verifies buyer authorization and any merchant approval remain active;
4. re-evaluates merchant policy;
5. re-reads published product version, price and stock;
6. validates or creates the idempotent payment-attempt record;
7. commits `EXECUTING` before external dispatch.

After dispatch, the adapter records provider references and transitions to `PAYMENT_PENDING`, `UNKNOWN` or a verified terminal state. A timeout never triggers an immediate second creation call.

## Idempotency

- External mutating operations accept `Idempotency-Key`.
- Scope is actor + operation + key.
- The request fingerprint covers the immutable logical request.
- Same key and same fingerprint returns the stored outcome.
- Same key and different fingerprint returns `409 IDEMPOTENCY_KEY_REUSED`.
- Database uniqueness, not an in-memory lock, is the final guard.
- A unique transaction-to-provider-attempt relationship prevents duplicate provider orders across restart.

## Provider verification

The initial implementation spike must establish the exact Razorpay Test Mode payment/capture condition. Checkout-return signatures and webhook signatures are verified according to the selected integration, and provider lookup is used whenever local and provider state disagree or delivery is uncertain.

## Audit model

Every consequential event records actor, action, reason code, merchant, buyer, proposal/authorization references, prior/new state, correlation ID, time and redacted provider reference. Descriptions and raw conversation may be linked for context but are not authoritative financial inputs.

## Deployment

- Backend: FastAPI or equivalent modular monolith.
- Data: PostgreSQL or equivalent transactional relational database.
- Dashboard: thin React/Next.js or equivalent client.
- Buyer access: reference chat connected to the same backend application services.
- External agent interoperability: one remote MCP server connected to those same application services.
- Background work: database-backed worker or safe scheduled reconciliation; Redis is optional and not correctness-critical.
