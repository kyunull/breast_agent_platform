from collections.abc import Generator
import sys

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    pass


_models_initialized = False
_models_initializing = False


def initialize_models() -> None:
    global _models_initialized, _models_initializing
    if _models_initialized or _models_initializing:
        return

    _models_initializing = True
    try:
        from app.core import model_registry  # noqa: F401

        _models_initialized = True
    finally:
        _models_initializing = False


def _model_module_is_initializing() -> bool:
    for module_name, module in list(sys.modules.items()):
        if not module_name.startswith("app.") or not module_name.endswith(".models"):
            continue
        spec = getattr(module, "__spec__", None)
        if getattr(spec, "_initializing", False):
            return True
    return False


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


if not _model_module_is_initializing():
    initialize_models()
