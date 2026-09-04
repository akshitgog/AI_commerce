from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from ai_commerce_gateway.core.config import get_settings

EXPECTED_TABLES = {
    "merchants",
    "merchant_users",
    "products",
    "product_metadata",
    "product_images",
    "merchant_policies",
    "buyers",
    "purchase_proposals",
    "buyer_authorizations",
    "merchant_decisions",
    "transactions",
    "idempotency_records",
    "payment_attempts",
    "provider_webhooks",
    "transaction_events",
}


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]  # noqa: E501
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES | {"alembic_version"}

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
