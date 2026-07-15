"""Add administrator-reviewed cafe imports.

Revision ID: 20260712_0003
Revises: 20260712_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_0003"
down_revision = "20260712_0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"))
    op.create_index("ix_users_role", "users", ["role"])
    op.create_table("cafe_import_candidates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255)), sa.Column("latitude", sa.Numeric(10, 7)), sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("source_url", sa.String(length=500)), sa.Column("search_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending_review"),
        sa.Column("submitted_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_cafe_import_candidates_status", "cafe_import_candidates", ["status"])
    op.create_index("ix_cafe_import_candidates_submitted_by_user_id", "cafe_import_candidates", ["submitted_by_user_id"])

def downgrade() -> None:
    op.drop_table("cafe_import_candidates")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
