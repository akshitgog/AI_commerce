# Database migrations

Run `uv run alembic upgrade head` after configuring `DATABASE_URL`.

Migration files are reviewed contracts. Domain owners approve table semantics; Workstream 06 owns migration mechanics. Never rewrite an applied migration—add a new revision.

