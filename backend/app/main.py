from collections.abc import Generator

from fastapi import FastAPI, Request
from sqlalchemy.orm import Session

from app.api import router
from app.core.config import Settings
from app.core.database import get_engine, get_request_db, session_factory
from app.core.errors import validation_error_handler


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Breast Cancer Decision Agent Backend", version="0.1.0")
    app.state.settings = settings or Settings()
    app.state.engine = get_engine(app.state.settings)
    app.state.db_factory = session_factory(app.state.engine)
    app.include_router(router)
    app.add_exception_handler(ValueError, validation_error_handler)
    return app


def get_db(request: Request) -> Generator[Session, None, None]:
    yield from get_request_db(request)


app = create_app()
