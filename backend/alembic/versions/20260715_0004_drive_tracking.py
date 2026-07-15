"""Add external navigation anchors and GPS drive tracking.

Revision ID: 20260715_0004
Revises: 20260712_0003
Create Date: 2026-07-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260715_0004"
down_revision = "20260712_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course_navigation_anchors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "course_id",
            sa.BigInteger(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("anchor_type", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("pass_radius_meters", sa.Integer(), nullable=False, server_default="100"),
        sa.UniqueConstraint("course_id", "sequence"),
    )
    op.create_index(
        "ix_course_navigation_anchors_course_id",
        "course_navigation_anchors",
        ["course_id"],
    )
    op.create_index(
        "ix_course_navigation_anchors_anchor_type",
        "course_navigation_anchors",
        ["anchor_type"],
    )

    op.create_table(
        "drive_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.BigInteger(),
            sa.ForeignKey("courses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="RECORDING"),
        sa.Column(
            "validation_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("distance_meters", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baseline_delta_seconds", sa.Integer()),
        sa.Column(
            "path_coverage_percent", sa.Numeric(5, 2), nullable=False, server_default="0"
        ),
        sa.Column("ranking_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
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
    )
    for column in [
        "user_id",
        "course_id",
        "status",
        "validation_status",
        "started_at",
        "ranking_eligible",
    ]:
        op.create_index(f"ix_drive_records_{column}", "drive_records", [column])

    op.create_table(
        "drive_record_points",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "drive_record_id",
            sa.BigInteger(),
            sa.ForeignKey("drive_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("accuracy_meters", sa.Numeric(7, 2)),
        sa.Column("speed_mps", sa.Numeric(7, 2)),
        sa.Column("heading_degrees", sa.Numeric(6, 2)),
        sa.Column("distance_from_path_meters", sa.Numeric(9, 2)),
        sa.UniqueConstraint("drive_record_id", "sequence"),
    )
    op.create_index(
        "ix_drive_record_points_drive_record_id", "drive_record_points", ["drive_record_id"]
    )
    op.create_index(
        "ix_drive_record_points_recorded_at", "drive_record_points", ["recorded_at"]
    )

    op.create_table(
        "drive_record_anchor_passes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "drive_record_id",
            sa.BigInteger(),
            sa.ForeignKey("drive_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "anchor_id",
            sa.BigInteger(),
            sa.ForeignKey("course_navigation_anchors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("passed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minimum_distance_meters", sa.Numeric(9, 2), nullable=False),
        sa.UniqueConstraint("drive_record_id", "anchor_id"),
    )
    op.create_index(
        "ix_drive_record_anchor_passes_drive_record_id",
        "drive_record_anchor_passes",
        ["drive_record_id"],
    )
    op.create_index(
        "ix_drive_record_anchor_passes_anchor_id",
        "drive_record_anchor_passes",
        ["anchor_id"],
    )


def downgrade() -> None:
    op.drop_table("drive_record_anchor_passes")
    op.drop_table("drive_record_points")
    op.drop_table("drive_records")
    op.drop_table("course_navigation_anchors")
