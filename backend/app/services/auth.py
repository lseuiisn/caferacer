from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.user import RefreshSession
from app.repositories.user import UserRepository
from app.schemas.auth import SocialLoginRequest, TokenResponse
from app.services.oauth import OAuthProfileVerifier


class AuthService:
    def __init__(self, db: Session, verifier: OAuthProfileVerifier):
        self.db = db
        self.verifier = verifier
        self.users = UserRepository(db)

    async def social_login(self, payload: SocialLoginRequest) -> TokenResponse:
        profile = await self.verifier.verify(payload.provider, payload.provider_credential)

        user = self.users.get_by_identity(profile.provider, profile.subject)
        if user is None:
            user = self.users.create_with_identity(
                provider=profile.provider,
                subject=profile.subject,
                email=profile.email,
            )

        access_token = create_access_token(user_id=user.id)
        raw_refresh_token, expires_at = create_refresh_token()

        self.db.add(RefreshSession(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            device_name=payload.device_name,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        ))
        self.db.commit()

        return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)