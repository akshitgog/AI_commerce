# Implementation plan — one defensible vertical slice

The numbered phases in this file are product-level integration stages, not permission for one giant
branch or agent run. Feature delivery uses the A/B/C child phases in `MASTER_DEVELOPMENT_PLAN.md`,
the workstream briefs and `PHASE_EXECUTION.md`. Each child phase is reviewed and approved before the
next begins; product-level stages close only when the required lane outputs integrate.

## Phase 0 — provider truth spike

Use Razorpay Test Mode to validate the exact order, checkout, signature/webhook, payment and capture lifecycle. Decide and test the precise provider condition mapped to `SUCCEEDED`. Record redacted evidence before building UI breadth.

Exit: one manual end-to-end Test Mode payment is verified and the adapter contract is documented.

## Phase 1 — domain and database

Implement the canonical entities, constraints, transaction states, proposal hashing, authorization matching, merchant policy, event append and database-backed idempotency.

Exit: deterministic unit and persistence tests prove invalid transitions, stale scope and duplicate logical requests are rejected.

## Phase 2 — merchant publication

Implement demo merchant authentication, manual product management, CSV import, publication and policy configuration. Create a second isolated merchant fixture. Keep AI enrichment optional.

Exit: only published products appear to buyers and cross-tenant operations fail.

## Phase 3 — proposal and independent gates

Implement catalog search, immutable proposal creation, buyer approval surface, merchant policy evaluation and merchant manual-review decision.

Exit: missing buyer authorization and missing merchant acceptance fail for distinct, explainable reasons.

## Phase 4 — transaction authority

Implement readiness checks, state transitions, execution locking, idempotency records, payment attempts, Razorpay adapter and checkout initiation.

Exit: concurrent and repeated execution returns one logical result and at most one provider order.

## Phase 5 — verification and recovery

Implement checkout verification, webhook verification/deduplication, provider lookup, `UNKNOWN`, reconciliation and a test-only timeout-after-dispatch fault.

Exit: verified payments reach `SUCCEEDED`; failed/abandoned payments do not; ambiguous requests reconcile without blind retry.

## Phase 6 — reference chat, MCP and dashboard

Build the reference buyer chat over the shared application layer as the guaranteed buyer demo. Expose the seven canonical tools through a separate remote MCP adapter over that same layer. Build merchant product, policy, review, transaction and audit views. Configure one compatible external MCP client for interoperability proof.

Exit: the full judge journey works without direct API manipulation.

## Phase 7 — evidence and submission

Run every `EVALUATION.md` scenario, update `TESTED.md`, publish redacted provider evidence and record the five-minute demo. State remaining limitations honestly.

## Cut order

Cut in this order if constrained:

1. AI catalog enrichment.
2. CSV polish and advanced search.
3. Dashboard animation and visual extras.
4. Nonessential MCP convenience tools.

Do not cut merchant publication, the reference buyer-chat flow, independent buyer/merchant gates, provider verification, durable idempotency, reconciliation, tenant isolation or audit evidence. If constrained, reduce MCP proof breadth but preserve at least catalog discovery and proposal creation over the same backend.
