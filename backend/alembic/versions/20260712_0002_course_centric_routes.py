"""Move the catalog to a course-centric drive model.

Revision ID: 20260712_0002
Revises: 20260710_0001
Create Date: 2026-07-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260712_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("courses") as batch_op:
        batch_op.alter_column("summary", new_column_name="description", existing_type=sa.Text())
        batch_op.add_column(sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="normal"))
        batch_op.add_column(sa.Column("recommended_season", sa.String(length=20), nullable=False, server_default="all"))
        batch_op.add_column(sa.Column("recommended_time", sa.String(length=20), nullable=False, server_default="day"))
        batch_op.add_column(sa.Column("thumbnail_url", sa.String(length=500), nullable=True))
    op.create_index("ix_courses_difficulty", "courses", ["difficulty"])
    op.create_index("ix_courses_recommended_season", "courses", ["recommended_season"])

    op.create_table(
        "course_tags",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_course_tags_category", "course_tags", ["category"])
    op.create_table(
        "course_tag_assignments",
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.BigInteger(), sa.ForeignKey("course_tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "course_paths",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("course_id", sa.BigInteger(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("road_name", sa.String(length=120)),
        sa.Column("road_type", sa.String(length=30), nullable=False, server_default="unknown"),
        sa.UniqueConstraint("course_id", "sequence"),
    )
    op.create_index("ix_course_paths_course_id", "course_paths", ["course_id"])
    op.create_index("ix_course_paths_road_type", "course_paths", ["road_type"])
    op.execute(
        "INSERT INTO course_paths (course_id, sequence, latitude, longitude, road_name, road_type) "
        "SELECT course_id, sequence, latitude, longitude, name, 'unknown' FROM course_waypoints"
    )
    op.drop_table("course_waypoints")

    with op.batch_alter_table("course_cafes") as batch_op:
        batch_op.add_column(sa.Column("stop_order", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_unique_constraint(
            "uq_course_cafes_course_id_stop_order", ["course_id", "stop_order"]
        )


def downgrade() -> None:
    with op.batch_alter_table("course_cafes") as batch_op:
        batch_op.drop_constraint("uq_course_cafes_course_id_stop_order", type_="unique")
        batch_op.drop_column("stop_order")
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
    op.execute(
        "INSERT INTO course_waypoints (course_id, sequence, name, latitude, longitude, waypoint_type) "
        "SELECT course_id, sequence, COALESCE(road_name, '경유지'), latitude, longitude, road_type FROM course_paths"
    )
    op.drop_index("ix_course_paths_road_type", table_name="course_paths")
    op.drop_index("ix_course_paths_course_id", table_name="course_paths")
    op.drop_table("course_paths")
    op.drop_table("course_tag_assignments")
    op.drop_index("ix_course_tags_category", table_name="course_tags")
    op.drop_table("course_tags")
    op.drop_index("ix_courses_recommended_season", table_name="courses")
    op.drop_index("ix_courses_difficulty", table_name="courses")
    with op.batch_alter_table("courses") as batch_op:
        batch_op.drop_column("thumbnail_url")
        batch_op.drop_column("recommended_time")
        batch_op.drop_column("recommended_season")
        batch_op.drop_column("difficulty")
        batch_op.alter_column("description", new_column_name="summary", existing_type=sa.Text())
