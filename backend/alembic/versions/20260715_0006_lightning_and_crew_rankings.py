"""Add public lightning courses and crew daily rankings.

Revision ID: 20260715_0006
Revises: 20260715_0005
"""

from alembic import op
import sqlalchemy as sa

revision = "20260715_0006"
down_revision = "20260715_0005"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("crew_courses", sa.Column("event_date", sa.Date(), nullable=True))
    op.create_index("ix_crew_courses_event_date", "crew_courses", ["event_date"])

    op.create_table(
        "lightning_courses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("start_name", sa.String(120), nullable=False),
        sa.Column("start_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("start_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("destination_name", sa.String(120), nullable=False),
        sa.Column("destination_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("destination_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("baseline_duration_seconds", sa.Integer()),
        sa.Column("ranking_mode", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
    )
    for column in ["created_by_user_id", "event_date", "ranking_mode", "is_active"]:
        op.create_index(f"ix_lightning_courses_{column}", "lightning_courses", [column])

    op.create_table(
        "lightning_course_participants",
        sa.Column("lightning_course_id", sa.BigInteger(), sa.ForeignKey("lightning_courses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "crew_daily_course_rankings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("crew_id", sa.BigInteger(), sa.ForeignKey("crews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_date", sa.Date(), nullable=False),
        sa.Column("ranking_mode", sa.String(30), nullable=False),
        sa.Column("baseline_duration_seconds", sa.Integer()),
        *timestamps(),
        sa.UniqueConstraint("crew_id", "recommendation_date", "course_id", name="uq_crew_daily_course_ranking"),
    )
    for column in ["crew_id", "course_id", "created_by_user_id", "recommendation_date", "ranking_mode"]:
        op.create_index(f"ix_crew_daily_course_rankings_{column}", "crew_daily_course_rankings", [column])

    op.add_column("drive_records", sa.Column("lightning_course_id", sa.BigInteger()))
    op.create_foreign_key(
        "fk_drive_records_lightning_course_id_lightning_courses",
        "drive_records", "lightning_courses", ["lightning_course_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_drive_records_lightning_course_id", "drive_records", ["lightning_course_id"])


def downgrade() -> None:
    op.drop_index("ix_drive_records_lightning_course_id", table_name="drive_records")
    op.drop_constraint("fk_drive_records_lightning_course_id_lightning_courses", "drive_records", type_="foreignkey")
    op.drop_column("drive_records", "lightning_course_id")
    op.drop_table("crew_daily_course_rankings")
    op.drop_table("lightning_course_participants")
    op.drop_table("lightning_courses")
    op.drop_index("ix_crew_courses_event_date", table_name="crew_courses")
    op.drop_column("crew_courses", "event_date")
