# flow.md — Current Implemented System

## Status

Implementation status: MILESTONE 0 FOUNDATION FROZEN

This file must describe only the accepted implemented system.

Do not copy planned architecture here until it exists in code.

---

## Repository Structure

```text
src/ai_commerce_gateway/
├── api/               HTTP adapter and health endpoints
├── application/       feature-service implementation boundary
├── contracts/         frozen DTOs and service/provider/storage ports
├── core/              settings, errors and opaque IDs
├── domain/            provider-independent states and vocabulary
├── infrastructure/    database engine/session and canonical persistence models
├── providers/         future Razorpay adapter boundary
└── storage/           future object-storage adapter boundary

migrations/            Alembic environment and initial canonical schema
tests/                 unit, contract and integration test layers
```

## Runtime Components

FastAPI application factory with liveness and database-readiness endpoints. SQLAlchemy provides the PostgreSQL connection/session boundary. No feature services, merchant UI, buyer chat, MCP server or Razorpay adapter are implemented yet.

## Merchant Flow

Not implemented.

## Catalog Flow

Not implemented. Canonical catalog DTOs and service interface are frozen.

## MCP / AI Buyer Flow

Not implemented. Reference Buyer Chat and Remote MCP remain separate future adapters over the same frozen application-service contracts.

## Buyer Authorization Flow

Not implemented. Bounded authorization DTOs and service interface are frozen.

## Merchant Policy / Review Flow

Not implemented. Policy modes and decision contracts are frozen.

## Transaction Lifecycle

Not implemented. Canonical internal states are defined in the domain package and persistence schema.

## Razorpay Test Mode Integration

Not implemented. Only the provider-neutral service port and persistence records exist.

## Idempotency Flow

The request/response contract and durable `IdempotencyRecord` schema exist. Execution behavior is not implemented.

## Verification / Reconciliation Flow

Not implemented. Provider lookup ports and `UNKNOWN`/`RECONCILING` states are defined.

## Audit Flow

The append-only `TransactionEvent` schema and audit response contract exist. Event-writing behavior is not implemented.

## Dashboard Flow

Not implemented.

## Persistence

PostgreSQL is the target database. Alembic has an initial migration for all 15 canonical tables. Product image bytes remain outside PostgreSQL; only metadata is modeled.

## Background Jobs

Not implemented.

## Deployment / Local Runtime

Local setup uses `uv`, FastAPI/Uvicorn, Alembic and optional Docker Compose PostgreSQL. Configuration comes from environment variables documented in `.env.example`.

## Current Known Limitations

- Only Milestone 0 foundation is implemented; no commerce feature journey exists.
- The PostgreSQL-backed M0 workflow passed before the foundation was frozen at tag `m0-foundation`.
- Object storage, Razorpay, authentication, buyer chat, MCP and domain services are interfaces/placeholders only.
