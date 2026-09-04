import logging
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
    "merchant_sessions",
    "used_confirmation_tokens",
}


def _preserve_logger_states() -> dict[str, bool]:
    """Alembic's fileConfig disables existing loggers; snapshot to restore."""
    manager = logging.Logger.manager
    return {
        name: logger.disabled
        for name, logger in manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }


def _restore_logger_states(snapshot: dict[str, bool]) -> None:
    manager = logging.Logger.manager
    for name, was_disabled in snapshot.items():
        logger = manager.loggerDict.get(name)
        if isinstance(logger, logging.Logger):
            logger.disabled = was_disabled


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]  # noqa: E501
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    logger_states = _preserve_logger_states()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
    finally:
        _restore_logger_states(logger_states)

    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES | {"alembic_version"}

    logger_states = _preserve_logger_states()
    try:
        command.downgrade(config, "base")
    finally:
        _restore_logger_states(logger_states)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
