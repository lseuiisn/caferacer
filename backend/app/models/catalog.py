from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import NavigationAnchorType


class Cafe(TimestampMixin, Base):
    __tablename__ = "cafes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7), index=True)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), index=True)
    phone_number: Mapped[str | None] = mapped_column(String(30))
    business_hours: Mapped[str | None] = mapped_column(Text)
    price_range: Mapped[str | None] = mapped_column(String(20), index=True)
    parking_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CafeImage(TimestampMixin, Base):
    __tablename__ = "cafe_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    source_url: Mapped[str | None] = mapped_column(String(500))
    license_note: Mapped[str | None] = mapped_column(String(255))


class CafeTag(Base):
    __tablename__ = "cafe_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(30), index=True)


class CafeTagAssignment(Base):
    __tablename__ = "cafe_tag_assignments"
    __table_args__ = (UniqueConstraint("cafe_id", "tag_id"),)

    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("cafe_tags.id", ondelete="CASCADE"), primary_key=True)


class CafeDataSource(Base):
    __tablename__ = "cafe_data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(500))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CafeImportCandidate(TimestampMixin, Base):
    __tablename__ = "cafe_import_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    source_url: Mapped[str | None] = mapped_column(String(500))
    search_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending_review", index=True)
    submitted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(30), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer)
    estimated_distance_meters: Mapped[int] = mapped_column(Integer)
    drive_suitability_score: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    difficulty: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    recommended_season: Mapped[str] = mapped_column(String(20), default="all", index=True)
    recommended_time: Mapped[str] = mapped_column(String(20), default="day")
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CourseTag(Base):
    __tablename__ = "course_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(30), index=True)


class CourseTagAssignment(Base):
    __tablename__ = "course_tag_assignments"
    __table_args__ = (UniqueConstraint("course_id", "tag_id"),)

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("course_tags.id", ondelete="CASCADE"), primary_key=True)


class CoursePath(Base):
    __tablename__ = "course_paths"
    __table_args__ = (UniqueConstraint("course_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    road_name: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    road_type: Mapped[str] = mapped_column(String(30), default="unknown", index=True)


class CourseNavigationAnchor(Base):
    """Small, ordered set of points handed to the external TMAP app."""

    __tablename__ = "course_navigation_anchors"
    __table_args__ = (UniqueConstraint("course_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    anchor_type: Mapped[NavigationAnchorType] = mapped_column(
        Enum(NavigationAnchorType, native_enum=False), index=True
    )
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    pass_radius_meters: Mapped[int] = mapped_column(Integer, default=100)


class CourseCafe(Base):
    __tablename__ = "course_cafes"
    __table_args__ = (UniqueConstraint("course_id", "cafe_id"),)

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True)
    stop_order: Mapped[int] = mapped_column(Integer, default=1)
    recommendation_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1)
