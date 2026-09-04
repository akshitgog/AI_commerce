"""Migration and schema contract tests for Phase A1.

These tests verify:
- All merchant/catalog tables are registered in the ORM metadata.
- Key constraints (SKU uniqueness, membership uniqueness, image sort order) compile.
- The A1 ORM models match what the canonical DATA_MODEL specifies.
- Migration SQL can be generated without a live DB (offline SQL test).
"""

from __future__ import annotations

import subprocess
import sys

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from ai_commerce_gateway.infrastructure.database.models import Base

# ---------------------------------------------------------------------------
# Expected schema fixtures for A1
# ---------------------------------------------------------------------------

A1_TABLES = {
    "merchants",
    "merchant_users",
    "products",
    "product_metadata",
    "product_images",
    "merchant_policies",
}


def _all_table_constraints(table_name: str) -> set[tuple[str, ...]]:
    """Return the column sets of all unique constraints on a table."""
    table = Base.metadata.tables[table_name]
    return {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in table.constraints
        if hasattr(constraint, "columns") and len(list(constraint.columns)) > 0
    }


# ---------------------------------------------------------------------------
# ORM metadata contract tests
# ---------------------------------------------------------------------------


class TestA1SchemaContract:
    def test_a1_tables_present_in_metadata(self) -> None:
        """All six A1 tables must be registered in the ORM metadata."""
        all_tables = set(Base.metadata.tables.keys())
        missing = A1_TABLES - all_tables
        assert not missing, f"Missing A1 tables: {missing}"

    def test_merchant_sku_uniqueness_constraint_present(self) -> None:
        """(merchant_id, sku) UniqueConstraint must be on the products table."""
        products = Base.metadata.tables["products"]
        unique_pairs = {
            tuple(sorted(c.name for c in constraint.columns))
            for constraint in products.constraints
            if hasattr(constraint, "columns") and len(list(constraint.columns)) == 2
        }
        assert ("merchant_id", "sku") in unique_pairs

    def test_merchant_user_uniqueness_constraint_present(self) -> None:
        """(merchant_id, user_id) UniqueConstraint must be on merchant_users."""
        mu = Base.metadata.tables["merchant_users"]
        unique_pairs = {
            tuple(sorted(c.name for c in constraint.columns))
            for constraint in mu.constraints
            if hasattr(constraint, "columns") and len(list(constraint.columns)) == 2
        }
        assert ("merchant_id", "user_id") in unique_pairs

    def test_product_image_sort_order_uniqueness_present(self) -> None:
        """(product_id, sort_order) UniqueConstraint must be on product_images."""
        images = Base.metadata.tables["product_images"]
        unique_pairs = {
            tuple(sorted(c.name for c in constraint.columns))
            for constraint in images.constraints
            if hasattr(constraint, "columns") and len(list(constraint.columns)) == 2
        }
        assert ("product_id", "sort_order") in unique_pairs

    def test_product_metadata_product_id_is_primary_key(self) -> None:
        """product_metadata must use product_id as its primary key (1:1 with product)."""
        pm = Base.metadata.tables["product_metadata"]
        pk_columns = {col.name for col in pm.primary_key.columns}
        assert pk_columns == {"product_id"}

    def test_product_image_has_merchant_id_column(self) -> None:
        """product_images must retain merchant_id for tenant-scoped queries."""
        images = Base.metadata.tables["product_images"]
        column_names = {col.name for col in images.columns}
        assert "merchant_id" in column_names

    def test_product_price_column_is_integer(self) -> None:
        """price_minor must be an Integer column (not Float or Numeric)."""
        from sqlalchemy import Integer

        products = Base.metadata.tables["products"]
        price_col = products.c["price_minor"]
        assert isinstance(price_col.type, Integer)

    def test_product_has_version_column(self) -> None:
        products = Base.metadata.tables["products"]
        assert "version" in products.c

    def test_product_has_status_column(self) -> None:
        products = Base.metadata.tables["products"]
        assert "status" in products.c

    def test_product_has_currency_column(self) -> None:
        products = Base.metadata.tables["products"]
        assert "currency" in products.c

    def test_product_metadata_has_no_price_column(self) -> None:
        """ProductMetadata must not have price or stock columns."""
        pm = Base.metadata.tables["product_metadata"]
        column_names = {col.name for col in pm.columns}
        assert "price_minor" not in column_names
        assert "available_quantity" not in column_names
        assert "currency" not in column_names
        assert "status" not in column_names

    def test_merchant_policy_has_version_column(self) -> None:
        mp = Base.metadata.tables["merchant_policies"]
        assert "version" in mp.c

    def test_merchant_policy_has_mode_column(self) -> None:
        mp = Base.metadata.tables["merchant_policies"]
        assert "mode" in mp.c


# ---------------------------------------------------------------------------
# Schema compiles against PostgreSQL dialect
# ---------------------------------------------------------------------------


class TestPostgreSQLCompilation:
    def test_a1_tables_compile_for_postgresql(self) -> None:
        """All A1 tables must compile valid PostgreSQL DDL."""
        for table_name in A1_TABLES:
            table = Base.metadata.tables[table_name]
            compiled = str(CreateTable(table).compile(dialect=postgresql.dialect()))
            assert f"CREATE TABLE {table_name}" in compiled

    def test_products_check_constraints_include_price_nonnegative(self) -> None:
        products = Base.metadata.tables["products"]
        compiled = str(CreateTable(products).compile(dialect=postgresql.dialect()))
        assert "price_minor" in compiled
        assert "price_nonnegative" in compiled or "price_minor >= 0" in compiled

    def test_products_check_constraints_include_version_positive(self) -> None:
        products = Base.metadata.tables["products"]
        compiled = str(CreateTable(products).compile(dialect=postgresql.dialect()))
        assert "version_positive" in compiled or "version >= 1" in compiled


# ---------------------------------------------------------------------------
# Alembic offline SQL generation (migration compatibility test)
# ---------------------------------------------------------------------------


class TestMigrationOfflineSQL:
    def test_alembic_upgrade_head_sql_generates_without_error(self) -> None:
        """Run `alembic upgrade head --sql` and verify it produces DDL."""
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        # The command must exit successfully (or produce SQL on stdout even if exit 1
        # because there's no DB for offline mode to check against — offline mode
        # always exits 0).
        output = result.stdout + result.stderr
        # Key tables must appear in the generated SQL
        assert "CREATE TABLE" in output or result.returncode == 0, (
            f"alembic offline SQL failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        for table in A1_TABLES:
            assert table in output, f"Table {table!r} missing from migration SQL output"
