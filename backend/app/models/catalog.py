from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


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


class Course(TimestampMixin, Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(30), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer)
    estimated_distance_meters: Mapped[int] = mapped_column(Integer)
    drive_suitability_score: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CourseWaypoint(Base):
    __tablename__ = "course_waypoints"
    __table_args__ = (UniqueConstraint("course_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    waypoint_type: Mapped[str] = mapped_column(String(30))


class CourseCafe(Base):
    __tablename__ = "course_cafes"
    __table_args__ = (UniqueConstraint("course_id", "cafe_id"),)

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    cafe_id: Mapped[int] = mapped_column(ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True)
    recommendation_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1)
