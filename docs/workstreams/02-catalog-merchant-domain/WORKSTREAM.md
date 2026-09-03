# Workstream 02 — Catalog & Merchant Domain

## Mission

Own trusted merchant-scoped catalog state and expose the same published-product services to the dashboard, reference buyer chat and MCP adapter.

## Why this workstream exists

Price, stock, version and publication are trusted commercial inputs. Centralizing them prevents interfaces from inventing different catalog truth.

## Ownership

`Merchant`, `MerchantUser`, `Product`, `ProductMetadata`, `ProductImage`, `MerchantPolicy`; tenant-scoped CRUD; publication/versioning; stock; CSV import; published search/read; image metadata lifecycle.

## Explicit non-ownership

Buyer consent, proposal/transaction state, payment attempts, Razorpay calls, provider truth, chat orchestration and image binary infrastructure.

## Inputs / dependencies

Identity/DB/storage primitives from 06 and frozen entity/service contracts from M0.

## Outputs / exposed contracts

`catalog.search`, `catalog.get_product`, merchant catalog commands, policy persistence and image metadata operations. Reads return only safe published fields to buyer surfaces.

## Relevant domain entities

Logically owns `Merchant`, `MerchantUser`, `Product`, `ProductMetadata`, `ProductImage` and `MerchantPolicy`.

## Relevant database tables

Owns the corresponding six tables and their domain constraints. Coordinates migration mechanics with 06.

## Relevant API/application services

Merchant product CRUD/publish/unpublish/import; buyer catalog search/product read; image upload registration/delete/list; policy read/update.

## Relevant UI surfaces

Supplies data to dashboard and buyer product cards, including ordered safe image URL metadata.

## Directory ownership

Merchant/catalog domain, application services, repositories, schemas and owned tests. Storage implementation remains in 06.

## Shared contracts consumed

Identity/tenant context, storage abstraction, IDs/errors, DB transaction conventions.

## Shared contracts exposed

Catalog and policy entities/services plus buyer-safe catalog response models. Price/version/stock are server-owned.

## Security/trust rules

Scope every write/read by merchant ownership; expose only `PUBLISHED` products to buyers; AI enrichment may edit descriptive metadata only after merchant review; validate image type/size/count; never store image bytes in PostgreSQL.

## Required implementation tasks

1. Implement merchant/membership and catalog repositories/services.
2. Enforce SKU uniqueness, versioning, publication and stock rules.
3. Implement tenant-scoped search/read and CSV validation/import.
4. Integrate storage abstraction and persist ordered `ProductImage` rows.
5. Implement/version merchant policy persistence.

## Required tests

Unpublished invisible, published visible, tenant denial, trusted integer price, version increments, stock constraints, CSV atomic/partial behavior per frozen contract, image count/order/delete, safe buyer response, policy modes and repository constraints.

## Evidence required

Unit/integration/contract output and database evidence for constraints; M1 E2E evidence is captured with 07.

## Integration points

01 dashboard, 03 proposal revalidation/policy evaluation, 05 buyer/MCP adapters, 06 DB/storage and 07 E2E.

## Completion criteria

M1 passes through the shared service contracts and all three interfaces observe identical published catalog truth.

## Known non-goals

Cross-merchant ranking, recommendation, campaigns, advanced inventory allocation, image generation/moderation/CV and CDN optimization.

## Things this agent must never do

Create transactions, call Razorpay, trust client totals, leak draft/cross-tenant data, put financial rules in MCP-specific code, or store raw image blobs in PostgreSQL.

## Questions/escalation triggers

Escalate entity/service signature changes, stock-reservation semantics, product-version invalidation rules, CSV behavior or public-vs-signed image URLs.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../API.md`, `../../DATA_MODEL.md` and `../../SECURITY.md`.
