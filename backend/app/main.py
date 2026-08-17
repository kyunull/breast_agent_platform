from fastapi import FastAPI

from app.api import router
from app.core.config import Settings
from app.core.errors import validation_error_handler


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Breast Cancer Decision Agent Backend", version="0.1.0")
    app.state.settings = settings or Settings()
    app.include_router(router)
    app.add_exception_handler(ValueError, validation_error_handler)
    return app


app = create_app()
