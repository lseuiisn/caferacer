from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.enums import UserStatus
from app.models.user import RefreshSession, User, UserIdentity
from app.schemas.auth import MeResponse, RefreshRequest, SocialLoginRequest, TokenResponse
from app.services.oauth import OAuthProfileVerifier, OAuthValidationError

router = APIRouter(prefix="/auth", tags=["auth"])
profile_verifier = OAuthProfileVerifier()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def issue_tokens(db: DbSession, user: User, device_name: str | None) -> TokenResponse:
    raw_refresh_token, expires_at = create_refresh_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            device_name=device_name,
            expires_at=expires_at,
            created_at=utcnow(),
        )
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=raw_refresh_token)


@router.post("/social/login", response_model=TokenResponse)
async def social_login(payload: SocialLoginRequest, db: DbSession) -> TokenResponse:
    try:
        profile = await profile_verifier.verify(payload.provider, payload.provider_credential)
    except OAuthValidationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == profile.provider,
            UserIdentity.provider_subject == profile.subject,
        )
    )
    if identity is None:
        user = User(status=UserStatus.ACTIVE, nickname=profile.name)
        db.add(user)
        db.flush()
        identity = UserIdentity(
            user_id=user.id,
            provider=profile.provider,
            provider_subject=profile.subject,
            email=profile.email,
            linked_at=utcnow(),
        )
        db.add(identity)
    else:
        user = identity.user
        if user.status is not UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is unavailable")
    return issue_tokens(db, user, payload.device_name)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(payload.refresh_token))
    )
    if session is None or session.revoked_at is not None or session.expires_at <= utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    session.revoked_at = utcnow()
    db.flush()
    return issue_tokens(db, session.user, session.device_name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: DbSession) -> None:
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(payload.refresh_token))
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


@router.get("/me", response_model=MeResponse)
def read_me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=current_user.id,
        nickname=current_user.nickname,
        status=current_user.status,
        role=current_user.role,
        identities=[
            {"provider": identity.provider, "linked_at": identity.linked_at}
            for identity in current_user.identities
        ],
    )
