"""Print a short-lived access token for local Swagger administration.

Run only from a trusted development terminal. The script never writes the token
to the database or a file, and refuses non-admin accounts.
"""

import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import UserIdentity


def create_admin_access_token(email: str) -> str:
    db = SessionLocal()
    try:
        identity = db.scalar(select(UserIdentity).where(UserIdentity.email == email))
        if identity is None:
            raise ValueError("No signed-up account was found for this email")
        if identity.user.role != UserRole.ADMIN:
            raise ValueError("This account is not an administrator")
        return create_access_token(identity.user.id)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.create_admin_access_token <email>")
        sys.exit(1)
    print(create_admin_access_token(sys.argv[1]))
