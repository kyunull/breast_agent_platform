from __future__ import annotations

import getpass
import sys
from pathlib import Path

from sqlalchemy import select

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.audit.service import record_audit
from app.core.config import Settings
from app.core.database import Base, get_engine, initialize_models, session_factory
from app.core.security import hash_password
from app.users.models import User


def main() -> int:
    settings = Settings()
    initialize_models()
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    db = session_factory(engine)()
    try:
        username = input("Admin username: ").strip()
        if not username:
            print("Username is required.", file=sys.stderr)
            return 2
        if db.scalar(select(User).where(User.username == username)) is not None:
            print("Username already exists.", file=sys.stderr)
            return 1
        password = getpass.getpass("Admin password: ")
        confirmation = getpass.getpass("Confirm admin password: ")
        if not password or password != confirmation:
            print("Passwords do not match.", file=sys.stderr)
            return 2
        display_name = input("Display name: ").strip() or username
        user = User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role="admin_developer",
        )
        db.add(user)
        db.flush()
        record_audit(
            db,
            actor_id=None,
            action="user.create",
            entity_type="user",
            entity_id=user.id,
            metadata={"changed_fields": ["username", "display_name", "role"]},
        )
        db.commit()
        print(f"Created admin user {username}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
