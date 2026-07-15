from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    ContentStatus,
    CrewJoinPolicy,
    CrewMemberRole,
    CrewMemberStatus,
    CrewVisibility,
    RankingMode,
    ReportStatus,
)


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str | None] = mapped_column(String(300))
    profile_image_url: Mapped[str | None] = mapped_column(String(500))


class UserVehicle(TimestampMixin, Base):
    __tablename__ = "user_vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    manufacturer: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str] = mapped_column(String(100))
    model_year: Mapped[int | None] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "cafe_id"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    cafe_id: Mapped[int] = mapped_column(
        ForeignKey("cafes.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DailyCourseRecommendation(Base):
    __tablename__ = "daily_course_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_date",
            "display_order",
            name="uq_daily_course_recommendations_date_order",
        ),
        UniqueConstraint(
            "recommendation_date",
            "course_id",
            name="uq_daily_course_recommendations_date_course",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_date: Mapped[date] = mapped_column(Date, index=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer)
    headline: Mapped[str | None] = mapped_column(String(120))


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False), default=ContentStatus.ACTIVE, index=True
    )


class PostImage(Base):
    __tablename__ = "post_images"
    __table_args__ = (UniqueConstraint("post_id", "display_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    image_url: Mapped[str] = mapped_column(String(500))
    display_order: Mapped[int] = mapped_column(Integer)


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String(1000))
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False), default=ContentStatus.ACTIVE, index=True
    )


class PostLike(Base):
    __tablename__ = "post_likes"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserBlock(Base):
    __tablename__ = "user_blocks"

    blocker_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target_type: Mapped[str] = mapped_column(String(30), index=True)
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(50))
    details: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False), default=ReportStatus.PENDING, index=True
    )


class Crew(TimestampMixin, Base):
    __tablename__ = "crews"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    visibility: Mapped[CrewVisibility] = mapped_column(
        Enum(CrewVisibility, native_enum=False), index=True
    )
    join_policy: Mapped[CrewJoinPolicy] = mapped_column(
        Enum(CrewJoinPolicy, native_enum=False), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CrewMember(TimestampMixin, Base):
    __tablename__ = "crew_members"
    __table_args__ = (UniqueConstraint("crew_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[CrewMemberRole] = mapped_column(
        Enum(CrewMemberRole, native_enum=False), default=CrewMemberRole.MEMBER
    )
    status: Mapped[CrewMemberStatus] = mapped_column(
        Enum(CrewMemberStatus, native_enum=False),
        default=CrewMemberStatus.PENDING,
        index=True,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CrewInvitation(TimestampMixin, Base):
    __tablename__ = "crew_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"), index=True
    )
    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CrewMessage(TimestampMixin, Base):
    __tablename__ = "crew_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(String(2000))
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False), default=ContentStatus.ACTIVE, index=True
    )


class CrewCourse(TimestampMixin, Base):
    __tablename__ = "crew_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    start_name: Mapped[str] = mapped_column(String(120))
    start_latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    start_longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    destination_name: Mapped[str] = mapped_column(String(120))
    destination_latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    destination_longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    baseline_duration_seconds: Mapped[int] = mapped_column(Integer)
    ranking_mode: Mapped[RankingMode] = mapped_column(
        Enum(RankingMode, native_enum=False), index=True
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class LightningCourse(TimestampMixin, Base):
    __tablename__ = "lightning_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    start_name: Mapped[str] = mapped_column(String(120))
    start_latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    start_longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    destination_name: Mapped[str] = mapped_column(String(120))
    destination_latitude: Mapped[float] = mapped_column(Numeric(10, 7))
    destination_longitude: Mapped[float] = mapped_column(Numeric(10, 7))
    baseline_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    ranking_mode: Mapped[RankingMode] = mapped_column(
        Enum(RankingMode, native_enum=False), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class LightningCourseParticipant(Base):
    __tablename__ = "lightning_course_participants"
    __table_args__ = (UniqueConstraint("lightning_course_id", "user_id"),)

    lightning_course_id: Mapped[int] = mapped_column(
        ForeignKey("lightning_courses.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CrewDailyCourseRanking(TimestampMixin, Base):
    __tablename__ = "crew_daily_course_rankings"
    __table_args__ = (
        UniqueConstraint(
            "crew_id", "recommendation_date", "course_id",
            name="uq_crew_daily_course_ranking",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    crew_id: Mapped[int] = mapped_column(
        ForeignKey("crews.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    recommendation_date: Mapped[date] = mapped_column(Date, index=True)
    ranking_mode: Mapped[RankingMode] = mapped_column(
        Enum(RankingMode, native_enum=False), index=True
    )
    baseline_duration_seconds: Mapped[int | None] = mapped_column(Integer)
