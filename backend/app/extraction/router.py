from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.extraction.schemas import ExtractionPreview, ExtractionPreviewRequest
from app.extraction.service import preview_extraction


router = APIRouter(prefix="/api/v1/workflows", tags=["extraction"])


@router.post("/{workflow_id}/draft/extraction/preview", response_model=ExtractionPreview)
def preview_workflow_extraction(
    workflow_id: str,
    request: ExtractionPreviewRequest,
    _: Annotated[object, Depends(get_current_user)],
) -> ExtractionPreview:
    return preview_extraction(request.resolved_payload(), request.config)
