"""Add favorites, daily courses, profiles, community, and crews.

Revision ID: 20260715_0005
Revises: 20260715_0004
"""

from alembic import op
import sqlalchemy as sa

revision = "20260715_0005"
down_revision = "20260715_0004"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    with op.batch_alter_table("drive_records") as batch_op:
        batch_op.alter_column("course_id", existing_type=sa.BigInteger(), nullable=True)
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bio", sa.String(300)),
        sa.Column("profile_image_url", sa.String(500)),
        *timestamps(),
    )
    op.create_table(
        "user_vehicles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manufacturer", sa.String(80)),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_year", sa.Integer()),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
    )
    op.create_index("ix_user_vehicles_user_id", "user_vehicles", ["user_id"])
    op.create_index("ix_user_vehicles_is_primary", "user_vehicles", ["is_primary"])
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cafe_id", sa.BigInteger(), sa.ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "daily_course_recommendations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("recommendation_date", sa.Date(), nullable=False),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("headline", sa.String(120)),
        sa.UniqueConstraint(
            "recommendation_date",
            "display_order",
            name="uq_daily_course_recommendations_date_order",
        ),
        sa.UniqueConstraint(
            "recommendation_date",
            "course_id",
            name="uq_daily_course_recommendations_date_course",
        ),
    )
    op.create_index("ix_daily_course_recommendations_recommendation_date", "daily_course_recommendations", ["recommendation_date"])
    op.create_index("ix_daily_course_recommendations_course_id", "daily_course_recommendations", ["course_id"])

    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        *timestamps(),
    )
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_table(
        "post_images",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("post_id", "display_order"),
    )
    op.create_index("ix_post_images_post_id", "post_images", ["post_id"])
    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_comment_id", sa.BigInteger(), sa.ForeignKey("comments.id", ondelete="CASCADE")),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        *timestamps(),
    )
    for column in ["post_id", "author_id", "parent_comment_id", "status"]:
        op.create_index(f"ix_comments_{column}", "comments", [column])
    op.create_table(
        "post_likes",
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "user_blocks",
        sa.Column("blocker_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("blocked_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("reporter_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("details", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        *timestamps(),
    )
    for column in ["reporter_id", "target_type", "target_id", "status"]:
        op.create_index(f"ix_reports_{column}", "reports", [column])

    op.create_table(
        "crews",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(500)),
        sa.Column("image_url", sa.String(500)),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.Column("join_policy", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    for column in ["owner_id", "visibility", "join_policy", "is_active"]:
        op.create_index(f"ix_crews_{column}", "crews", [column])
    op.create_table(
        "crew_members",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crew_id", sa.BigInteger(), sa.ForeignKey("crews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("crew_id", "user_id"),
    )
    for column in ["crew_id", "user_id", "status"]:
        op.create_index(f"ix_crew_members_{column}", "crew_members", [column])
    op.create_table(
        "crew_invitations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crew_id", sa.BigInteger(), sa.ForeignKey("crews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    for column in ["crew_id", "invited_by_user_id", "expires_at"]:
        op.create_index(f"ix_crew_invitations_{column}", "crew_invitations", [column])
    op.create_table(
        "crew_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crew_id", sa.BigInteger(), sa.ForeignKey("crews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        *timestamps(),
    )
    for column in ["crew_id", "author_id", "status"]:
        op.create_index(f"ix_crew_messages_{column}", "crew_messages", [column])
    op.create_table(
        "crew_courses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crew_id", sa.BigInteger(), sa.ForeignKey("crews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("start_name", sa.String(120), nullable=False),
        sa.Column("start_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("start_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("destination_name", sa.String(120), nullable=False),
        sa.Column("destination_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("destination_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("baseline_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("ranking_mode", sa.String(30), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    for column in ["crew_id", "created_by_user_id", "ranking_mode", "is_active"]:
        op.create_index(f"ix_crew_courses_{column}", "crew_courses", [column])

    with op.batch_alter_table("drive_records") as batch_op:
        batch_op.add_column(sa.Column("crew_course_id", sa.BigInteger()))
        batch_op.create_foreign_key(
            "fk_drive_records_crew_course_id_crew_courses",
            "crew_courses",
            ["crew_course_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_drive_records_crew_course_id", "drive_records", ["crew_course_id"])


def downgrade() -> None:
    op.drop_index("ix_drive_records_crew_course_id", table_name="drive_records")
    with op.batch_alter_table("drive_records") as batch_op:
        batch_op.drop_constraint("fk_drive_records_crew_course_id_crew_courses", type_="foreignkey")
        batch_op.drop_column("crew_course_id")
        batch_op.alter_column("course_id", existing_type=sa.BigInteger(), nullable=False)
    for table in [
        "crew_courses",
        "crew_messages",
        "crew_invitations",
        "crew_members",
        "crews",
        "reports",
        "user_blocks",
        "post_likes",
        "comments",
        "post_images",
        "posts",
        "daily_course_recommendations",
        "favorites",
        "user_vehicles",
        "user_profiles",
    ]:
        op.drop_table(table)
