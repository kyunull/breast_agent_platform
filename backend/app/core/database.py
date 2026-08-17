from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    pass


def get_engine(settings: Settings) -> Engine:
    kwargs = (
        {"connect_args": {"check_same_thread": False}}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    return create_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=True,
        **kwargs,
    )


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


# Import mapped models after Base exists so callers can use Base.metadata directly.
from app.core import model_registry as _model_registry  # noqa: E402,F401
