from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from ai_commerce_gateway.infrastructure.database.models import Base

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


def test_all_canonical_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_schema_compiles_for_postgresql() -> None:
    statements: list[str] = []
    create_mock_engine("postgresql+psycopg://", lambda sql, *_: statements.append(str(sql)))
    for table in Base.metadata.sorted_tables:
        compiled = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert f"CREATE TABLE {table.name}" in compiled


def test_critical_uniqueness_constraints_are_present() -> None:
    idempotency = Base.metadata.tables["idempotency_records"]
    attempts = Base.metadata.tables["payment_attempts"]
    transaction = Base.metadata.tables["transactions"]
    assert any(
        {column.name for column in constraint.columns}
        == {"actor_id", "operation", "idempotency_key"}
        for constraint in idempotency.constraints
        if hasattr(constraint, "columns")
    )
    assert any(
        {column.name for column in constraint.columns} == {"transaction_id", "attempt_number"}
        for constraint in attempts.constraints
        if hasattr(constraint, "columns")
    )
    assert any(
        {column.name for column in constraint.columns} == {"proposal_id"}
        for constraint in transaction.constraints
        if hasattr(constraint, "columns")
    )
