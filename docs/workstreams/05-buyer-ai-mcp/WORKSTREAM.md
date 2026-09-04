# Workstream 05 — Buyer AI + MCP

## Mission

Deliver the primary reference buyer-chat journey and a separate MCP interoperability proof, both through thin adapters over identical application services.

## Why this workstream exists

The reference chat guarantees a judgeable buyer demo without depending on an external MCP host. MCP proves that compatible external AI applications can reuse the same commerce capabilities.

## Ownership

Reference Buyer Chat; AI/tool orchestration; buyer-facing adapter; remote MCP server/adapter; MCP schemas/mapping; external MCP compatibility demo.

## Explicit non-ownership

Trusted price/total, buyer approval, merchant policy, transaction transitions, Razorpay calls, payment truth, idempotency storage or reconciliation logic.

## Inputs / dependencies

Frozen catalog/proposal/authorization/transaction service contracts from 02/03; auth binding from 06; provider behavior only through transaction services. Use mocks until services are available.

## Outputs / exposed contracts

Buyer chat UX and canonical tools: `search_catalog`, `get_product`, `create_purchase_proposal`, `request_authorization`, `execute_transaction`, `get_transaction_status`, `get_transaction_audit`.

## Relevant domain entities

Consumes safe views of `Product`, `ProductImage`, `PurchaseProposal`, `BuyerAuthorization`, `Transaction`, `TransactionEvent`. Owns no financial table.

## Relevant database tables

No owned tables. All persistence is reached through shared application services; tool/session telemetry must not become financial authority.

## Relevant API/application services

Maps each buyer tool one-to-one to the shared services in `API.md`. Human buyer approval remains a separate buyer-controlled surface.

## Relevant UI surfaces

Reference buyer chat, product cards/images, proposal confirmation, authorization-request handoff, checkout initiation and status/audit presentation.

## Directory ownership

Reference chat, tool-orchestration code, buyer adapter, MCP transport/server/schema code and their tests.

## Shared contracts consumed

`catalog.*`, `proposal.create`, `authorization.request`, `transaction.create/execute/get_status/get_audit`; stable errors, identity and idempotency conventions.

## Shared contracts exposed

MCP schemas and buyer-facing tool schemas only. Their semantics must be projections of application services, not alternate implementations.

## Security/trust rules

Bind actor identity server-side; never accept trusted prices, credentials or forced states; sanitize/catalog content as untrusted; require explicit buyer-controlled approval; preserve idempotency; return only redacted audit/provider data.

## Required implementation tasks

1. Implement reference chat as the guaranteed end-to-end buyer path.
2. Implement narrow tool calling and buyer-safe rendering, including image metadata.
3. Implement authorization request/human approval handoff without AI self-approval.
4. Implement remote MCP discovery and one-to-one service mappings.
5. Prove compatible external MCP client interoperability without making it a demo prerequisite.

## Lane phases

| Phase | Scope | Exit evidence |
|---|---|---|
| C1 `phase/c1-buyer-adapter` | Buyer-safe application-service adapter and frozen-contract mocks | Identity binding, error mapping and contract-parity tests |
| C2 `phase/c2-reference-chat` | Primary chat shell, discovery, product and proposal presentation | Reference-chat component/journey tests; no MCP dependency |
| C3 `phase/c3-tool-orchestration` | Narrow intent-to-tool mapping and explicit authorization handoff | Prompt-injection, tool permission and no-self-approval tests |
| C4 `phase/c4-mcp-adapter` | Separate Remote MCP server/adapter and one-to-one schema mappings | MCP discovery/call contract tests against the same service semantics |
| C5 `phase/c5-buyer-transaction-ui` | Payment handoff, status, recovery and audit presentation | Status mapping, recovery, redaction and no-false-success tests |
| C6 `phase/c6-buyer-harness` | Buyer/chat/MCP integration harness and dependency replacement | Real-seam parity tests and separate chat/MCP traces; not the full project E2E suite |

Each phase branches from `feature/buyer-agent`. C2 is the guaranteed buyer demo and never waits for
C4. C4 cannot become the normal buyer UI. C6 hands assembled fixtures to workstream 07; it does not
claim provider or full-system scenario success.

## Required tests

Tool schemas/contracts, intent-to-tool mapping, explicit consent boundary, prompt-injection isolation, server-derived price display, repeat call idempotency, safe errors/redaction, identical chat/MCP service semantics and external MCP discovery/proposal scenario.

## Evidence required

Reference chat recording/log, tool traces with redaction, MCP client discovery/call trace and contract/E2E output. Financial success evidence comes from 04/07.

## Integration points

02 catalog, 03 transaction services, 06 identity/deployment, 01 shared display conventions and 07 full journey.

## Completion criteria

M6 is met: reference chat works end to end as the primary demo; MCP independently proves catalog/proposal interoperability over the same backend.

## Known non-goals

MCP-first demo dependency, autonomous approval, broad agent framework, recommendation/campaign engine, arbitrary tools, direct provider access and MCP-specific business logic.

## Things this agent must never do

Make external MCP availability necessary for the primary demo; approve on behalf of the buyer; calculate trusted totals; bypass merchant policy; call Razorpay; set state; reconcile; or fork application logic.

## Questions/escalation triggers

Escalate tool semantic/schema changes, identity binding, idempotency-key derivation, approval UX boundaries, image URL safety or any request to make MCP authoritative/primary.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../ARCHITECTURE.md`,
`../../API.md`, `../../SECURITY.md` and `../../EVALUATION.md`.
