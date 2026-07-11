from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = (datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_days)).replace(tzinfo=None)
    raw_token = uuid4().hex + uuid4().hex
    return raw_token, expires_at


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> int:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise jwt.InvalidTokenError("Invalid access token type")
    return int(payload["sub"])
