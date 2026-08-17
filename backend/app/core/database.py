from collections.abc import Generator
from typing import Any

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    pass


_models_initialized = False


def initialize_models() -> None:
    global _models_initialized
    if _models_initialized:
        return

    from app.core import model_registry  # noqa: F401

    _models_initialized = True


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def get_engine(settings: Settings) -> Engine:
    kwargs = (
        {"connect_args": {"check_same_thread": False}}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    engine = create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
        **kwargs,
    )
    if settings.database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_request_db(request: Request) -> Generator[Session, None, None]:
    yield from get_db(request.app.state.db_factory)
