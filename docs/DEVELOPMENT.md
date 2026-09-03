# Development foundation

Milestone 0 provides contracts and infrastructure only. It intentionally contains no merchant, buyer-chat, MCP or Razorpay feature implementation.

## Repository layout

```text
src/ai_commerce_gateway/
├── api/               # HTTP adapter and health endpoints
├── application/       # future application-service implementations
├── contracts/         # frozen DTOs and service/provider/storage ports
├── core/              # settings, error envelope and opaque IDs
├── domain/            # provider-independent enums/domain vocabulary
├── infrastructure/
│   └── database/      # SQLAlchemy metadata and session factory
├── providers/         # future Razorpay adapter
└── storage/           # future object-storage adapter

migrations/            # Alembic environment and versioned schema
tests/
├── unit/
├── contract/
└── integration/
```

Reference Buyer Chat and Remote MCP will remain separate adapters. Neither package belongs in the trusted transaction authority, and both must consume the same application-service contracts.

## Local setup

```powershell
Copy-Item .env.example .env
uv sync --all-groups
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn ai_commerce_gateway.api.app:app --reload
```

Liveness is `GET /health/live`; readiness is `GET /health/ready` and checks the configured database.

## Validation

```powershell
uv run ruff check .
uv run mypy
uv run pytest --cov=ai_commerce_gateway
uv run alembic upgrade head --sql
```

The PostgreSQL connection integration test runs only when `TEST_DATABASE_URL` is configured. Migration round-trip and PostgreSQL SQL compilation are always tested without external services.

## Contract-change rule

Changes to models in `contracts/`, canonical states, table meaning, provider/storage ports or service method signatures require the process in `MASTER_DEVELOPMENT_PLAN.md`: document reason and affected workstreams, update canonical API/data docs, obtain integrator approval, then modify implementation and contract tests.
