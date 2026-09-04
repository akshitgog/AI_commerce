# Workstream 05 — Buyer AI + Two-Sided MCP

## Mission

Deliver the primary reference buyer-chat journey plus isolated buyer and merchant MCP interoperability proofs through thin adapters over shared application services.

## Why this workstream exists

The reference chat guarantees a judgeable buyer demo without depending on an external MCP host. Buyer MCP proves external commerce interoperability; merchant MCP separately proves authenticated catalog management without duplicating catalog rules.

## Ownership

Reference Buyer Chat; AI/tool orchestration; buyer-facing adapter; separate buyer and merchant MCP permission surfaces; MCP schemas/mapping; external MCP compatibility demos.

## Explicit non-ownership

Trusted price/total, catalog rules, buyer approval, merchant policy, transaction transitions, Razorpay calls, payment truth, idempotency storage, publication-confirmation issuance or reconciliation logic.

## Inputs / dependencies

Frozen catalog/proposal/authorization/transaction service contracts from 02/03; auth binding from 06; provider behavior only through transaction services. Use mocks until services are available.

## Outputs / exposed contracts

Buyer chat UX and buyer tools: `search_catalog`, `get_product`, `create_purchase_proposal`, `request_authorization`, `execute_transaction`, `get_transaction_status`, `get_transaction_audit`. Merchant MCP tools: `create_product_draft`, `update_product`, `get_product`, `list_products`, `publish_product`, `unpublish_product`.

## Relevant domain entities

Consumes safe views of `Product`, `ProductImage`, `PurchaseProposal`, `BuyerAuthorization`, `Transaction`, `TransactionEvent`. Owns no financial table.

## Relevant database tables

No owned tables. All persistence is reached through shared application services; tool/session telemetry must not become financial authority.

## Relevant API/application services

Maps buyer and merchant tools one-to-one to the shared services in `API.md`. Human buyer approval remains separate. Merchant publish/unpublish requires a short-lived confirmation issued by the dashboard-controlled human surface.

## Relevant UI surfaces

Reference buyer chat, product cards/images, proposal confirmation, authorization-request handoff, checkout initiation and status/audit presentation.

## Directory ownership

Reference chat, tool-orchestration code, buyer adapter, MCP transport/server/schema code and their tests.

## Shared contracts consumed

`catalog.*`, `proposal.create`, `authorization.request`, `transaction.create/execute/get_status/get_audit`; stable errors, identity and idempotency conventions.

## Shared contracts exposed

Buyer- and merchant-facing MCP tool schemas only. Their semantics must be projections of application services, not alternate implementations.

## Security/trust rules

Bind actor identity and one active merchant server-side; keep buyer and merchant tool discovery disjoint; never accept identity, tenant, roles, credentials or forced states in tool input; require transport idempotency for mutations and human confirmation for publication; return only safe/redacted data.

## Required implementation tasks

1. Implement reference chat as the guaranteed end-to-end buyer path.
2. Implement narrow tool calling and buyer-safe rendering, including image metadata.
3. Implement authorization request/human approval handoff without AI self-approval.
4. Implement remote MCP discovery and one-to-one service mappings.
5. Prove compatible external MCP client interoperability without making it a demo prerequisite.
6. Expose the approved merchant catalog service through a separate merchant MCP surface after C6.
7. Prove the merchant MCP cannot mint publication confirmation or access buyer financial tools.

## Lane phases

| Phase | Scope | Exit evidence |
|---|---|---|
| C1 `phase/c1-buyer-adapter` | Buyer-safe application-service adapter and frozen-contract mocks | Identity binding, error mapping and contract-parity tests |
| C2 `phase/c2-reference-chat` | Primary chat shell, discovery, product and proposal presentation | Reference-chat component/journey tests; no MCP dependency |
| C3 `phase/c3-tool-orchestration` | Narrow intent-to-tool mapping and explicit authorization handoff | Prompt-injection, tool permission and no-self-approval tests |
| C4 `phase/c4-mcp-adapter` | Separate Remote MCP server/adapter and one-to-one schema mappings | MCP discovery/call contract tests against the same service semantics |
| C5 `phase/c5-buyer-transaction-ui` | Payment handoff, status, recovery and audit presentation | Status mapping, recovery, redaction and no-false-success tests |
| C6 `phase/c6-buyer-harness` | Buyer/chat/MCP integration harness and dependency replacement | Real-seam parity tests and separate chat/MCP traces; not the full project E2E suite |
| C7 `phase/c7-merchant-mcp-catalog` | Required merchant MCP catalog adapter with isolated discovery and human-confirmed publication | Role/tenant/tool isolation, confirmation and external merchant-client parity evidence |

Each phase branches from `feature/buyer-agent`. C2 is the guaranteed buyer demo and never waits for
C4. C4 cannot become the normal buyer UI. C6 hands the buyer fixtures to workstream 07; it does not
claim provider or full-system scenario success. C7 begins only after C6 and approved A7 seams. It is
a required release gate but does not delay the reference chat, dashboard or transaction/provider
lane.

## Required tests

Tool schemas/contracts, intent-to-tool mapping, explicit consent boundary, prompt-injection isolation,
server-derived price display, repeat call idempotency and safe errors/redaction. C7 covers disjoint
buyer/merchant discovery, missing/wrong roles, cross-tenant IDs, injected `merchant_id`, stale
versions, malformed money, forbidden extra fields, same-key replay, changed-fingerprint rejection,
concurrent mutation, confirmation validation and identical adapter/service semantics. It also proves
draft/update cannot publish implicitly and all publication calls the canonical catalog service.

## Evidence required

Reference chat recording/log, redacted buyer and merchant MCP discovery/call traces, confirmation-bound publication evidence and contract/E2E output. Financial success evidence comes from 04/07.

## Integration points

02 catalog, 03 transaction services, 06 identity/deployment, 01 shared display conventions and 07 full journey.

## Completion criteria

M6 is met: reference chat works end to end as the primary demo; buyer MCP proves catalog/proposal interoperability; merchant MCP proves human-confirmed catalog management over the same backend before release.

## Known non-goals

MCP-first demo dependency, autonomous approval, broad agent framework, recommendation/campaign engine, arbitrary tools, direct provider access and MCP-specific business logic.

## Things this agent must never do

Make external MCP availability necessary for the primary demo; approve on behalf of the buyer; calculate trusted totals; bypass merchant policy; call Razorpay; set state; reconcile; or fork application logic.

## Questions/escalation triggers

Escalate tool semantic/schema changes, identity binding, idempotency-key derivation, approval UX boundaries, image URL safety or any request to make MCP authoritative/primary.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../ARCHITECTURE.md`,
`../../API.md`, `../../SECURITY.md` and `../../EVALUATION.md`.
