# Database migrations

Run `uv run alembic upgrade head` after configuring `database.url` in `config/local.yaml`.
CI/deployment may instead use `APP_CONFIG_FILE` or the `DATABASE_URL` environment override.

Migration files are reviewed contracts. Domain owners approve table semantics; Workstream 06 owns migration mechanics. Never rewrite an applied migration—add a new revision.

