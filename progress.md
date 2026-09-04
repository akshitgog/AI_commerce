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


## [2026-09-04] Phase A3 Catalog Publication

**Role:** Agent A (Merchant/Catalog Lane)
**Status:** REVIEWED AND APPROVED
**Branch:** phase/a3-catalog-publication

**Implemented:**
1. **Catalog Publication Lifecycle:** Implemented `publish_product` and `unpublish_product` in `ApplicationMerchantCatalogService` enforcing role-based permissions (`ADMIN` or `EDITOR`), `expected_version` concurrency pre-checks, and atomic SQL-level update incrementing version.
2. **Buyer Catalog Service:** Created `ApplicationCatalogService` in `src/ai_commerce_gateway/application/buyer_catalog_service.py` implementing `CatalogService`. Enforces draft invisibility (`get_product` returns 404 for un-published items) and safe published search.
3. **Approved Contract Change (D-008):** Formally updated `CatalogService.get_product(merchant_id: str, product_id: str, actor: ActorContext)` to ensure SQL-level tenant isolation (Invariant 19). Reverted `MerchantCatalogService.get_product` to keep its frozen `(product_id, actor)` signature without unnecessary alterations.

**Review Findings Addressed:**
- **[BLOCKER 1 - Ruff E501]:** Fixed all line length violations in `test_buyer_catalog_service.py` and `buyer_catalog_service.py`. `uv run ruff check .` passes with 0 errors.
- **[IMPORTANT 2 - Formal Contract Approval]:** Recorded explicit integrator/human approval for D-008 in `docs/decisions.md` and `decisions.md` (Status: APPROVED).
- **[IMPORTANT 3 - Merchant Protocol Seam]:** Restored `MerchantCatalogService.get_product` signature in `contracts/services.py` back to `(product_id: str, actor: ActorContext)` so it matches implementation and keeps the M0 frozen protocol intact.
- **[IMPORTANT 4 - Role Denial & Isolation Tests]:** Added exhaustive tests for `publish_product` and `unpublish_product` asserting `VIEWER` (403) and cross-tenant actor (403) rejections. Added tests for multi-merchant search isolation proving products from Merchant A never leak to Merchant B searches.
- **[IMPORTANT 5 - Search Filtering Architecture]:** Documented architectural rationale for in-memory filtering over frozen `ProductRepository.list_published(merchant_id, cursor, limit)`. Synchronized `list_published` cursor pagination to use tuple-based `(created_at, id)` comparisons matching `list_for_merchant`. Added test coverage for all filter branches (`category`, `min_price_minor`, `max_price_minor`, `currency`, `query` on title & description) and multi-page cursor pagination.
- **[MINOR 6 - Code Deduplication]:** Deduplicated `_to_product_view` into a single reusable helper imported across services.
- **[GOVERNANCE 7 - Dedicated Branch]:** Switched active work to dedicated branch `phase/a3-catalog-publication` while preserving `phase/a2-product-crud` at commit `2bf012f`.

**Validation:**
- `uv run ruff check .` -> PASS (0 errors)
- `uv run mypy` -> PASS (0 issues across 27 source files)
- `uv run pytest --cov=ai_commerce_gateway --cov-report=term-missing` -> PASS (144 passed, 27 skipped, 0 failed, 96% coverage)
- `uv run alembic upgrade head --sql` -> PASS (clean schema build)

**Minor / Optional Review Notes Recorded:**
1. Search filtering in memory over tenant-scoped `list_published` is documented and appropriate for V1 merchant scale; can revisit if buyer search scale warrants dedicated repository methods.
2. Search cursor pagination edge case (when in-memory filtering reduces result count) is noted and preserves keyset correctness.
3. Root `decisions.md` and `docs/decisions.md` duplicate D-008; recommendation noted for canonicalization.
4. Future roadmap option for SQL-level filtering via `search_published(filters)` deferred until scale requires it.

**A7 Obstruction Check:**
A3 neither adds nor removes `idempotency_key` semantics and leaves `MerchantCatalogService`, enums, `contracts/models.py` DTOs, and the database schema completely untouched. Future Phase A7 durable fingerprinted idempotency and publication confirmation can wrap canonical operations seamlessly. The only carried-forward note is that `CatalogService.get_product` (buyer path) now requires `merchant_id`, which is relevant to Workstream C integration.

## [2026-09-04] Phase A4 Merchant Policy

**Role:** Agent A (Merchant/Catalog Lane)
**Status:** REVIEWED AND APPROVED
**Branch:** phase/a4-merchant-policy

**Implemented:**
1. **Policy Application Service:** Implemented `ApplicationMerchantPolicyService` in `src/ai_commerce_gateway/application/policy_service.py` satisfying `MerchantPolicyService`.
2. **Policy Configuration & Versioning:**
   - `get_policy`: Strictly tenant-scoped policy retrieval (returns 403 for unauthorized actors, 404 if no policy exists).
   - `update_policy`: Gated to `ADMIN` role. Validates policy modes (`MANUAL_ALL`, `AUTO_BELOW_LIMIT`, `DENY_ALL`) and enforces `auto_accept_max` constraints with strict minor unit typing. Handles version incrementing and rejects stale writes with 409 VALIDATION_ERROR.
3. **Manual Review Queue Operations:**
   - `list_reviews`: Tenant-scoped review queue retrieval supporting cursor pagination over pending `REVIEW_REQUIRED` merchant decision items.
4. **Clean Domain Seams:**
   - `evaluate` and `record_manual_decision`: Correctly deferred to Transaction Core (B2) with `NotImplementedError` per architectural boundaries.
5. **Comprehensive Testing:**
   - Created `tests/unit/test_merchant_policy_service.py` with 100% statement coverage on `policy_service.py` and `contracts/models.py`. Validates all modes, initial creation, updates, role rejections (non-ADMIN denied update with 403), cross-tenant rejections (403), review queue pagination, and command validations.

**Validation:**
- `uv run ruff check .` -> PASS (0 errors)
- `uv run mypy` -> PASS (0 issues across 28 source files)
- `uv run pytest --cov=ai_commerce_gateway --cov-report=term-missing` -> PASS (149 passed, 27 skipped, 0 failed, 97% overall coverage, 100% on policy_service.py)
- `uv run alembic upgrade head --sql` -> PASS (clean schema build)

**Minor / Optional Review Notes Recorded:**
1. `list_reviews` direct ORM join bypasses the repository layer (couples application layer to DB schema; recommend introducing `MerchantPolicyRepository.list_pending_reviews()` in future refactor).
2. `session=None` returns an empty review queue silently; consider raising an explicit configuration error in production hardening.
3. Inlined `datetime.now(tz=UTC)` at `policy_service.py:89` noted for consistency with shared `_now()` helpers.
4. Coordination with B2: Ensure B2's review-required decision flow populates `MerchantDecision.reason_code` and `decision` columns consistently with `list_reviews`.

**A7 Obstruction Check:**
A4 neither changes frozen contracts/DTOs/enums/schema nor introduces any idempotency or publication-confirmation behavior that would obstruct A7. A7 wraps only canonical product CRUD/publication operations, none of which A4 touches. No obstruction.

## [2026-09-04] Phase A5 Product Storage

**Role:** Agent A (Merchant/Catalog Lane)
**Status:** READY FOR REVIEW
**Branch:** phase/a5-product-storage

**Implemented:**
1. **Storage Adapters:**
   - `InMemoryStorageService` (`src/ai_commerce_gateway/storage/memory.py`) implementing `StorageService` for unit tests and local development.
   - `LocalStorageService` (`src/ai_commerce_gateway/storage/local.py`) implementing `StorageService` persisting images to local filesystem directory with URL mapping and cleanup methods.
   - Exported both adapters in `src/ai_commerce_gateway/storage/__init__.py`.
2. **Product Image Lifecycle in `ApplicationMerchantCatalogService`:**
   - Injected optional `image_repo: ProductImageRepository | None = None` and `storage_svc: StorageService | None = None` into `__init__`, maintaining 100% backwards compatibility with existing call sites.
   - Implemented `add_product_image(command: AddProductImageCommand, actor: ActorContext) -> ProductImageView`:
     - Role-based authorization (`ADMIN` or `EDITOR` required; `VIEWER` or `APPROVER` rejected with 403).
     - Product existence and tenant ownership check (404 / 403).
     - Content-Type validation against allowed set (`image/jpeg`, `image/png`, `image/webp`, `image/gif`), rejecting invalid types with 400.
     - Size limits: rejects empty content (`b""`) and files > 5MB with 400.
     - Max 3 images per product limit: strictly rejects attempt to add a 4th image with 400.
     - Sort order uniqueness: pre-checks sort_order collision (0-2) per product and returns 409 VALIDATION_ERROR.
     - Uploads binary content to `storage_svc` and stores metadata in `image_repo` (no raw blobs in DB).
     - Atomicity/cleanup: deletes uploaded storage blob if repository persistence fails.
   - Implemented `delete_product_image(command: DeleteProductImageCommand, actor: ActorContext) -> None`:
     - Role-based authorization (`ADMIN` or `EDITOR` required; `VIEWER` rejected with 403).
     - Scoped deletion in both `image_repo` and `storage_svc`.
     - Validates product and image existence (404 if not found).
   - Added helper `_get_product_images` and populated safe `images: tuple[ProductImageView, ...]` in all product read/write views (`get_product`, `list_products`, `update_product`, `publish_product`, `unpublish_product`).
3. **Buyer Catalog Service Integration:**
   - Updated `ApplicationCatalogService` in `src/ai_commerce_gateway/application/buyer_catalog_service.py` with optional `image_repo`.
   - Populates `images: tuple[ProductImageView, ...]` for published products in buyer `get_product` and `search` queries.
   - Exposes safe `url`, `alt_text`, `sort_order` while strictly withholding internal storage paths from clients.
4. **Comprehensive Unit Testing:**
   - Created `tests/unit/test_product_storage_service.py` covering:
     - `InMemoryStorageService` and `LocalStorageService` upload, delete, exists, public URL resolution.
     - Happy path multi-image lifecycle (1, 2, 3 images with sort_orders 0, 1, 2).
     - Max 3 image limit enforcement (400).
     - Duplicate sort_order conflict rejection (409).
     - Content-type validation (400 on PDF, plain text, video, BMP).
     - Empty payload (400) and > 5MB payload (400) rejections.
     - Role denial (`VIEWER` / `APPROVER` -> 403) and cross-tenant denial (403).
     - Product not found (404) and image not found (404).
     - Storage unconfigured handling (500 INTERNAL_ERROR).
     - Storage file rollback when repo insert raises an exception.
     - Buyer catalog search and get_product image projection.
     - Lifecycle preservation across product update, publish, unpublish, and listing.

**Validation:**
- `uv run ruff check .` -> PASS (0 errors)
- `uv run ruff format --check .` -> PASS (0 files need formatting)
- `uv run mypy` -> PASS (0 issues across 30 source files)
- `uv run pytest --cov=ai_commerce_gateway --cov-report=term-missing` -> PASS (166 passed, 27 skipped, 0 failed, 98% coverage; `storage/local.py` 100%, `storage/memory.py` 100%)
- `uv run alembic upgrade head --sql` -> PASS (clean schema build, no schema migrations altered)

**A7 Obstruction Check:**
A5 leaves `idempotency_key` semantics and database models completely untouched, wrapping canonical product image operations without interfering with future Phase A7 durable fingerprinted idempotency or 5-minute publication confirmation tokens.

---

## Entry — Phase A6: Merchant AI-Assisted Catalog Creation (Backend Extraction, D-010)

Date/time:       2026-09-04
Git branch:      phase/a6-merchant-dashboard
Author/Agent:    Agent A (Merchant/Catalog Lane)
Workstream:      01 Merchant Experience / 02 Catalog Domain
Phase:           A6 phase/a6-merchant-dashboard (backend extraction slice)
Status:          IMPLEMENTED — READY FOR REVIEW

**Implemented:**
1. **ProductDraftExtractor** (pplication/product_draft_extraction.py):
   - ProductDraft propose-only schema (source, missing_fields, attributes)
   - StubProductDraftExtractor: deterministic offline heuristics (rupee price, unit count, ports, title)
   - LLMProductDraftExtractor: OpenAI-compatible chat completions, strict JSON schema prompt, null-for-unstated
2. **Extraction endpoint** (pi/merchant/router.py):
   - POST /merchants/{merchant_id}/products/extract-draft — propose-only, persisted: false
   - Tenant-scoped demo actor from headers (real auth = A6 auth work); role-gated ADMIN/EDITOR
   - Stub when no llm_api_key, real LLM when configured
3. **Config**: llm_provider_url, llm_api_key (repr=False), llm_model — additive

**Trust boundary (D-010):** endpoint has NO repository access — propose-only by construction; the merchant reviews the draft and creation/publication flow through the frozen MerchantCatalogService.

**Tests (16 new):** stub heuristics, missing-field reporting, determinism, LLM valid/transport-failure/non-dict/never-invents, endpoint 200/400/403/422, no-persistence signature check.

**Validation:**
- uv run ruff check . -> PASS
- uv run mypy -> PASS (33 source files)
- uv run pytest -rs -> PASS (182 passed, 27 skipped, 0 failed)
