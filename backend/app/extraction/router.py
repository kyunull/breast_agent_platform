from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.extraction.schemas import ExtractionPreview, ExtractionPreviewRequest
from app.extraction.service import preview_extraction
from app.core.database import get_request_db
from app.users.models import User
from app.workflows.service import get_workflow


router = APIRouter(prefix="/api/v1/workflows", tags=["extraction"])


@router.post("/{workflow_id}/draft/extraction/preview", response_model=ExtractionPreview)
def preview_workflow_extraction(
    workflow_id: str,
    request: ExtractionPreviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> ExtractionPreview:
    workflow = get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "workflow not found"})
    if current_user.role != "admin_developer" and workflow.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "workflow access denied"})
    return preview_extraction(request.resolved_payload(), request.config)
