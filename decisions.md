# decisions.md — Architectural and Product Decisions

Record durable decisions that future developers and AI agents must understand.

---

## D-001 — Target only the AI-buyer branch of Razorpay Track 1

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

V1 focuses on making a merchant transactable by an AI buyer end to end.

Revenue campaigns, upsell/cross-sell engines and campaign orchestration are outside v1.

### Why

The Track 1 prompt uses an OR condition. Narrowing scope allows deeper execution and stronger evidence.

### Alternatives Considered

- Build both merchant growth and AI-buyer transaction flows.
- Build a revenue-growth-only project.

### Consequences

Architecture prioritizes merchant publication, MCP access, transaction authority, Razorpay Test Mode, audit and recovery.

### Evidence / Trigger

Project scope review.

### Supersedes

None.

---

## D-002 — MCP is an adapter, not the payment authority

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

MCP tools call the same application services as HTTP/dashboard flows.

### Why

Financial rules must remain deterministic and centralized.

### Alternatives Considered

- Put business logic directly in MCP tools.

### Consequences

The MCP layer remains thin. Authorization, money, policy, transaction state and Razorpay calls remain in backend services.

### Evidence / Trigger

Architecture review.

### Supersedes

None.

---

## D-003 — Keep buyer consent and merchant acceptance as separate gates

Status: ACTIVE
Date: <fill>
Branch: <fill>
Owner: Project team

### Decision

Buyer authorization and merchant policy/manual acceptance are independent.

### Why

They answer different questions: whether the buyer may spend and whether the merchant accepts the order.

### Alternatives Considered

- One generic approval state.

### Consequences

Data model, state machine, audit and UI must preserve both decisions independently.

### Evidence / Trigger

Security and product review.

### Supersedes

None.

---

## D-004 — Use seven bounded workstreams across three execution lanes

Status: ACTIVE
Date: 2026-09-04
Branch: main
Owner: Project team

### Decision

Organize implementation into seven ownership-bounded workstreams and execute them through three
long-lived lanes: `feature/merchant-catalog`, `feature/transaction-core`, and
`feature/buyer-agent`. Freeze shared entity, application-service, provider and storage contracts
before parallel feature work.

Reference Buyer Chat remains the primary guaranteed buyer demo. Remote MCP remains a separate interoperability proof over the same application services.

### Why

A solo developer using multiple coding agents needs narrow reading scope, explicit non-ownership and stable integration seams to avoid architecture drift, merge conflicts and duplicated financial logic.

### Alternatives Considered

- Assign agents by ad hoc feature without shared ownership documents.
- Split immediately into independent microservices.
- Make the external MCP client the primary demo dependency.

### Consequences

Every agent reads the master plan and only its assigned workstream plus linked canonical contracts. Cross-workstream contract changes require integrator review. Parallel development begins only after the foundation/contracts gate.

### Evidence / Trigger

Architecture/documentation planning review and the requirement to support three simultaneous coding lanes safely.

### Supersedes

None.

---

## D-005 — Use a typed Python modular-monolith foundation

Status: ACTIVE
Date: 2026-09-04
Branch: main
Owner: Project team

### Decision

Use Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL/psycopg, Alembic, pytest, Ruff and mypy. Keep shared DTOs and service/provider/storage ports in a dependency-light `contracts` package.

### Why

This stack supports a small modular monolith, explicit validation, durable relational constraints and fast contract testing without introducing service-distribution overhead.

### Alternatives Considered

- TypeScript/Node backend.
- Multiple deployable microservices from Milestone 0.
- Untyped dictionaries as cross-workstream contracts.

### Consequences

Feature workstreams implement the frozen Protocol interfaces. PostgreSQL remains the correctness target, while migration round-trips and DDL compilation can be validated without external infrastructure.

### Evidence / Trigger

Milestone 0 implementation and passing lint, type, contract, schema and migration tests.

### Supersedes

None.

---

## D-006 — Deliver each lane through gated child phases

Status: ACTIVE
Date: 2026-09-04
Branch: main
Owner: Project team

### Decision

Treat the three feature branches as ownership and integration lanes, not single agent assignments.
Implement one bounded A/B/C phase at a time on a `phase/*` child branch. Merge a phase only into its
own lane after risk-specific tests, contract checks, lint/typecheck, self-review, independent audit
and human approval. Stop before the next phase.

### Why

Small phase boundaries make review, rollback, debugging, contract drift and evidence provenance
tractable while retaining parallel work across the three lanes.

### Alternatives Considered

- Give each agent its entire lane in one long-running task.
- Merge every phase directly to `main`.
- Create all future phase branches before their prerequisites exist.
- Defer testing until workstream 07.

### Consequences

Only the current phase branch for each lane should normally exist. Phase PRs target their lane;
lanes target `main` only at integration milestones. Each phase owns its tests, while workstream 07
audits assembled seams and project scenarios. Phase status and evidence follow
`docs/PHASE_EXECUTION.md`.

### Evidence / Trigger

Review of the operational risk created by three giant agent-owned branches, especially transaction
locking, idempotency, provider verification and reconciliation.

### Supersedes

Refines D-004; does not change its ownership boundaries.

---

## D-008 — Add merchant_id to CatalogService.get_product (A3 Contract Change)

Status: APPROVED
Date: 2026-09-04
Branch: phase/a3-catalog-publication
Owner: Human Integrator Approval

### Approval
Integrator / human approval granted:
"APPROVED — Shared Contract Change A3: Approve changing CatalogService.get_product to get_product(merchant_id: str, product_id: str, actor: ActorContext) -> ProductView. Rationale: resolves conflict between frozen contract and Invariant 19. No unscoped repository lookup may be introduced. Requirements: merchant_id is a lookup/tenant scope, not authentication. Repository lookup must remain SQL-scoped by merchant_id. Buyer reads must enforce publication/visibility rules. Merchant/private operations must verify actor-to-merchant authorization. Do not restore get_by_id_unscoped. Update the canonical contract and its contract tests. Update all current call sites and mocks/fixtures. Record the approved decision in the project decision/change documentation. Notify Workstream C that get_product now requires merchant_id. Do not make unrelated shared-contract changes."

### Decision

Update the frozen CatalogService.get_product contract to require merchant_id:
`def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView: ...`

MerchantCatalogService.get_product remains strictly unchanged as `def get_product(self, product_id: str, actor: ActorContext) -> ProductView: ...` since merchant actors possess explicit tenant context (`actor.merchant_ids`).

### Why

Invariant 19 mandates that all database queries be tenant-scoped at the SQL level (using merchant_id). Buyer contexts do not inherently possess a list of merchant_ids to iterate over, making it impossible to perform a tenant-scoped lookup using only product_id. The client must provide the merchant_id when reading a product.

### Alternatives Considered

- Using an unscoped DB query (explicitly rejected in Phase A2 review as violating SQL-level tenant isolation).
- Iterating over all merchants (unscalable and impossible).

### Consequences

Workstream C (Buyer/MCP) must supply the merchant_id when fetching a product (this data is already available via the search result). MerchantCatalogService.get_product remains unchanged as it safely scopes to the actor's authorized merchant_ids.

### Evidence / Trigger

Phase A3 escalation during implementation of buyer-safe reads. Gate approved by human integrator.

### Supersedes

None.

---

## D-009 — Execute A7 before A6 in the merchant lane

Status: ACTIVE
Date: 2026-09-04
Branch: phase/a7-merchant-mcp-readiness
Owner: Human direction, recorded by Agent A

### Decision

Execute Phase A7 (`phase/a7-merchant-mcp-readiness`) immediately after A5 and before A6
(`phase/a6-merchant-dashboard`), producing the ordering A5 → A7 → A6. All backend domain logic
(catalog idempotency, publication-confirmation issuer/verifier) is completed before the merchant
dashboard UI is built, so A6 consumes finalized, idempotent APIs.

### Why

A7 is pure backend domain logic: wrapping `create_product`, `update_product`, `publish_product`
and `unpublish_product` with durable fingerprinted idempotency on the existing
`idempotency_records` table, plus the 5-minute signed publication-confirmation token issuer and
verification seam. A6 is the frontend dashboard. Building the UI against already-frozen idempotent
services avoids rework when the confirmation handoff and idempotent semantics land.

### Alternatives Considered

- Follow the default WORKSTREAM 02 ordering (A6 then A7): rejected because the confirmation
  claims' interactive dashboard button is an A7 integration contribution that does not depend on
  A6 being built first, while A6 benefits from building against final A7 seams.

### Consequences

WORKSTREAM 02 line 80 ("A7 begins after the A6 dashboard and approved auth seam are available")
is deliberately deviated from. A6 still owns the dashboard UI for the confirmation handoff; A7
provides only the backend issuer/verifier services. MCP transport remains Workstream 05 (C7).
No frozen contracts, DTOs, enums or DB schema change.

### Evidence / Trigger

Human direction during Phase A5 review (2026-09-04): "architecturally it is actually much better
to do A7 before A6 … we can record this deliberate ordering in decisions.md and execute:
A5 → A7 → A6."

### Supersedes

Refines D-006 and D-007; does not change their ownership boundaries.
