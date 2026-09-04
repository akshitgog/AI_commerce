"""add durable merchant session and used-confirmation-token stores

Revision ID: b7f3c91d5e20
Revises: 2a8a78d61842
Create Date: 2026-09-04 12:00:00.000000

P0-2/P0-4/P0-5: durable, restart-safe stores for merchant sessions (hashed
tokens only) and consumed publication-confirmation JTIs (replay protection
that survives restarts).  Approved schema change per the P0 directive.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7f3c91d5e20"
down_revision: str | Sequence[str] | None = "2a8a78d61842"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "merchant_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"], ["merchants.id"], name=op.f("fk_merchant_sessions_merchant_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchant_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_merchant_sessions_token_hash")),
    )
    op.create_index(
        op.f("ix_merchant_sessions_token_hash"),
        "merchant_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_merchant_sessions_merchant_id"),
        "merchant_sessions",
        ["merchant_id"],
        unique=False,
    )
    op.create_table(
        "used_confirmation_tokens",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("jti", name=op.f("pk_used_confirmation_tokens")),
    )
    op.create_index(
        op.f("ix_used_confirmation_tokens_merchant_id"),
        "used_confirmation_tokens",
        ["merchant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_used_confirmation_tokens_merchant_id"), table_name="used_confirmation_tokens"
    )
    op.drop_table("used_confirmation_tokens")
    op.drop_index(op.f("ix_merchant_sessions_merchant_id"), table_name="merchant_sessions")
    op.drop_index(op.f("ix_merchant_sessions_token_hash"), table_name="merchant_sessions")
    op.drop_table("merchant_sessions")
