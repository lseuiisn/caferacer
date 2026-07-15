# scripts/set_admin.py
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import UserRole
from app.models.user import UserIdentity


def set_admin(email: str) -> None:
    db = SessionLocal()
    try:
        identity = db.scalar(select(UserIdentity).where(UserIdentity.email == email))
        if identity is None:
            raise ValueError(f"{email} 로 가입된 계정이 없습니다")
        identity.user.role = UserRole.ADMIN
        db.commit()
        print(f"{email} → ADMIN 완료")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python scripts/set_admin.py <email>")
        sys.exit(1)
    set_admin(sys.argv[1])