from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_session
from app.auth.schemas import LoginRequest, TokenResponse
from app.auth.service import authenticate
from app.core.database import get_request_db
from app.users.models import AuthSession


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_request_db)],
) -> TokenResponse:
    result = authenticate(db, credentials, request.app.state.settings)
    if result is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "message": "invalid username or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, session = result
    db.commit()
    return TokenResponse(access_token=token, expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: Annotated[Session, Depends(get_request_db)],
    session: Annotated[AuthSession, Depends(get_current_session)],
) -> Response:
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
