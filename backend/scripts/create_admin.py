from __future__ import annotations

import getpass
import sys
from pathlib import Path

from alembic.config import Config
from sqlalchemy import select

from alembic import command

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.audit.service import record_audit
from app.core.config import Settings
from app.core.database import get_engine, session_factory
from app.core.security import hash_password
from app.users.models import User


def upgrade_database(settings: Settings) -> None:
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    alembic_config.attributes["database_url"] = settings.database_url
    command.upgrade(alembic_config, "head")


def main() -> int:
    settings = Settings()
    upgrade_database(settings)
    engine = get_engine(settings)
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
