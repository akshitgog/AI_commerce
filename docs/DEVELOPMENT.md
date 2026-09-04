# Development foundation

Milestone 0 provides contracts and infrastructure only. It intentionally contains no merchant, buyer-chat, MCP or Razorpay feature implementation.

## Repository layout

```text
src/ai_commerce_gateway/
├── api/               # HTTP adapter and health endpoints
├── application/       # future application-service implementations
├── contracts/         # frozen application/storage contracts; provisional provider port
├── core/              # settings, error envelope and opaque IDs
├── domain/            # provider-independent enums/domain vocabulary
├── infrastructure/
│   └── database/      # SQLAlchemy metadata and session factory
├── providers/         # Razorpay Test Mode adapter; B4 order/checkout initiation implemented
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
Copy-Item config/local.example.yaml config/local.yaml
# Edit config/local.yaml with the local database, LLM and required credentials.
uv sync --all-groups
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn ai_commerce_gateway.api.app:app --reload
```

Liveness is `GET /health/live`; readiness is `GET /health/ready` and checks the configured database.

## Configuration

Safe defaults and the complete typed shape live in `config/default.yaml`. Developers place local
overrides in the Git-ignored `config/local.yaml`. CI/deployment can select another YAML overlay with
the process environment variable `APP_CONFIG_FILE`; existing flat environment variables remain
higher-priority compatibility/secret-manager overrides. Unknown YAML fields and invalid values stop
startup. See `../config/README.md`.

## Validation

```powershell
uv run ruff check .
uv run mypy
uv run pytest --cov=ai_commerce_gateway
uv run alembic upgrade head --sql
```

Database access and service ports are synchronous throughout. The PostgreSQL connection integration
test runs locally only when `database.test_url` (or `TEST_DATABASE_URL`) is configured and is
mandatory in CI. Migration round-trip and PostgreSQL SQL compilation are also tested without
external services.

## Razorpay Test Mode order check

Configure only Test Mode credentials in ignored `config/local.yaml`:

```yaml
razorpay:
  key_id: rzp_test_...
  key_secret: ...
  webhook_secret: ... # distinct secret configured for the webhook endpoint
```

Then run:

```powershell
uv run pytest tests/integration/test_razorpay_test_mode.py -m provider -s
```

The adapter rejects `rzp_live_*` keys and non-approved API hosts. The test creates a Test Mode order
but performs no payment. Its console evidence redacts the provider ID. Never paste or commit the
secret or the full order identifier.

## Contract-change rule

Changes to models in `contracts/`, canonical states, table meaning, provider/storage ports or service method signatures require the process in `MASTER_DEVELOPMENT_PLAN.md`: document reason and affected workstreams, update canonical API/data docs, obtain integrator approval, then modify implementation and contract tests.
