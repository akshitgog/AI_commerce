# progress.md — Development History

This file is append-only.

Do not record planned work as completed work.

---

## Entry 000 — Project memory initialized

Date/time:       <fill when repository is initialized>
Git branch:      <exact branch>
Commit:          <short hash if available>
Author/Agent:    <name/agent>
Workstream:      docs
Change:          Added development-memory framework
Files/modules:   AGENT.md, flow.md, progress.md, technical-questions.md, decisions.md

### What Changed

Created the project memory files used by human developers and AI agents.

### Reason

Preserve current architecture, historical changes, unresolved questions, decisions and evidence throughout implementation.

### Technical Impact

No runtime behavior changed.

### Validation

Confirmed the files exist and are readable.

### Evidence

Repository files.

### Result

SUCCESS

### Problems / Limitations

Runtime implementation has not been recorded yet.

### Next Step

Begin Phase 0 Razorpay Test Mode provider spike.

---

## Entry 001 — Parallel workstream documentation created

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      main
Commit:          951ba00
Author/Agent:    Codex architecture/documentation agent
Workstream:      docs
Change:          Added master execution plan, seven bounded workstream briefs and aligned canonical interface contracts
Files/modules:   AGENT.md, decisions.md, progress.md, technical-questions.md, docs/MASTER_DEVELOPMENT_PLAN.md, docs/workstreams/, docs/README.md, docs/DOCS_INDEX.md, docs/EVALUATION.md, docs/IMPLEMENTATION_PLAN.md, docs/API.md, docs/DATA_MODEL.md, docs/TESTED.md

### What Changed

Created a contract-first execution system for three parallel coding lanes. Corrected existing MCP-first wording so the reference buyer chat is consistently the primary guaranteed demo and MCP is a separate interoperability adapter. Added the bounded `ProductImage` and storage contracts required by the plan.

### Reason

Reduce agent reading scope, prevent overlapping ownership and preserve the single financial authority during parallel implementation.

### Technical Impact

Documentation/contracts only. No runtime code or implemented system state changed.

### Validation

Checked document links, required workstream headings, transaction-state terminology, scenario ledger counts and buyer-chat/MCP wording. No runtime tests were run because no runtime implementation exists.

### Evidence

Repository diff and documentation validation commands on branch `main`.

### Result

SUCCESS

### Problems / Limitations

Razorpay success evidence, image URL policy and MCP idempotency-key derivation remain open. All runtime scenarios remain `NOT RUN`.

### Next Step

Freeze M0 shared contracts, then start the provider truth spike and three bounded implementation lanes.

---

## Entry 002 — Milestone 0 foundation implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      main
Commit:          951ba00
Author/Agent:    Codex
Workstream:      06-data-infrastructure / shared contracts
Change:          Implemented repository layout, database connection, migration framework, canonical schemas, contracts, interfaces, errors, tests and environment template
Files/modules:   pyproject.toml, uv.lock, .env.example, docker-compose.yml, alembic.ini, migrations/, src/ai_commerce_gateway/, tests/, docs/DEVELOPMENT.md, flow.md

### What Changed

Created the typed Python modular-monolith foundation. Added all 15 canonical SQLAlchemy tables and initial Alembic migration; frozen Pydantic DTOs and Protocol ports; stable application/validation error envelopes; opaque ID generation; FastAPI liveness/readiness; environment and PostgreSQL templates; and unit, contract and integration test layers.

Moved the previously created workstream briefs into the required `docs/workstreams/` location.

### Reason

Satisfy Milestone 0 and provide safe seams for the three implementation lanes before feature work begins.

### Technical Impact

Foundation only. No merchant, catalog, transaction, Razorpay, buyer-chat or MCP feature behavior was implemented.

### Validation

`uv run ruff check .` passed. `uv run mypy` passed. `uv run pytest --cov=ai_commerce_gateway --cov-report=term-missing` passed 13 tests with 97% package coverage; one live PostgreSQL connection test skipped because `TEST_DATABASE_URL` was not configured. Alembic upgrade/downgrade passed against a temporary database, and offline PostgreSQL migration SQL generation succeeded.

### Evidence

Local command output on branch `main`; migration revision `2a8a78d61842`.

### Result

SUCCESS WITH EXTERNAL-DB CHECK NOT RUN

### Problems / Limitations

No PostgreSQL service was available for a live connection test. Existing Razorpay, storage URL and MCP idempotency questions remain unresolved.

### Next Step

Run the provider-truth spike or begin the bounded Milestone 1 merchant/catalog lane using the frozen contracts.

---

## Entry 003 — Milestone 0 frozen and buyer-path documentation normalized

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      main
Commit:          9c32855
Author/Agent:    Codex
Workstream:      docs / foundation review
Change:          Recorded the successful PostgreSQL gate and removed residual MCP-first ambiguity
Files/modules:   AGENT.md, flow.md, progress.md, docs/PRD.md, docs/EVALUATION.md, docs/MASTER_DEVELOPMENT_PLAN.md, docs/TESTED.md

### What Changed

Recorded successful GitHub Actions run `33817667540` for M0 commit `1640869` and the resulting
`m0-foundation` freeze. Clarified that Reference Buyer Chat is the primary buyer journey and that
Remote MCP is a separate interoperability proof over the same application services.

### Reason

Prevent future development agents from interpreting older combined buyer/MCP wording as an
MCP-first product or demo architecture.

### Technical Impact

Documentation only. No implementation, contracts, schema or runtime behavior changed.

### Validation

Searched canonical and living documentation for MCP-first buyer/demo language and reviewed the
resulting documentation diff. Remaining MCP-first phrases are explicit prohibitions or non-goals.

### Evidence

GitHub Actions run `33817667540`; tag `m0-foundation`; repository documentation diff.

### Result

SUCCESS

### Problems / Limitations

Provider behavior and the exact mutating-MCP idempotency strategy remain intentionally provisional.

### Next Step

Start feature work only within the frozen workstream boundaries.

---

## Entry 004 — Gated child-phase execution model documented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      main
Commit:          commit containing this entry
Author/Agent:    Codex
Workstream:      docs / execution governance
Change:          Split three long-lived lanes into bounded A/B/C child phases with hard review gates
Files/modules:   AGENT.md, decisions.md, progress.md, docs/PHASE_EXECUTION.md, docs/DOCS_INDEX.md, docs/MASTER_DEVELOPMENT_PLAN.md, docs/IMPLEMENTATION_PLAN.md, docs/workstreams/*/WORKSTREAM.md

### What Changed

Defined the existing `feature/*` branches as long-lived ownership lanes and added A1–A6, B1–B6 and
C1–C6 child phases. Added phase statuses, branch direction, required prompt shape, risk-specific
tests, self-review, independent audit, human approval and a reusable evidence record. Updated every
workstream with its phase ownership or integration role.

### Reason

Prevent large agent runs from erasing review boundaries and make rollback, debugging and evidence
attribution practical without giving up three-lane parallelism.

### Technical Impact

Documentation and development process only. No runtime implementation, frozen contract, schema or
branch reference changed.

### Validation

Cross-checked phase IDs, branch names, workstream ownership, testing responsibility, integration
direction and Reference Buyer Chat/MCP boundaries across canonical and living documentation.

### Evidence

Repository documentation diff and relationship search.

### Result

SUCCESS

### Problems / Limitations

No phase branches were created. Human approval is still required before starting the first phase in
each lane.

### Next Step

Choose the first active phase per lane and create only those three child branches from their current
lane heads.

---

## Entry 005 — Transaction state machine and atomic audit foundation implemented

Date/time:       2026-09-04 11:35 IST
Git branch:      phase/b1-transaction-domain
Commit:          uncommitted working tree
Author/Agent:    Codex Agent B
Workstream:      transaction
Change:          Added the provider-independent transaction transition validator and atomic causal event persistence
Files/modules:   domain/transactions.py, infrastructure/database/transactions.py, transaction state/event tests

### What Changed

Added an immutable transaction aggregate that uses the frozen canonical `TransactionState` enum,
defines the exact allowed transition graph and produces a structured causal event for every valid
state change. Added an internal SQLAlchemy state repository that flushes the state update and event
append together inside the caller's database transaction.

The B1 scope follows the repository phase plan: proposal hashing, buyer authorization, merchant
policy/decision and readiness application behavior remain deferred to B2.

### Reason

Establish deterministic, provider-independent state and audit semantics before proposal-gate
application services, idempotent provider orchestration or Razorpay integration are added.

### Technical Impact

Canonical transitions are centrally validated; terminal states cannot transition; `SUCCEEDED` is
reachable only from `VERIFYING` or `RECONCILING`; and cancellation/expiry are limited to states
before provider dispatch. Frozen DTOs, service/provider/storage ports, persistence schema, money
conventions, errors and identifier conventions were not changed.

### Validation

`uv run ruff check .` passed. `uv run mypy` passed. `uv run pytest
--cov=ai_commerce_gateway` passed 259 tests with 98% package coverage; two PostgreSQL tests skipped
because `TEST_DATABASE_URL` was not configured. `uv run alembic upgrade head --sql` passed. A
targeted coverage run reported 100% for the new transaction domain module and 98% for its database
repository.

### Evidence

Local command output on branch `phase/b1-transaction-domain`. The portable database test proves
that a deliberately failed event insert rolls back the accompanying state update.

### Result

SUCCESS

### Problems / Limitations

The PostgreSQL-specific transaction/event atomicity test was not run locally because
`TEST_DATABASE_URL` is unset. B1 intentionally contains no proposal, authorization, merchant-gate,
readiness, idempotency, locking, provider, reconciliation-worker or interface implementation.

### Next Step

Submit B1 for independent audit and human review. Do not begin B2 before approval and merge into
`feature/transaction-core`.

---

## Entry 006 — Proposal and independent gate application services implemented

Date/time:       2026-09-04 12:12 IST
Git branch:      phase/b2-proposal-gates
Commit:          uncommitted working tree; based on approved B1 merge d0a7342
Author/Agent:    Codex Agent B
Workstream:      transaction
Change:          Implemented immutable proposals, bounded buyer authorization, merchant policy/manual decisions and READY transaction creation
Files/modules:   domain/proposal_gates.py, application/proposal_gates.py, infrastructure/database/proposal_gates.py, proposal/gate tests

### What Changed

Added canonical hashing and immutable commercial snapshots derived only from persisted product
price, version, currency and stock. Added bounded authorization request/approval logic with a
required human-approval verifier, exact proposal matching and fail-closed expiry behavior. Added
deterministic merchant policy evaluation, authenticated manual review and current-policy-version
checks. Added readiness revalidation and creation/reuse of a `READY` transaction with its causal
creation event.

B1 was committed as `034fb42`, approved into `feature/transaction-core` as merge `d0a7342`, and B2
was created from that lane head.

### Reason

Complete the B2 proposal and independent-gates phase while keeping financial authority in the
domain/application layers and preserving the frozen Milestone 0 contracts.

### Technical Impact

Buyer consent and merchant acceptance are independent. AI-facing callers cannot approve because
authorization approval requires an injected verifier for a human-controlled surface. Product or
policy drift prevents readiness. Transaction creation emits an initial structured event but does
not execute, lock, create an idempotency record or create a provider attempt.

### Validation

`uv run ruff check .` passed. `uv run mypy` passed. `uv run pytest
--cov=ai_commerce_gateway` passed 327 tests with 97% package coverage; three PostgreSQL-dependent
tests skipped because `TEST_DATABASE_URL` was not configured. The new proposal/gate domain module
reported 99% coverage. `uv run alembic upgrade head --sql` passed.

### Evidence

Local command output on `phase/b2-proposal-gates`. Unit tests cover stable hash and scope mismatch
rules. Database-backed tests cover automatic allow, manual review, AI approval denial, tenant
isolation, current product/policy drift and causal `READY` transaction creation without a payment
attempt. A PostgreSQL version of the proposal/gate flow is present and skips when the test URL is
unavailable.

### Result

SUCCESS

### Problems / Limitations

Durable idempotency-key/fingerprint behavior and execution locking remain B3. The concrete
human-approval authentication adapter remains owned by the later buyer-facing phase; B2 requires
that verifier and has no permissive fallback. PostgreSQL-specific B2 evidence was not run locally
because `TEST_DATABASE_URL` is unset. No HTTP, chat, MCP, provider or UI behavior was added.

Independent review accepted the B2 implementation with minor follow-up notes for B3: the
authorization-request reuse is soft deduplication rather than durable idempotency; concurrent
decision ordering and latest-record selection must be rechecked under transaction locks. Optional
negative tests for approval-before-request and policy change during manual review were noted but
were not required for the B2 gate.

### Next Step

Submit B2 for independent audit and human review. Do not begin B3 before approval and merge into
`feature/transaction-core`.

---

## Entry 007 — Durable transaction execution boundary implemented

Date/time:       2026-09-04 12:53 IST
Git branch:      phase/b3-idempotency-locking
Commit:          uncommitted working tree; based on approved B2 merge 10bbf50
Author/Agent:    Codex Agent B
Workstream:      transaction
Change:          Implemented durable execution idempotency, transaction locking and one-attempt provider orchestration
Files/modules:   domain/execution.py, application/transaction_execution.py, infrastructure/database/execution.py, execution tests

### What Changed

Added canonical execution and provider-request fingerprints, a durable idempotency-record domain
projection, and a payment-attempt snapshot consumed by transaction orchestration. Added an
execution application service that requires the owning buyer, atomically claims the scoped
idempotency key, locks and revalidates the `READY` transaction and both gates, creates attempt 1,
and commits `EXECUTING` before invoking the provisional provider port. A provider order response
can advance only to `PAYMENT_PENDING`; an exception or incomplete observation records `UNKNOWN`
and blocks redispatch.

Added a SQLAlchemy unit of work and repository using PostgreSQL/SQLite conflict-safe inserts for
the frozen `(actor_id, operation, idempotency_key)` uniqueness scope and `SELECT ... FOR UPDATE`
for the logical transaction. Targeted rollback tests exposed that a nested-savepoint claim could
escape an outer rollback under SQLite's legacy transaction behavior, so that approach was removed
and replaced with dialect-native `ON CONFLICT DO NOTHING ... RETURNING`.

B2 was committed as `905808b` and approved into `feature/transaction-core` as merge `10bbf50`
before this phase branch was created.

### Reason

Complete B3's restart-safe boundary so repeat, concurrent and ambiguous executions cannot create a
second physical provider order, while stopping before any Razorpay-specific implementation,
verification, webhook handling or reconciliation.

### Technical Impact

Execution now persists the idempotency claim, payment attempt, `READY -> EXECUTING` transition and
causal audit event in one database commit before external dispatch. The application re-reads the
exact proposal, authorization, merchant decision/current policy and published product snapshot
under the transaction lock. Same-key/same-fingerprint calls replay the bound transaction;
same-key/different-fingerprint calls fail with `IDEMPOTENCY_KEY_REUSED`. Independent keys for the
same transaction observe the committed non-`READY` state and do not dispatch. Provider references
are stored on the attempt and only a redacted suffix enters audit events.

No frozen DTO, service protocol, enum, ORM model or migration changed. B3 consumes the explicitly
provisional `ProviderService.create_order` seam through a fake in tests; it does not implement a
provider adapter or claim provider truth.

### Validation

`uv run ruff check .` passed. `uv run mypy` passed with no issues in 28 source files. `uv run
pytest tests/unit/test_execution.py tests/integration/test_transaction_execution.py -q` passed 14
tests with one PostgreSQL test skipped because `TEST_DATABASE_URL` is unset. The concurrency-focused
portable suite also passed five consecutive runs before the final full validation. `uv run pytest
--cov=ai_commerce_gateway --cov-report=term-missing` passed 341 tests with four skips and 96% total
coverage; the new execution application, domain and repository modules reported 91%, 98% and 94%
coverage respectively. `uv run alembic upgrade head --sql` passed. Frozen contract, enum, ORM-model
and migration paths have no diff.

### Evidence

Database-backed provider-fake tests prove that `EXECUTING`, the idempotency binding and exactly one
attempt are committed before the provider call. Tests cover stable/different fingerprints,
same-key replay, simultaneous database claim contention, overlapping independent keys, restart
after a simulated process death, timeout and incomplete-observation `UNKNOWN` behavior, no blind
retry, gate/product/policy drift rollback, tenant isolation, audit redaction and the rule that
provider order creation is only `PAYMENT_PENDING`. An isolated PostgreSQL concurrency test is
present and automatically runs when `TEST_DATABASE_URL` is configured.

### Result

SUCCESS — B3 READY_FOR_REVIEW

### Problems / Limitations

The PostgreSQL-specific contention test was not run locally because `TEST_DATABASE_URL` is unset;
portable SQLite tests exercise durable uniqueness and overlapping calls, but SQLite does not apply
row-level `FOR UPDATE` semantics. No actual Razorpay call, checkout response, signature, webhook,
provider lookup or `UNKNOWN -> RECONCILING` implementation exists in B3. Those remain provider
workstream phases and require Test Mode evidence. A process death after the pre-dispatch commit
intentionally leaves `EXECUTING`; B3 will not guess or redispatch, and later reconciliation must
resolve it from provider truth.

Independent review accepted B3 with `PASS WITH MINOR ISSUES`. The reviewer confirmed the durable
conflict-safe claim, row-lock query, pre-dispatch commit, one-live-attempt, restart safety and
unknown-no-blind-retry behavior. Follow-up notes for later phases are that a fresh key on an
already-`UNKNOWN` transaction currently returns a 200 response carrying `UNKNOWN`, several
defensive revalidation branches remain indirectly covered, and the PostgreSQL row-lock test still
requires a configured test database. None was classified as a B3 defect.

### Next Step

Submit B3 for independent audit and human review. Do not commit/merge it or begin provider phase B4
until the phase gate is accepted.

---

## Entry 008 — Razorpay order and checkout-initiation adapter implemented

Date/time:       2026-09-04 16:13 IST
Git branch:      phase/b4-razorpay-adapter
Commit:          uncommitted working tree; based on approved B3 merge 1a17c78
Author/Agent:    Codex Agent B
Workstream:      provider
Change:          Implemented one-shot Test Mode order creation and secret-free checkout options
Files/modules:   providers/razorpay.py, provider config, B4 tests and Razorpay documentation

### What Changed

Added a synchronous Razorpay Test Mode adapter using direct HTTP Basic authentication. It sends one
Orders API request with trusted minor-unit money, receipt, disabled partial payment and correlation
notes. It performs no automatic retry and strictly validates the returned order identity, money,
receipt, initial `created` state, zero paid amount and zero attempts before normalizing evidence.

Added safe Standard Checkout options containing the public Test Mode key ID, trusted amount/currency,
provider order ID and display text. The key secret never enters checkout output. Live keys and
non-approved API hosts fail closed. B5 verification/webhook/lookup methods remain explicit
`NotImplementedError` boundaries.

### Reason

Complete B4's concrete order/checkout boundary without treating order creation as payment, enabling
blind transport retries or pulling B5/B6 behavior into this phase.

### Technical Impact

`TransactionExecutionApplicationService` can now use the concrete Razorpay adapter through the
existing provider Protocol. A valid created order persists provider order evidence and reaches only
`PAYMENT_PENDING`; it carries no payment/capture truth. Provider exceptions continue through B3's
durable `UNKNOWN` path. The provider method signatures, frozen application DTOs/enums, ORM schema
and migration remain unchanged. `httpx` moved from development-only to runtime dependencies.

### Validation

`uv run ruff check .` passed. `uv run mypy` passed with no issues in 29 source files. The
credentialed `uv run pytest --cov=ai_commerce_gateway --cov-report=term-missing` passed 373 tests,
skipped four PostgreSQL checks and reported 97% total coverage; `providers/razorpay.py` reported 98%.
`uv run alembic upgrade head --sql` passed. The dedicated real-provider command passed.

### Evidence

Thirty adapter tests and one concrete-adapter/B3 database seam test cover exact request mapping,
Basic auth, Test Mode-only configuration, no retry after API/transport failure, malformed and
mismatched responses, secret-free checkout options, explicit B5 boundaries, attempt persistence and
order-not-success behavior. Real Test Mode run `B4-RZP-20260904-01` created a redacted order ending
`...JzsC44` in `created` state with no payment/capture truth. See `docs/RAZORPAY_TEST_MODE.md`.

### Result

SUCCESS — B4 READY_FOR_REVIEW

### Problems / Limitations

PostgreSQL-specific tests skipped because `TEST_DATABASE_URL` is unset. Checkout signature
verification, webhooks and lookup are intentionally B5; reconciliation remains B6. J05 remains
`NOT RUN` because B4 proves order creation, not completed payment verification.

### Next Step

Commit B4, perform independent audit and request human approval. Do not begin B5.
