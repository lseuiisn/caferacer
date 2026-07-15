from enum import StrEnum


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    KAKAO = "kakao"


class UserStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    SUSPENDED = "suspended"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class ConsentType(StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"
    LOCATION = "location"


class RecordStatus(StrEnum):
    RECORDING = "recording"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RecordValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


class NavigationAnchorType(StrEnum):
    START = "start"
    WAYPOINT = "waypoint"
    DESTINATION = "destination"


class ContentStatus(StrEnum):
    ACTIVE = "active"
    HIDDEN = "hidden"
    DELETED = "deleted"


class CrewVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class CrewJoinPolicy(StrEnum):
    OPEN = "open"
    APPROVAL = "approval"
    INVITE_ONLY = "invite_only"


class CrewMemberRole(StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


class CrewMemberStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    LEFT = "left"
    REMOVED = "removed"


class RankingMode(StrEnum):
    FASTEST = "fastest"
    CLOSEST_TO_BASELINE = "closest_to_baseline"


class ReportStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
