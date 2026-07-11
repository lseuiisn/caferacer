"""Initial authentication and catalogue schema.

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("nickname", sa.String(length=50)),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        *timestamp_columns(),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_table(
        "user_identities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("provider", "provider_subject"),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
    op.create_table(
        "user_consents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(length=20), nullable=False),
        sa.Column("document_version", sa.String(length=30), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "consent_type", "document_version"),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("device_name", sa.String(length=100)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_expires_at", "refresh_sessions", ["expires_at"])

    op.create_table(
        "cafes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("phone_number", sa.String(length=30)),
        sa.Column("business_hours", sa.Text()),
        sa.Column("price_range", sa.String(length=20)),
        sa.Column("parking_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        *timestamp_columns(),
    )
    for column in ["name", "latitude", "longitude", "price_range", "parking_available", "is_active"]:
        op.create_index(f"ix_cafes_{column}", "cafes", [column])
    op.create_table(
        "cafe_images",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cafe_id", sa.BigInteger(), sa.ForeignKey("cafes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("alt_text", sa.String(length=255)),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_url", sa.String(length=500)),
        sa.Column("license_note", sa.String(length=255)),
        *timestamp_columns(),
    )
    op.create_index("ix_cafe_images_cafe_id", "cafe_images", ["cafe_id"])
    op.create_table(
        "cafe_tags",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_cafe_tags_category", "cafe_tags", ["category"])
    op.create_table(
        "cafe_tag_assignments",
        sa.Column("cafe_id", sa.BigInteger(), sa.ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.BigInteger(), sa.ForeignKey("cafe_tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "cafe_data_sources",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cafe_id", sa.BigInteger(), sa.ForeignKey("cafes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_cafe_data_sources_cafe_id", "cafe_data_sources", ["cafe_id"])

    op.create_table(
        "courses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_distance_meters", sa.Integer(), nullable=False),
        sa.Column("drive_suitability_score", sa.Numeric(4, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamp_columns(),
    )
    op.create_index("ix_courses_region", "courses", ["region"])
    op.create_index("ix_courses_is_active", "courses", ["is_active"])
    op.create_table(
        "course_waypoints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("waypoint_type", sa.String(length=30), nullable=False),
        sa.UniqueConstraint("course_id", "sequence"),
    )
    op.create_index("ix_course_waypoints_course_id", "course_waypoints", ["course_id"])
    op.create_table(
        "course_cafes",
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cafe_id", sa.BigInteger(), sa.ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recommendation_weight", sa.Numeric(5, 2), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    for table in [
        "course_cafes", "course_waypoints", "courses", "cafe_data_sources", "cafe_tag_assignments",
        "cafe_tags", "cafe_images", "cafes", "refresh_sessions", "user_consents", "user_identities", "users",
    ]:
        op.drop_table(table)
