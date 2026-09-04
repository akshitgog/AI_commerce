# Workstream 01 — Merchant Experience

## Mission

Give a nontechnical merchant a thin, understandable interface for publishing products, configuring acceptance policy, reviewing orders and seeing financial audit status.

## Why this workstream exists

The dashboard is a human interface over shared application services. Keeping it separate prevents UI convenience logic from becoming a second transaction engine.

## Ownership

- Merchant login/session user experience.
- Product list/create/edit screens, 1–3 image upload UX, price/stock fields and publish/unpublish actions.
- Merchant policy editor and manual-review queue.
- Orders view, simplified status labels and audit timeline presentation.
- Client validation, accessibility and loading/error states.
- Explicit human publication confirmation/step-up handoff for merchant MCP publication.

## Explicit non-ownership

No financial state transitions, trusted price calculations, buyer authorization, merchant-policy algorithm, durable idempotency, confirmation-token cryptography, Razorpay calls, provider verification or reconciliation.

## Inputs / dependencies

Frozen merchant/catalog/policy/review/transaction-read APIs; auth context from 06; catalog services from 02; audit/read models from 03/04. It may develop against contract mocks after M0.

## Outputs / exposed contracts

UI components and routes only. It exposes no trusted financial service. Any generated client types must remain derived from canonical API contracts.

## Relevant domain entities

Consumes views of `Merchant`, `MerchantUser`, `Product`, `ProductMetadata`, `ProductImage`, `MerchantPolicy`, `MerchantDecision`, `Transaction` and `TransactionEvent`. It owns no table.

## Relevant database tables

Reads the corresponding catalog, policy, transaction and event tables only through application services; owns no migration or repository.

## Relevant API/application services

Merchant product CRUD/publish routes, dashboard-only publication-confirmation route, image upload/delete routes, policy read/update, review list/decision, transaction status and audit reads.

## Relevant UI surfaces

Merchant sign-in, catalog manager, product editor, image picker/gallery, policy form, review queue, order detail and audit timeline.

## Directory ownership

Merchant dashboard/client directories and their component tests. Shared generated contracts may change only through the contract-change process.

## Shared contracts consumed

`catalog.*`, merchant policy/manual decision services, storage upload responses, transaction status/audit read models, stable error envelope and UI-state mapping.

## Shared contracts exposed

None across trust boundaries. UI callbacks are internal to the dashboard package.

## Security/trust rules

Never trust route merchant IDs without server enforcement. Never accept/display secrets. Treat descriptions and image metadata as untrusted content. Never infer financial success from checkout return or UI state.

## Required implementation tasks

1. Build merchant session shell and guarded navigation.
2. Build catalog CRUD, price/stock and publication flows.
3. Build ordered 1–3 image upload/delete experience with validation feedback.
4. Build policy configuration and manual-review decision screens.
5. Build orders and audit views using simplified labels without collapsing backend states.
6. In A7, add the explicit human confirmation/step-up handoff that requests a short-lived
   publication token without exposing that token to logs or persistent client storage.

## Lane phase ownership

This workstream is delivered primarily in `phase/a6-merchant-dashboard`, based on
`feature/merchant-catalog`. UI shells or contract mocks may be prepared earlier only when explicitly
included in the active phase scope. A6 must integrate the completed A2–A5 seams and must not repair
missing backend behavior in UI code.

A6 exits only when component/contract tests, accessibility states, merchant-scope handling and the
M1 dashboard journey pass review. Stop at `READY_FOR_REVIEW`; do not start buyer or transaction UI
work outside the approved phase.

The narrow confirmation handoff is an A7 integration contribution after A6; it does not reopen the
dashboard phase or move catalog idempotency/token verification into UI code.

## Required tests

Component tests for validation/status/error states; integration tests against mocked frozen contracts; role/tenant denial presentation; upload limits; publish/unpublish; policy modes; manual review; canonical-to-display status mapping.

## Evidence required

Test output and screenshots/recording for the merchant journey. Financial claims require backend evidence from workstream 07, not screenshots alone.

## Integration points

02 catalog, 03 policy/transaction/audit, 04 provider-phase read model, 06 auth/storage and 07 E2E.

## Completion criteria

The merchant can perform the M1 flow and later review M2–M4 outcomes through frozen APIs, with tests and accessible failure states.

## Known non-goals

Marketplace discovery, campaigns, analytics suites, complex media processing and provider administration.

## Things this agent must never do

Call Razorpay, compute authoritative totals, approve for the buyer, bypass policy, mutate transaction state locally, or mark tests passed from UI appearance.

## Questions/escalation triggers

Escalate API/schema changes, new status mappings, auth-role changes, storage URL semantics or any UI need that appears to require financial logic.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../API.md`,
`../../DATA_MODEL.md` and `../../SECURITY.md`.
