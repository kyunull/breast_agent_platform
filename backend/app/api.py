from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.extraction.router import router as extraction_router
from app.profiles.router import router as profiles_router
from app.users.router import router as users_router
from app.workflows.router import router as workflows_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(profiles_router)
router.include_router(extraction_router)
router.include_router(workflows_router)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "breast-agent-backend"}
