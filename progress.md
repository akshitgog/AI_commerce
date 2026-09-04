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

## Entry 005 — Phase C1 Buyer Application Adapter Implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      feature/buyer-agent
Commit:          PENDING
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented BuyerAdapter over M0 application-service contracts
Files/modules:   src/ai_commerce_gateway/application/buyer_adapter/

### What Changed

Implemented the thin buyer-side application/tool adapter foundation. Created narrow typed buyer-facing request/response schemas, safe error mapping, tools schemas, and contract tests using fakes.

### Reason

Satisfy Phase C1 requirements to prepare for C2 Reference Buyer Chat.

### Technical Impact

No direct provider calls or financial logic. Idempotency key and correlation ID propagation is supported via an InvocationContext.

### Validation

Passed ruff, mypy, and pytest with 94% coverage.

### Evidence

Repository files.

### Result

SUCCESS

### Problems / Limitations

None.

### Next Step

Phase C2.

---

## Entry 006 — Phase C2 Reference Buyer Chat HTTP Transport Implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      phase/c2-reference-chat
Commit:          PENDING
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented FastAPI HTTP router for the 7 canonical buyer tool operations.
Files/modules:   src/ai_commerce_gateway/api/buyer_chat/

### What Changed

Created the FastAPI HTTP router that maps the 7 buyer tool operations to endpoints, extracts ActorContext and InvocationContext from headers, and delegates to the BuyerAdapter. Included stub implementations of the application services for C2 demo wiring. Registered the router in app.py with a dedicated ValueError exception handler.

### Reason

Satisfy Phase C2 requirements to provide the primary Reference Buyer Chat HTTP transport layer without MCP dependencies.

### Technical Impact

Idempotency-Key and X-Correlation-ID are explicitly extracted from HTTP headers. AI/client payloads do not contain trusted financial fields. No LLM integration or MCP code is present here.

### Validation

Passed ruff, mypy, and pytest with 98% overall coverage. Specifically verified 422 responses for missing Idempotency-Key headers on mutating operations.

### Evidence

Repository files and local test execution.

### Result

SUCCESS

### Problems / Limitations

Uses stub services which must be replaced by real implementations from workstreams 02/03 at integration.

### Next Step

Merge Phase C2, then begin Phase C3.

---

## Entry 007 — Phase C3 Tool Orchestration Implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      phase/c3-tool-orchestration
Commit:          PENDING
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented ToolOrchestrator and LLMClient with httpx OpenAI compatibility.
Files/modules:   src/ai_commerce_gateway/application/buyer_adapter/

### What Changed

- Created LLMClient protocol and StubLLMClient for testing.
- Created OpenAILLMClient using httpx for real LLM API communication, configured via core/config.py.
- Implemented ToolOrchestrator to constrain LLM tool execution to the 7 canonical buyer tools.
- Enforced explicit authorization handoff: AI cannot self-approve; returns UI handoff on proposal/auth-request.
- Added /chat endpoint to buyer router.

### Reason

Satisfy Phase C3 requirements for intent-to-tool mapping, safe tool execution, and prompt-injection/no-self-approval guarantees.

### Technical Impact

Adds real HTTP LLM connectivity. No changes to frozen contracts or database schemas. The orchestrator effectively isolates the AI from unauthorized endpoints.

### Validation

Passed ruff, mypy, and pytest. Tests confirm prompt-injection isolation and strict permission bounding.

### Evidence

Repository files and local test execution.

### Result

SUCCESS

### Next Step

Merge Phase C3 and await next instructions.

---

## Entry 008 — Phase C4 MCP Buyer Adapter Implemented (and Fixed)

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      phase/c4-mcp-adapter
Commit:          c5177c0
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented MCP buyer adapter using official SDK v2.1.1 Streamable HTTP and fixed IMPORTANT #1.
Files/modules:   src/ai_commerce_gateway/api/mcp/, tests/unit/api/mcp/

### What Changed

- Added `mcp>=2.0,<3` to pyproject.toml (installed mcp 2.1.1).
- Created `buyer_server.py` registering 7 buyer tools via `MCPServer.tool()` decorators.
- Mounted Streamable HTTP ASGI app at `/mcp/buyer` with `streamable_http_path="/"`.
- Parent FastAPI lifespan enters `session_manager.run()` per SDK requirements.
- Fixed C3 I-1: Added 4 deterministic tests for OpenAILLMClient (mocked httpx).
- Fixed C3 I-2: MCP SDK derives tool schemas directly from function signatures.
- Fixed C4 IMPORTANT #1: derived deterministic idempotency keys for mutations using a fingerprint hash (`_derive_idempotency_key`) of `actor_id`, `tool_name` and tool arguments. Added `test_execute_transaction_is_idempotent` replay test to prove mutations will not duplicate state on retry.
- X-Buyer-ID documented as DEMO IDENTITY PLUMBING, not production auth.

### Reason

Satisfy Phase C4: prove external MCP client interoperability over the same commerce backend and ensure deterministic mutation replays.

### Technical Impact

Adds MCP SDK dependency. No changes to frozen contracts or database schemas. MCP adapter is thin: all business logic stays in Application Services. Deterministic idempotency protects against network retries causing double-purchases or duplicate authorizations.

### Validation

- ruff: PASS
- mypy: PASS (33 files, 0 errors)
- pytest: 66 passed, 1 skipped, 95% coverage
- Interop test: Official MCP Client over real HTTP transport proved search_catalog and create_purchase_proposal reach Application Services.
- Replay test: Verified duplicate tool calls pass the identical idempotency key to the Adapter.

### Evidence

In-memory contract tests (12) + HTTP interop test (1) + LLM client tests (4) + all existing tests (49).

### Result

SUCCESS

### Next Step

Await human gate review to begin Phase C5.
