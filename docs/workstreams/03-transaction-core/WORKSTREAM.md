# Workstream 03 — Transaction Core

## Mission

Implement the single trusted financial authority: immutable proposals, independent buyer/merchant gates, valid transaction transitions, durable idempotency and structured audit.

## Why this workstream exists

This is the most correctness-sensitive domain. It centralizes rules that no UI, AI, MCP or provider adapter may duplicate.

## Ownership

`PurchaseProposal`, `BuyerAuthorization`, `MerchantDecision`, `Transaction`, `IdempotencyRecord`, `TransactionEvent`; proposal snapshots/hashes; authorization matching; policy integration; readiness/revalidation; locking; state machine; idempotency; audit semantics.

## Explicit non-ownership

Razorpay SDK/API operations, signature verification, provider-state translation, UI/chat/MCP presentation, catalog persistence or infrastructure plumbing.

## Inputs / dependencies

Frozen catalog/policy/provider contracts; published product/version/stock from 02; DB transactions/constraints from 06; provider abstraction from 04.

## Outputs / exposed contracts

`proposal.create`, `authorization.request`, `authorization.approve`, `merchant_policy.evaluate`, `merchant_policy.record_manual_decision`, `transaction.create`, `transaction.execute`, `transaction.get_status`, `transaction.reconcile`, `transaction.get_audit`.

## Relevant domain entities

Owns the six records above plus logical ownership of `Buyer`. Consumes `Product`, `MerchantPolicy` and `PaymentAttempt` references.

## Relevant database tables

`Buyer`, `PurchaseProposal`, `BuyerAuthorization`, `MerchantDecision`, `Transaction`, `IdempotencyRecord` and `TransactionEvent`; consumes foreign references to catalog/provider tables.

## Relevant API/application services

Proposal/authorization routes, transaction create/execute/status/reconcile/audit routes and stable domain errors.

## Relevant UI surfaces

None. Supplies trusted read models/actions to buyer and merchant interfaces.

## Directory ownership

Proposal, authorization, merchant-decision integration, transaction, idempotency and audit domain/application code and tests; transaction migrations coordinated with 06.

## Shared contracts consumed

`catalog.get_product`, merchant policy evaluation and every provider abstraction method. Provider responses are evidence, never direct state assignments.

## Shared contracts exposed

The application services listed above, canonical states/transitions, audit event schema and idempotency semantics.

## Security/trust rules

Derive money server-side; bind human authorization to exact scope; keep merchant acceptance separate; lock before execute; atomically persist consequential transitions/events; never accept forced state/provider truth; enforce actor and tenant scope.

## Required implementation tasks

1. Implement immutable proposal snapshot/hash and expiry.
2. Implement authorization request and human approval with exact limits.
3. Integrate merchant policy/manual decisions without merging the gates.
4. Implement canonical transition validator and readiness revalidation.
5. Implement DB locking/idempotency and provider-attempt orchestration through the abstraction.
6. Emit append-only causal events atomically with state changes.

## Lane phases

| Phase | Scope | Exit evidence |
|---|---|---|
| B1 `phase/b1-transaction-domain` | Canonical transition validator and atomic audit-event semantics | State-table, invalid-transition and event-atomicity tests; no Razorpay |
| B2 `phase/b2-proposal-gates` | Proposal snapshots, buyer authorization and independent merchant gate | Trusted-total, stale proposal, consent, policy and manual-review tests |
| B3 `phase/b3-idempotency-locking` | Durable idempotency, locking and provider-attempt orchestration boundary | Fingerprint, repeat/concurrent/restart and one-live-attempt tests using a provider fake |

Each phase branches from `feature/transaction-core`. B1 must not implement proposals or provider
calls; B2 must not implement provider dispatch; B3 stops at the provider abstraction. Provider
implementation begins only in B4 under workstream 04.

## Required tests

Trusted totals, proposal immutability/staleness, no/wrong consent blocked, policy modes, approval expiry, invalid transitions, price/version/stock drift, same/different idempotency fingerprint, concurrent/restart behavior, one live attempt, unknown no-retry rule, tenant isolation and audit reconstruction.

## Evidence required

Unit, repository, concurrency, contract and state-transition test output. Provider truth is evidenced by 04/07.

## Integration points

02 catalog/policy data, 04 provider/recovery, 05 buyer/MCP adapters, 06 database and 07 cross-system tests.

## Completion criteria

M2 is complete; M3–M5 orchestration obeys the provider contract; invariants remain valid under retry, concurrency and restart.

## Known non-goals

Provider-specific SDK details, recommendations, UI status styling, multi-provider routing and distributed microservices.

## Things this agent must never do

Call Razorpay directly, treat order creation as success, put idempotency only in memory, let AI approve, merge buyer/merchant gates, blind-retry unknown dispatch or change shared contracts silently.

## Questions/escalation triggers

Escalate canonical state/transition changes, authorization scope changes, audit atomicity issues, retry semantics, policy conflicts or any provider behavior that cannot fit the frozen abstraction.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../ARCHITECTURE.md`,
`../../API.md`, `../../DATA_MODEL.md` and `../../SECURITY.md`.
