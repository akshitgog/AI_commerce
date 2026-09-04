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

## Entry 004 — Phase A1: Merchant and Catalog Domain Foundation

Date/time:       2026-09-04 11:40 IST
Git branch:      phase/a1-merchant-domain
Commit:          0946829
Author/Agent:    Agent A (AI Commerce Gateway — Merchant/Catalog lane)
Workstream:      merchant | catalog
Change:          Domain entities, repository protocols, SQLAlchemy implementations, and tests for Phase A1

Files/modules:
  src/ai_commerce_gateway/domain/merchant.py
  src/ai_commerce_gateway/domain/product.py
  src/ai_commerce_gateway/domain/policy.py
  src/ai_commerce_gateway/domain/repositories.py
  src/ai_commerce_gateway/infrastructure/database/merchant_repositories.py
  tests/unit/test_merchant_domain.py
  tests/unit/test_product_domain.py
  tests/unit/test_merchant_repository_contracts.py
  tests/unit/test_a1_schema_contracts.py
  tests/integration/test_merchant_persistence.py

### What Changed

Implemented the Phase A1 merchant/catalog domain foundation:

1. **Domain entities** (`domain/merchant.py`, `domain/product.py`, `domain/policy.py`):
   - Frozen, slotted dataclasses for `MerchantEntity`, `MerchantUserEntity`, `ProductEntity`,
     `ProductMetadataEntity`, `ProductImageEntity`, `MerchantPolicyEntity`.
   - `MoneyMinor` value object enforces integer minor units and 3-letter ISO currency.
   - `ProductMetadataEntity` is structurally separate from `ProductEntity`; no price/currency/
     stock/status fields exist on metadata — AI enrichment cannot accidentally modify commercial data.
   - `ProductImageEntity` carries both `merchant_id` and `product_id` so every query is
     tenant+product scoped; `belongs_to(merchant_id, product_id)` makes ownership explicit.
   - `MerchantPolicyEntity` enforces policy invariants at construction time (AUTO_BELOW_LIMIT
     requires auto_accept_max; other modes cannot have it; version >= 1).

2. **Repository protocols** (`domain/repositories.py`):
   - `MerchantRepository`, `MerchantUserRepository`, `ProductRepository`,
     `ProductMetadataRepository`, `ProductImageRepository`, `MerchantPolicyRepository`.
   - Every method signature that touches merchant-owned data requires `merchant_id` as a parameter,
     making cross-tenant access structurally impossible through the interface.

3. **SQLAlchemy implementations** (`infrastructure/database/merchant_repositories.py`):
   - Concrete implementations using the existing ORM models from the M0 foundation.
   - `IntegrityError` caught and converted to `AppError` with appropriate HTTP status codes.
   - All queries filter by `merchant_id` in the WHERE clause (not just application-level).

4. **Tests** (124 pass, 27 PostgreSQL integration tests skip when TEST_DATABASE_URL is absent):
   - Unit tests for all domain entity invariants (frozen, integer money, tenant separation,
     SKU semantics, metadata separation, image ownership, policy modes).
   - Repository contract tests using in-memory fakes (all 10 correctness requirements).
   - Schema contract tests verifying ORM metadata constraints and PostgreSQL DDL compilation.
   - Migration compatibility test: alembic offline SQL generation includes all A1 tables.
   - PostgreSQL persistence tests (skipped without TEST_DATABASE_URL).

### Reason

Phase A1 is the prerequisite for all later merchant/catalog work (A2–A6) and is required by the
workstream plan. The domain/persistence foundation must exist before product CRUD (A2) can begin.

### Technical Impact

- No changes to frozen shared contracts (contracts/models.py, contracts/services.py, domain/enums.py).
- No HTTP routes added (A2 scope).
- No application service layer added (A2 scope).
- The M0 foundation migration already covers all A1 tables; no new migration needed.
- ORM models unchanged; only new domain entities and repository implementations added.

### Validation

ruff: All checks passed
mypy: Success: no issues found in 25 source files
pytest: 124 passed, 27 skipped (PostgreSQL integration; no TEST_DATABASE_URL)
coverage: 81% total; domain and ORM models at 98–100%
alembic upgrade head --sql: Generates valid PostgreSQL DDL for all A1 tables with correct constraints
PostgreSQL integration: SKIPPED (TEST_DATABASE_URL not set); 27 tests ready to run

### Evidence

- All 10 correctness requirements covered by unit + contract + schema tests.
- SKU uniqueness (merchant-scoped) tested at domain, fake-repository, and schema levels.
- Tenant isolation tested with `belongs_to()` method and repo-level query guards.
- MoneyMinor rejects floats by type; no float field exists anywhere in the domain.
- ProductMetadata structurally has no price/currency/stock columns (schema test verifies).
- Alembic SQL shows `INTEGER NOT NULL` for `price_minor`, `version`, `available_quantity`.

### Result

SUCCESS

### Problems / Limitations

- PostgreSQL integration tests require TEST_DATABASE_URL to run (correctly skipped without it).
- The existing M0 migration covers all A1 tables; there is no A1-specific migration revision.
  This is intentional — the M0 freeze already captured the full schema. A new revision would be
  needed only if the A1 domain work required schema changes (it did not).
- No application service layer yet (A2 scope).
- No HTTP routes yet (A2 scope).

### Next Step

A2 — Product CRUD/Application Services (requires human approval before starting).
## [2026-09-04] Phase A1 Correction Pass

**Role:** Agent A (Merchant/Catalog Lane)
**Status:** READY FOR RE-REVIEW
**Branch:** phase/a1-merchant-domain

**Changes Made:**
1. **BLOCKER 1 - MoneyMinor & Int Validation**: Enforced strict int checks in MoneyMinor to explicitly reject bool, float, Decimal, and strings. Replicated strict typing to available_quantity, version, sort_order, and version. Added adversarial test coverage in test_product_domain.py.
2. **BLOCKER 2 - ProductMetadata Tenant Isolation**: Updated ProductMetadataRepository protocol and SqlAlchemyProductMetadataRepository implementation to require merchant_id parameter. Implemented an explicit _verify_ownership check against orm.Product before read/write operations to enforce proper tenant isolation.
3. **BLOCKER 3 - ProductImage Tenant Isolation**: Added product ownership verification logic (orm.Product.id == entity.product_id AND orm.Product.merchant_id == entity.merchant_id) before image insertion in SqlAlchemyProductImageRepository.add() to prevent cross-tenant DOs/hijacking.
4. **IMPORTANT - IntegrityError Mapping**: Wrapped session.flush() with try/except IntegrityError to raise AppError in SqlAlchemyProductRepository.update() and SqlAlchemyMerchantPolicyRepository.add() + update().
5. **IMPORTANT - Removed internal rollbacks**: Removed self._session.rollback() from all repository methods. This project uses caller-owned transactions (session_scope()), so internal rollbacks inappropriately discarded all pending caller work.
6. **IMPORTANT - Concrete Repository Tests**: Added tests/unit/test_concrete_repositories.py executing concrete SQLAlchemy implementations against a local in-memory SQLite database. This drastically improved test coverage (up to 92%) by verifying all error paths and untested branches.

**Validation:**
- ruff check passed with 0 errors.
- mypy passed with 0 errors.
- pytest passed (131 passed, 27 skipped, coverage increased to 92%).

All frozen shared contracts remain completely untouched. Phase A1 is now fully compliant with constraints and ready for merge.

## [2026-09-04] Phase A2 Product CRUD

**Role:** Agent A (Merchant/Catalog Lane)
**Status:** REVIEWED AND APPROVED
**Branch:** phase/a2-product-crud

**Changes Made:**
1. **Application Service implementation**: Created src/ai_commerce_gateway/application/catalog_service.py with ApplicationMerchantCatalogService implementing MerchantCatalogService.
2. **Tenant scoping & Roles**: Enforced tenant boundaries and role requirements (e.g. ADMIN or EDITOR required for create/update) using ActorContext via a _require_merchant_access guard.
3. **Draft Product CRUD**: Implemented create_product, update_product, get_product, and list_products.
4. **Validation and SKU Uniqueness**: Enforced SKU uniqueness on creation returning 409 Conflict. Implemented optimistic concurrency control using expected_version returning 409 Conflict on stale writes.
5. **Testing**: Implemented tests/unit/test_catalog_service.py to cover CRUD capabilities, authorization denials, SKU duplicate denials, and version mismatch denials.
6. **Unscoped product loading**: Added a safe get_by_id_unscoped to ProductRepository that allows fetching a product by ID before validating its merchant_id against the caller's authorized context (required since get_product contract only receives product_id).

**Validation:**
- ruff check . passed cleanly.
- mypy passed (0 issues).
- pytest passed (136 passed, coverage up to 95%).
- All M0 contracts adhered to.

**Correction Pass (Phase A2):**
1. **Removed get_by_id_unscoped:** Removed the unscoped lookup from ProductRepository to restore strictly tenant-scoped SQL queries.
2. **Fixed ID Enumeration Oracle:** Modified get_product to loop over actor.merchant_ids, performing a tenant-scoped query for each. If not found, it returns a safe 404 Not Found, preventing cross-tenant existence leaks (which previously returned 403 Forbidden).
3. **Fixed Linters:** Addressed all ruff violations (unused imports, long lines) in the test suite.
4. **Updated Adversarial Tests:** Validated that cross-tenant product probing yields a 404 Not Found.

**Correction Pass 2 (Phase A2):**
1. **Ruff linting (F1):** Fixed the missing # noqa: E501 on long raise statement lines in catalog_service.py to ensure ruff passes completely clean.
2. **Cursor pagination test (F2):** Implemented cursor logic fixes for sorting by (created_at, id) properly in SqlAlchemyProductRepository.list_for_merchant and authored 	est_merchant_catalog_service_list_products_pagination to assert 
ext_cursor logic with 55 created products.
3. **SYSTEM actor test (F3):** Authored 	est_merchant_catalog_service_system_get_product_not_implemented to cover the explicit NotImplementedError raised for SYSTEM actors querying without a merchant_id context in get_product.
4. **SQLite Warnings (F5):** Repaired ResourceWarning: unclosed database leaks by calling ngine.dispose() within test fixtures yielding Session objects across all of 	ests/unit/.

**Final IMPORTANT Correction (Phase A2 Review):**
1. **DB Atomic Concurrency Enforcement:** Refactored SqlAlchemyProductRepository.update to execute an atomic UPDATE ... WHERE id = X AND merchant_id = Y AND version = expected_version instead of a select-and-modify. This enforces optimistic concurrency natively at the SQL level, ensuring a concurrent race maps cleanly to a 409 VALIDATION_ERROR (stale write) rather than causing unexpected overwrite behavior. Added a rigorous 	est_merchant_catalog_service_update_product_db_race unit test verifying that bypassing the application-level pre-checks still hits this SQL-level lock properly.
2. **Review Status Updated:** Phase A2 is reviewed and approved.


## Phase A3 Updates (Catalog Publication)
- Updated CatalogService.get_product contract to explicitly require merchant_id to strictly preserve SQL-level tenant isolation, per D-008.
- Implemented publish_product and unpublish_product in ApplicationMerchantCatalogService enforcing atomic version increments and stale-write checks.
- Implemented ApplicationCatalogService for buyers in src/ai_commerce_gateway/application/buyer_catalog_service.py to fulfill the CatalogService contract:
  - get_product validates ProductStatus.PUBLISHED before returning the product, rendering draft products strictly invisible to buyers.
  - search handles multi-parameter CatalogSearchQuery filtering across query strings, prices, and categories over the repository list_published page.
- Added comprehensive unit tests in test_buyer_catalog_service.py verifying published visibility, draft invisibility, filter correctness, publish/unpublish mechanics, and 409 stale-write scenarios.
- Ran formatting and static checks (ruff check, mypy). All pass cleanly. Test coverage remains at 95% across 141 tests.
- Status: READY FOR REVIEW
