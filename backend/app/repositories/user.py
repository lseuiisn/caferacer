from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import OAuthProvider, UserRole
from app.models.user import User, UserIdentity


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_identity(self, provider: OAuthProvider, subject: str) -> User | None:
        identity = (
            self.db.query(UserIdentity)
            .filter_by(provider=provider, provider_subject=subject)
            .first()
        )
        return identity.user if identity else None

    def create_with_identity(
        self,
        provider: OAuthProvider,
        subject: str,
        email: str | None,
        nickname: str | None = None,
    ) -> User:
        user = User(nickname=nickname, role=UserRole.USER)
        self.db.add(user)
        self.db.flush()  # user.id 확보

        self.db.add(UserIdentity(
            user_id=user.id,
            provider=provider,
            provider_subject=subject,
            email=email,
            linked_at=datetime.now(timezone.utc),
        ))
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        identity = self.db.query(UserIdentity).filter_by(email=email).first()
        return identity.user if identity else None