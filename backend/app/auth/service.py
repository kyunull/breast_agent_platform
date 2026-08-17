from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest
from app.core.config import Settings
from app.core.security import create_access_token, hash_access_token, verify_password
from app.users.models import AuthSession, User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def authenticate(
    db: Session,
    credentials: LoginRequest,
    settings: Settings,
) -> tuple[str, AuthSession] | None:
    user = db.scalar(select(User).where(User.username == credentials.username))
    if user is None or not user.is_active or not verify_password(credentials.password, user.password_hash):
        return None

    token = create_access_token()
    session = AuthSession(
        token_hash=hash_access_token(token),
        user_id=user.id,
        expires_at=utc_now() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.flush()
    return token, session
