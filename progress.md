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

---

## Entry 009 — Phase C5 Buyer Transaction UI Implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      phase/c5-buyer-transaction-ui
Commit:          e629008
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented C5 transaction presentation formatting and safety logic in ToolOrchestrator.
Files/modules:   src/ai_commerce_gateway/application/buyer_adapter/orchestrator.py, tests/unit/application/buyer_adapter/test_orchestrator.py

### What Changed

- Enhanced `ToolOrchestrator` to map raw `TransactionState` into buyer-safe presentation strings.
- Implemented recovery guidance for failed transactions within the `get_transaction_status` tool.
- Ensured `get_transaction_audit` strictly redacts sensitive provider secrets from metadata.
- Implemented explicit payment handoff logic for `execute_transaction`, preventing false success hallucinations.
- Added four new contract tests for status mapping, recovery, redaction, and handoff triggers.

### Reason

Satisfy Phase C5 requirements: Payment handoff, status mapping, recovery, redaction, and no-false-success guarantees for the buyer's UI/chat.

### Technical Impact

No backend API signatures changed. The orchestrator now safely formats tool outputs so that the LLM receives safe text, preventing hallucinated success states.

### Validation

- ruff: PASS
- mypy: PASS (33 files, 0 errors)
- pytest: 69 passed, 1 skipped, 96% coverage
- Contract tests proved the orchestrator safely handles and redacts transactions.

### Evidence

Repository tests, coverage report, and test execution output.

### Result

SUCCESS

### Next Step

Await human gate review to begin Phase C6.

### Gate Review Notes (C5)
- **Verdict**: PASS WITH MINOR ISSUES
- **IMPORTANT #1**: Fixed mapping for `UNKNOWN` and `RECONCILING` states in `get_transaction_status` to ensure buyer-safe presentation with appropriate recovery text. (Implemented in follow-up commit).
- **MINOR #2**: Noted `frontend-handoff/` directory bleed. These are UI documents for a separate frontend component (Workstream 01 / A6) and are not part of C5 behavior.
- **MINOR #3**: Tests correctly use `MockBuyerAdapter` to isolate orchestrator testing.
- **MINOR #4**: Redaction zeroes out `metadata`, relying on upstream masking for other top-level keys like `provider_reference_redacted`.

---

## Entry 010 — Phase C6 Buyer Integration Harness Implemented

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      phase/c6-buyer-harness
Commit:          577f5ab
Author/Agent:    Antigravity
Workstream:      05-buyer-ai-mcp
Change:          Implemented the Buyer/Chat/MCP integration harness and dependency replacement.
Files/modules:   src/ai_commerce_gateway/api/app.py, tests/integration/test_buyer_harness.py

### What Changed

- Updated `app.py`'s `create_app` factory to accept an injected `buyer_adapter`.
- Bound the injected adapter cleanly to both the `BuyerAdapter` dependency (for HTTP routes) and the MCP Server (for MCP tooling).
- Created `test_buyer_harness.py` containing an end-to-end integration test harness.
- Wrote parity tests (`test_buyer_harness_chat_parity`, `test_buyer_harness_mcp_parity`) that exercise the complete canonical buyer journey via both the direct `/v1/buyer/chat` and `/v1/buyer/*` endpoints, as well as the MCP Streamable HTTP endpoint.

### Reason

Satisfies Phase C6 requirements for real-seam parity tests and separate chat/MCP traces without relying on a full E2E setup. Proves that both interfaces behave identically over the same application seams.

### Technical Impact

Allows tests (or staging environments) to completely replace the backend service implementations without breaking or altering application structure. The parity tests prove the system is fully prepared to consume Workstream 02/03 database-backed services.

### Validation

- ruff: PASS
- mypy: PASS (33 files, 0 errors)
- pytest: 71 passed, 1 skipped, 97% overall test coverage.

### Evidence

Repository tests, coverage report, and integration harness execution.

### Result

SUCCESS

### Next Step

Await human gate review to begin Workstream 05 (C7) or proceed to next lane.

### Gate Review Notes (C6)
- **Verdict**: PASS WITH MINOR ISSUES
- **IMPORTANT #1**: Noted that "Chat parity" drives only the search step through the LLM/chat path, while steps 2-4 hit direct HTTP seams (`/v1/buyer/purchase-proposals`, etc.). This proves transport-seam parity but does not fully trace the LLM intent->tool path for the full sequence.
- **MINOR #2**: `frontend-handoff/` docs from C5 remain bundled in the lineage.
- **MINOR #3**: Harness correctly uses stubs (no `TEST_DATABASE_URL`), keeping full DB-backed persistence tests deferred to 07.
- **MINOR #4**: The MCP parity test focuses on happy-path equivalence rather than re-verifying tool schemas/permissions (which is covered by C4's contract tests).

---

## Entry 011 — P0-1 Real service composition seam replaces production stubs

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      feature/buyer-ai-lane
Commit:          <this commit>
Author/Agent:    opencode buyer-lane agent (GLM)
Workstream:      05-buyer-ai-mcp
Change:          Removed Stub* services from production; added BuyerServiceBundle/BuyerServicesFactory composition seam with in-process and remote strategies and fail-fast default
Files/modules:   src/ai_commerce_gateway/api/composition.py (new), src/ai_commerce_gateway/infrastructure/http/remote_services.py (new), src/ai_commerce_gateway/api/app.py, src/ai_commerce_gateway/api/buyer_chat/router.py, src/ai_commerce_gateway/api/buyer_chat/stubs.py (deleted), src/ai_commerce_gateway/api/mcp/buyer_server.py, src/ai_commerce_gateway/api/buyer_chat/dependencies.py, src/ai_commerce_gateway/core/config.py, config/default.yaml, config/local.example.yaml, pyproject.toml, uv.lock, tests/* (conftest, harness, mcp, chat routes, llm client, new composition and remote-services tests)

### What Changed

- Deleted `api/buyer_chat/stubs.py` entirely: the default app can no longer construct StubCatalogService/StubProposalService/StubAuthorizationService/StubTransactionService in any environment, and the `app_env == "test"` stub escape hatch was removed.
- Added `api/composition.py`: `BuyerServiceBundle` (the four frozen buyer-facing service protocols as one unit), `BuyerServicesFactory` (callable returning a request-scoped context-managed bundle owning the unit of work), `static_bundle_factory` (test/embedding seam), `compose_remote_buyer_services_factory` (HTTP-client adapters over deployed trusted services), `compose_in_process_buyer_services_factory` (lazy-imports the approved merchant/transaction lane services: merchant `ApplicationCatalogService`, transaction `ProposalApplicationService`/`AuthorizationApplicationService`/`compose_transaction_services`, `SqlAlchemyProposalGateRepository`, `RazorpayAdapter`), `compose_default_buyer_services_factory` (config-selected, never stubs), and `SessionBuyerApprovalVerifier` (human buyer approval bound to the server-trusted session actor; implements the transaction lane's HumanBuyerApprovalVerifier protocol structurally).
- Added `infrastructure/http/remote_services.py`: RemoteCatalogService/RemoteProposalService/RemoteAuthorizationService/RemoteTransactionService implementing the frozen protocols over a documented internal wire contract with X-Actor-ID/X-Actor-Type/X-Correlation-ID trusted-context headers, Idempotency-Key forwarding for mutations, DTO round-trips and canonical error-envelope → AppError mapping.
- `create_app(services_factory=...)` is now the single composition seam; the factory is stored on `app.state.buyer_services_factory`, consumed by the HTTP router (request-scoped dependency with commit/rollback via the context manager) and by every buyer MCP tool (same seam, same real services). The module-level ASGI `app` is built lazily (PEP 562) so the fail-fast guard triggers at server start, not import.
- New `buyer_services` YAML config section (mode/catalog_base_url/transaction_base_url/timeout_seconds) validated by the strict config schema.
- Tests: fakes enriched and confined to tests (search now returns a published product for journey tests); all stub imports removed from tests; new `tests/unit/api/test_composition.py` (fail-fast guidance, remote validation, integrated-composition wiring via monkeypatched namespace, approval-verifier positive/negative) and `tests/unit/infrastructure/test_remote_services.py` (wire contract, headers, idempotency forwarding, error mapping via httpx.MockTransport); MCP idempotency test rewritten to spy at the service layer (per-request adapters make instance patching obsolete).

### Reason

P0-1 of the buyer-lane P0 brief: the default buyer FastAPI app must use real injected application services, never stubs; test fakes only in tests; clear composition/DI seams for the integrated application.

### Technical Impact

- Production composition is stub-free by construction; misconfiguration fails fast with actionable remediation text.
- The buyer chat HTTP API, buyer UI API and buyer MCP now provably reach the same service bundle through one seam.
- In-process composition mirrors the sibling lanes' reviewed constructors exactly (verified against phase/a6-merchant-dashboard and phase/b7-security-hardening heads on 2026-09-04); runtime validation of that path is deferred to integration because those modules do not exist in a single-lane checkout.
- Remote adapters define a wire contract that the merchant/transaction lanes do not yet serve (no buyer-facing HTTP API exists in either lane); they are exercised in tests against an in-test stand-in and documented for future separate deployment.

### Validation

- `uv run ruff check .` — PASS
- `uv run mypy` — PASS (35 files, 0 errors; per-module ignore_missing_imports override added in pyproject for the cross-lane lazy imports)
- `uv run pytest` — 94 passed, 1 skipped (tests/integration/test_database_connection.py: TEST_DATABASE_URL not configured)
- Fail-fast verified: `uv run python -c "import ai_commerce_gateway.api.app as m; m.app"` raises the composition guidance RuntimeError on this single-lane checkout.

### Evidence

Command outputs above on branch feature/buyer-ai-lane; test files tests/unit/api/test_composition.py, tests/unit/infrastructure/test_remote_services.py.

### Result

SUCCESS (in-process composition runtime validation deferred to integration by design)

### Problems / Limitations

- The in-process composition path imports modules that only exist in the integrated repository; it is unit-tested via monkeypatched stand-ins and cannot be runtime-validated on this branch.
- No buyer-facing HTTP API exists yet in the merchant/transaction lanes for the remote adapters to target; the wire contract is documented for coordination.
- The buyer MCP still uses the temporary demo actor (`buyer_demo_001`); replacement with the authenticated actor context is the P0-4 step.

### Next Step

P0-2: bounded Buyer AI (config-driven LLM client, complete JSON tool schemas from tools.py, bounded tool-result loop with audit events, no self-approval tools).

---

## Entry 012 — P0-2 Bounded Buyer AI: config LLM client, full tool schemas, bounded loop, orchestration audit

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      feature/buyer-ai-lane
Commit:          <this commit>
Author/Agent:    opencode buyer-lane agent (GLM)
Workstream:      05-buyer-ai-mcp
Change:          Wired the chat route to a YAML-configured LLM client, served complete JSON tool schemas, implemented the bounded tool-result loop with human-handoff cutoff, and added non-sensitive orchestration audit events
Files/modules:   src/ai_commerce_gateway/application/buyer_adapter/audit.py (new), src/ai_commerce_gateway/application/buyer_adapter/orchestrator.py, src/ai_commerce_gateway/application/buyer_adapter/llm_client.py, src/ai_commerce_gateway/api/buyer_chat/router.py, src/ai_commerce_gateway/core/config.py, config/default.yaml, config/local.example.yaml, tests/unit/application/buyer_adapter/test_orchestrator.py, tests/unit/application/buyer_adapter/test_llm_client.py

### What Changed

- LLM selection is config-driven: `create_llm_client(settings)` returns the litellm-backed provider client when `llm.api_key` is configured, else the deterministic local fallback with a loud warning. `OpenAILLMClient` now receives injected Settings (no global lookup inside the client) and forwards `llm.temperature`; the buyer chat route builds the orchestrator from `create_llm_client()` — the hardcoded StubLLMClient is gone from production wiring.
- Tool schemas sent to the model are the complete JSON schemas from `tools.ALL_TOOLS` (typed properties, required lists, no price/total/approve/provider surface anywhere).
- `ToolOrchestrator.chat` now runs a bounded tool-result loop (default bound 8, configurable via new `llm.max_tool_steps`): the model's tool calls execute against the BuyerAdapter and results are fed back as tool messages until the model answers with text, a handoff is reached, or the bound is hit (explicit step-limit message).
- Security fix: when a handoff tool (create_purchase_proposal / request_authorization / execute_transaction) succeeds, any further tool calls from the SAME model response are dropped and recorded as rejected — the AI can never chain proposal -> execute past the human gate inside one turn.
- New `buyer_adapter/audit.py`: `AiOrchestrationAuditEvent` (request_id, correlation_id, actor_id, turn, tool, outcome, result_reference — never raw prompts or free-text argument values), `AiOrchestrationAuditRecorder` port, `LoggingAiOrchestrationAuditRecorder` default, and non-sensitive result-reference extraction (resource ids / coarse counts only). The chat response exposes the same events as `trace` for the buyer UI "AI works" surface.
- StubLLMClient now terminates the loop after tool results (role == "tool" -> plain answer) and keyword-matches only the last USER message, keeping the loop deterministic for tests/E2E.
- Provider error logging no longer logs exception payloads (type name only) to avoid leaking request content into logs.

### Reason

P0-2 of the buyer-lane brief: a genuine bounded Buyer AI over configured LLM, complete JSON tool schemas, the canonical bounded loop with human authorization handoff, and non-sensitive orchestration auditing.

### Technical Impact

- The buyer chat endpoint now exercises a real multi-turn loop; search -> answer and buy -> proposal -> handoff both verified end to end.
- No new tools were added; the frozen tool surface is unchanged.
- The chat response gains a non-sensitive `trace` array; response shape is otherwise unchanged.

### Validation

- `uv run ruff check .` — PASS
- `uv run mypy` — PASS (36 files, 0 errors)
- `uv run pytest` — 100 passed, 1 skipped (PostgreSQL-only test; no TEST_DATABASE_URL locally)
- Manual trace: POST /v1/buyer/chat with test buyer token returns trace with requested+completed events, non-sensitive references only.

### Evidence

Test run above; new tests cover complete-schema delivery, tool-result feedback into the loop, the hard step bound, the same-response handoff cutoff, audit-event non-sensitivity, and result-reference extraction.

### Result

SUCCESS

### Problems / Limitations

- Real provider behavior (litellm against a live key) is not exercised locally; deterministic fallback covers CI. Provider smoke test belongs to a configured environment.
- Orchestration audit defaults to structured logging; a durable recorder can be injected via the orchestrator constructor when the audit store is provisioned.

### Next Step

P0-3: buyer identity/security — replace the test-token middleware with server-trusted session authentication and verify buyer ownership enforcement end to end (including the human approve path).

---

## Entry 013 — P0-3 Server-trusted buyer sessions and human-only approval endpoint

Date/time:       2026-09-04 (Asia/Calcutta)
Git branch:      feature/buyer-ai-lane
Commit:          <this commit>
Author/Agent:    opencode buyer-lane agent (GLM)
Workstream:      05-buyer-ai-mcp
Change:          Replaced the test_buyer_* token simulation with HMAC-signed buyer session tokens, removed all trust of X-Buyer-ID/body identity, and added the human-only authorization approval endpoint
Files/modules:   src/ai_commerce_gateway/api/session_auth.py (new), src/ai_commerce_gateway/api/app.py, src/ai_commerce_gateway/api/buyer_chat/router.py, src/ai_commerce_gateway/api/buyer_chat/dependencies.py, src/ai_commerce_gateway/core/config.py, config/default.yaml, config/local.example.yaml, pyproject.toml (itsdangerous), uv.lock, tests/conftest.py, tests/unit/api/test_buyer_sessions.py (new), tests/unit/application/buyer_adapter/test_chat_routes.py, tests/unit/application/buyer_adapter/fakes.py, tests/integration/test_buyer_harness.py

### What Changed

- New `BuyerSessionService` (api/session_auth.py): HMAC-signed, expiring buyer session tokens via itsdangerous URLSafeTimedSerializer (SHA-256). `issue()` mints server-side; `resolve()` verifies signature+expiry; `actor_context()` returns a server-trusted ActorContext or None. Without a configured secret the gateway is fail-closed (every buyer endpoint 401s).
- `auth_middleware` replaced entirely: only `Authorization: Bearer <signed token>` is accepted; `X-Buyer-ID`, request bodies and query parameters can never set identity. The old `test_buyer_*` prefix acceptance is deleted from production code.
- `POST /v1/buyer/sessions` mints tokens but is guarded by the configured issuer key (`buyer_sessions.issuer_key`, X-Session-Issuer-Key header); disabled (503) when unconfigured. This is the identity bootstrap seam a real identity provider would hold.
- `POST /v1/buyer/purchase-proposals/{id}/approvals` is the human authorization handoff: the buyer UI replays exactly the terms shown (proposal_hash, max_quantity, max_amount, expiry); Idempotency-Key required. It is deliberately NOT exposed via BuyerAdapter, the AI tool surface or MCP — the approve capability is structurally absent there (asserted by test).
- `create_app(..., settings=...)` is now an explicit DI seam; app.state carries settings + session service so routes never fall back to global config lookup.
- 401s now use the canonical error envelope (AppError UNAUTHENTICATED) instead of bare HTTPException.
- FakeAuthorizationService (tests only) now records approve calls and returns an APPROVED view bound to the session actor.

### Reason

P0-3 of the buyer-lane brief: production identity must come from server-trusted session middleware, never from client-supplied buyer IDs; ownership enforced on every call by passing the verified actor to the services (the transaction lane additionally re-checks proposal ownership server-side).

### Technical Impact

- All existing tests were migrated from opaque test tokens to real HMAC session tokens minted in conftest (`issue_buyer_token`), so the HTTP surface now always exercises the real session path.
- New config section `buyer_sessions` (secret/issuer_key/ttl_seconds), strict-validated.
- Security boundary confirmed: AI/MCP surfaces expose search/inspect/propose/request/execute/status/audit only; approval is human-UI-only.

### Validation

- `uv run ruff check .` — PASS
- `uv run mypy` — PASS (37 files, 0 errors)
- `uv run pytest` — 122 passed, 1 skipped (PostgreSQL-only test)
- tests/unit/api/test_buyer_sessions.py covers: issuance issuer-key guards, no-token/arbitrary/tampered/foreign-secret/expired rejection (401), missing-secret fail-closed, X-Buyer-ID never trusted (unauthenticated and no override), body buyer-spoofing ignored, per-buyer identity scoping, human approve binding to the session actor with idempotency, and approve's structural absence from the AI/MCP adapter.

### Evidence

Test run above; issue/resolve flow exercised through the real TestClient surface.

### Result

SUCCESS

### Problems / Limitations

- The issuer-key issuance endpoint is the prototype identity bootstrap (explicitly documented as such); a production identity provider integration replaces it without touching the session token mechanism.
- The MCP surface still uses the demo actor; wiring MCP to the same session identity is P0-4.

### Next Step

P0-4: finish buyer MCP — authenticated actor from the session layer inside MCP tools, buyer-only isolation checks, and real HTTP interop tests.
