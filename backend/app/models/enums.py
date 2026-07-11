from enum import StrEnum


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    KAKAO = "kakao"


class UserStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    SUSPENDED = "suspended"


class ConsentType(StrEnum):
    TERMS = "terms"
    PRIVACY = "privacy"
    LOCATION = "location"


class RecordStatus(StrEnum):
    RECORDING = "recording"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

