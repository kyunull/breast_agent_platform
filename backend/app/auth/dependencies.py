from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_request_db
from app.core.security import hash_access_token
from app.users.models import AuthSession, User


_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": "authentication required"},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def get_current_session(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_request_db)],
) -> AuthSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    session = db.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(AuthSession.token_hash == hash_access_token(credentials.credentials))
    )
    if (
        session is None
        or session.revoked_at is not None
        or _aware(session.expires_at) <= datetime.now(timezone.utc)
        or session.user is None
        or not session.user.is_active
    ):
        raise _unauthorized()

    request.state.auth_session = session
    return session


def get_current_user(
    session: Annotated[AuthSession, Depends(get_current_session)],
) -> User:
    return session.user


def require_role(*roles: str):
    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail={"code": "forbidden", "message": "insufficient role"},
            )
        return current_user

    return dependency
