from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.core.security import hash_password
from app.users.models import User
from app.users.schemas import UserCreate


def create_user(db: Session, payload: UserCreate, actor_id: str | None = None) -> User:
    if db.scalar(select(User).where(User.username == payload.username)) is not None:
        raise ValueError("username already exists")

    user = User(
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        actor_id=actor_id,
        action="user.create",
        entity_type="user",
        entity_id=user.id,
        metadata={"changed_fields": ["username", "display_name", "role"]},
    )
    return user
