# Workstream 06 — Data & Infrastructure

## Mission

Provide durable PostgreSQL, identity, object storage, configuration, deployment and observability foundations without owning domain policy.

## Why this workstream exists

Transaction correctness depends on durable constraints and storage. Infrastructure is shared while domain meaning stays with the owning workstream.

## Ownership

PostgreSQL connection/migrations; DB constraints implementation with domain owners; authentication infrastructure; environment/configuration; deployment; product-image object storage; observability foundations; optional worker scheduling.

## Explicit non-ownership

Catalog semantics, authorization/policy decisions, transaction transitions, provider translation, UI/chat/MCP behavior and evaluation claims.

## Inputs / dependencies

Frozen entity schemas/constraints and service needs from 02–04; deployment needs from all lanes.

## Outputs / exposed contracts

Migration framework, repositories' infrastructure primitives, authenticated actor context, storage abstraction, environment template, health/telemetry and deployable runtime.

## Relevant domain entities

Mechanically supports all canonical entities without owning their business meaning.

## Relevant database tables

Supports all tables. Logical ownership remains: catalog tables 02, transaction/audit tables 03, provider tables 04. Actual image bytes live in object storage; `ProductImage` metadata lives in PostgreSQL.

## Relevant API/application services

`storage.upload_product_image`, `storage.delete_product_image`, `storage.get_public_url`, auth/session middleware, database unit-of-work and worker scheduling.

## Relevant UI surfaces

None, except infrastructure support for login and upload transport.

## Directory ownership

Migrations framework, DB/session/config/auth/storage/deployment/observability infrastructure and tests. Domain migrations are co-reviewed by their logical owner.

## Shared contracts consumed

Canonical entities, unique/check/foreign-key requirements, actor context, storage contract and secret/config requirements.

## Shared contracts exposed

DB transaction/unit-of-work primitives, authenticated actor context, storage interface, config schema, health/telemetry conventions.

## Security/trust rules

Keep secrets out of source/logs; least-privilege storage and DB access; validate upload type/size; preserve tenant context; use durable uniqueness; redact provider/user data; separate Test Mode configuration.

## Required implementation tasks

1. Configure PostgreSQL (preferred Supabase PostgreSQL) and migrations.
2. Implement reviewed constraints/indexes for canonical records.
3. Implement auth/tenant context infrastructure.
4. Implement Supabase Storage or equivalent behind the storage abstraction.
5. Provide environment template, local/deployed setup, health checks and correlation-ready logging.

## Phase participation

M0 infrastructure is frozen. Subsequent infrastructure work is a bounded contribution to the active
owning phase, not an independent catch-all lane: A1–A5 may request reviewed catalog migrations,
identity or storage work; B1–B6 may request reviewed transaction/provider migrations, locking,
worker or configuration work. Infrastructure changes use the requesting phase branch and are
co-reviewed by this workstream and the logical domain owner.

Do not create a parallel infrastructure phase that changes shared schema underneath active lanes.
Every migration must be called out in the phase evidence record and validated through real
PostgreSQL where correctness depends on PostgreSQL behavior.

## Required tests

Migration up/down or forward verification, constraints, transaction/locking behavior, auth context, cross-tenant denial support, storage upload/delete/URL behavior, restart persistence, config failure and secret redaction.

## Evidence required

Migration output/schema snapshot, persistence/restart test, storage object plus metadata proof, deployment health output and redacted configuration documentation.

## Integration points

02 catalog/images, 03 transaction/idempotency/audit, 04 attempts/webhooks/reconciliation, 01/05 auth and 07 environments.

## Completion criteria

M0 infrastructure exists; data survives restart; constraints enforce frozen invariants; 1–3 product images work through the abstraction; environments are reproducible.

## Known non-goals

Microservice platform, Redis as a correctness requirement, advanced CDN/image processing, production-scale operations and multiple payment providers.

## Things this agent must never do

Choose domain semantics unilaterally, weaken constraints to satisfy tests, store image blobs in PostgreSQL, expose secrets, make in-memory locks authoritative or claim E2E/provider success.

## Questions/escalation triggers

Escalate schema/constraint conflicts, auth identity-model changes, public-vs-signed URL choice, migration ownership collisions or infrastructure requiring domain/API changes.

See `../../MASTER_DEVELOPMENT_PLAN.md`, `../../PHASE_EXECUTION.md`, `../../DATA_MODEL.md`,
`../../API.md` and `../../SECURITY.md`.
