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

## D-007 — Require isolated merchant MCP catalog interoperability

Status: ACTIVE
Date: 2026-09-04
Branch: codex/merchant-mcp-extension-plan
Owner: Project team

### Decision

V1 requires a merchant MCP catalog adapter after the buyer C4–C6 phases. Keep C4 buyer-only; add
A7 for canonical catalog idempotency and human publication-confirmation support, then C7 for the
thin merchant adapter. Expose `/mcp/buyer` and `/mcp/merchant` with disjoint registries.

Bind a merchant session server-side to one active merchant and derive `ActorContext`; tool inputs
cannot supply identity, merchant or roles. Require transport-level `Idempotency-Key` metadata for
mutations. Publishing and unpublishing additionally require a five-minute dashboard-issued HS256
confirmation bound to actor, tenant, product, version and action. The adapter verifies and strips
the token before invoking the frozen `MerchantCatalogService` command.

### Why

Two-sided interoperability strengthens the product without creating a second catalog authority or
allowing an AI credential to publish autonomously. Separating C7 preserves the buyer critical path
and the transaction/provider lane while still making merchant interoperability a release gate.

### Alternatives Considered

- Keep merchant MCP optional after v1.
- Expand buyer C4 with merchant mutations.
- Allow authenticated MCP mutation alone to publish.
- Put merchant identity or idempotency keys in business tool schemas.
- Limit merchant MCP to drafts with no publication path.

### Consequences

Workstreams 01, 02 and 06 contribute A7 seams; Workstream 05 owns C7 transport and schema mapping;
Workstream 07 adds J16 and release evidence. Buyer and merchant discovery remain isolated. The M0
service interfaces and database schema remain frozen.

### Evidence / Trigger

Human-approved Required Merchant MCP Extension plan dated 2026-09-04. Runtime evidence remains
`NOT RUN` until A7/C7 and J16 execute.

### Supersedes

Extends D-002 and D-004 without replacing them.

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
## D-009 � Create Razorpay Test Mode orders once without adapter retries

Status: ACTIVE
Date: 2026-09-04
Branch: phase/b4-razorpay-adapter
Owner: Workstream 04 / Agent B

### Decision

Implement `provider.create_order` as one direct authenticated Razorpay REST request with automatic
retries disabled. Accept only `rzp_test_*` credentials and the approved HTTPS API host. Validate the
entire initial order identity, amount, currency, receipt, state and counters before persisting its
normalized observation. A `created` order maps only to `PAYMENT_PENDING`.

Construct Standard Checkout options from the public key ID, trusted amount/currency and stored
provider order ID. Never expose the key secret. Keep checkout verification, webhooks and lookup out
of B4.

### Why

A timeout may occur after Razorpay creates an order but before the response reaches the platform.
An SDK or transport retry at this boundary could create a second physical order outside the B3
durable one-attempt guard. Strict response matching also prevents provider drift or mismatched
money from being accepted as local truth.

### Alternatives Considered

- Enable the official SDK's retry option.
- Retry only timeout or server responses inside the adapter.
- Treat any HTTP 2xx body containing an order ID as sufficient.
- Treat order creation as payment success.

### Consequences

Provider exceptions after B3's pre-dispatch commit follow the existing conservative `UNKNOWN`
path and require later reconciliation. Test Mode credentials and secrets are server-only. B5 must
independently establish checkout/payment authenticity and captured-payment success.

### Evidence / Trigger

Official Razorpay Orders and Standard Checkout documentation, B3's unknown-no-blind-retry
invariant, B4 mock-transport/transaction-seam tests and real Test Mode run
`B4-RZP-20260904-01`.

### Supersedes

None.

---

## D-010 � Centralize typed developer configuration in YAML

Status: ACTIVE
Date: 2026-09-04
Branch: feature/transaction-core
Owner: Project team / Workstream 06

### Decision

Use `config/default.yaml` for the safe complete configuration shape and ignored
`config/local.yaml` for developer overrides. Allow `APP_CONFIG_FILE` to select a deployment YAML
overlay. Validate YAML through typed `Settings`, reject unknown fields and wrap secrets in
`SecretStr`. Existing flat environment variables remain higher-priority deployment and
secret-manager overrides; feature code must not read them directly.

### Why

Database connections, LLM selections, provider credentials and other inputs need one discoverable,
validated location without scattering developer setup through source code and shell state.

### Alternatives Considered

- Retain `.env` as the primary developer interface.
- Permit arbitrary untyped YAML values.
- Commit environment-specific files containing credentials.

### Consequences

New runtime inputs require a typed setting, YAML mapping, safe default/example and tests. B5 adds
the distinct Razorpay webhook secret through this path. Existing B1–B4 consumers and CI environment
overrides remain compatible.

### Evidence / Trigger

User-approved configuration requirement and automated overlay, validation, redaction and B4
compatibility tests.

### Supersedes

Refines the environment-template portion of D-005; no frozen commerce or persistence contract is
changed.

---

## D-011 � Require five independent conditions for platform SUCCEEDED

Status: ACTIVE
Date: 2026-09-04
Branch: phase/b5-provider-verification
Owner: Workstream 04 / Agent B

### Decision

Platform `SUCCEEDED` requires all of: (1) valid checkout HMAC or webhook HMAC authenticity;
(2) provider payment and order IDs correlated to the stored attempt; (3) payment state `captured`
with `captured: true` from an independent lookup; (4) order state `paid` with zero amount due from
an independent lookup; and (5) provider amount and currency matching the immutable transaction.

Neither a created order, an authorized payment, a failed payment, a valid signature alone, nor a
mismatched amount can produce SUCCEEDED.

### Why

Order creation is not payment. Checkout signatures prove message integrity, not payment capture.
Only an independent provider lookup can confirm the actual financial state. Amount verification
prevents partial-payment or currency-mismatch acceptance.

### Alternatives Considered

- Accept signature validity alone as success.
- Accept any non-failed payment state as success.
- Skip independent lookup and trust webhook payload.
- Allow checkout callback without amount verification.

### Consequences

The verification service always performs two independent lookups (payment + order) before
transitioning to SUCCEEDED. This adds latency but prevents accepting unverified or inconsistent
provider states as platform truth.

### Evidence / Trigger

B5 integration tests prove the two-step transition (PAYMENT_PENDING → VERIFYING → SUCCEEDED) and
that each insufficient condition blocks success. Official Razorpay documentation for Standard
Checkout verification and payment capture states.

### Supersedes

Resolves the open question in technical-questions.md about the exact SUCCEEDED condition.

---

## D-012 � Merchant AI-assisted catalog creation in A6

Status: ACTIVE
Date: 2026-09-04
Branch: main (docs commit 928409f)
Owner: Project team

### Decision

Phase A6 includes an AI-assisted catalog creation flow: 'Add with AI' is the primary merchant path
for product creation. The extraction endpoint (POST /merchants/{id}/products/extract-draft) returns
a proposed ProductDraft only � it never persists; the human merchant reviews, edits, saves the
draft, and publishes through the normal confirmation flow.

### Why

AI-assisted catalog creation demonstrates the merchant side of agentic commerce while keeping the
AI propose-only: it cannot set trusted price, stock, currency, or publication state on its own.

### Alternatives Considered

- Manual form only.
- Let the AI write directly to the catalog (rejected: no trusted-field mutation by AI).

### Consequences

The workstream 01 references to 'D-010' now point here (renumbered during the three-lane merge to
avoid collision with transaction-lane decision numbering).

### Evidence / Trigger

Docs commit 928409f added the A6 scope; the merge into an integrated ledger required a unique ID.

### Supersedes

None.

