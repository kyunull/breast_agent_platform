from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.schemas import UserRead
from app.core.database import get_request_db
from app.users.models import User
from app.users.schemas import UserCreate
from app.users.service import create_user

router = APIRouter(prefix="/api/v1", tags=["users"])
_admin_user = require_role("admin_developer")


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_request_db)],
    current_user: Annotated[User, Depends(_admin_user)],
) -> User:
    try:
        user = create_user(db, payload, actor_id=current_user.id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": str(exc)}) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "username already exists"}) from exc
    return user
