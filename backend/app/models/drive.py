from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import RecordStatus, RecordValidationStatus


class DriveRecord(TimestampMixin, Base):
    __tablename__ = "drive_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), index=True
    )
    crew_course_id: Mapped[int | None] = mapped_column(
        ForeignKey("crew_courses.id", ondelete="SET NULL"), index=True
    )
    lightning_course_id: Mapped[int | None] = mapped_column(
        ForeignKey("lightning_courses.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False),
        default=RecordStatus.RECORDING,
        index=True,
    )
    validation_status: Mapped[RecordValidationStatus] = mapped_column(
        Enum(RecordValidationStatus, native_enum=False),
        default=RecordValidationStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[int] = mapped_column(Integer, default=0)
    baseline_delta_seconds: Mapped[int | None] = mapped_column(Integer)
    path_coverage_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    ranking_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class DriveRecordPoint(Base):
    __tablename__ = "drive_record_points"
    __table_args__ = (UniqueConstraint("drive_record_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    drive_record_id: Mapped[int] = mapped_column(
        ForeignKey("drive_records.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    accuracy_meters: Mapped[float | None] = mapped_column(Numeric(7, 2))
    speed_mps: Mapped[float | None] = mapped_column(Numeric(7, 2))
    heading_degrees: Mapped[float | None] = mapped_column(Numeric(6, 2))
    distance_from_path_meters: Mapped[float | None] = mapped_column(Numeric(9, 2))


class DriveRecordAnchorPass(Base):
    __tablename__ = "drive_record_anchor_passes"
    __table_args__ = (UniqueConstraint("drive_record_id", "anchor_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    drive_record_id: Mapped[int] = mapped_column(
        ForeignKey("drive_records.id", ondelete="CASCADE"), index=True
    )
    anchor_id: Mapped[int] = mapped_column(
        ForeignKey("course_navigation_anchors.id", ondelete="CASCADE"), index=True
    )
    passed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    minimum_distance_meters: Mapped[float] = mapped_column(Numeric(9, 2))
