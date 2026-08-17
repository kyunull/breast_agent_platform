import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_request_db
from app.extraction.schemas import ExtractionConfig
from app.graph.schemas import WorkflowGraph
from app.users.models import User
from app.workflows.schemas import WorkflowCreate, WorkflowDraftPatch, WorkflowRead
from app.workflows.service import create_workflow, get_draft, update_draft


router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


class TemplateCloneRequest(BaseModel):
    name: str = Field(default="我的 HER2 流程", min_length=1, max_length=255)
    description: str | None = None


@lru_cache(maxsize=1)
def _template() -> dict[str, Any]:
    path = Path(__file__).with_name("her2_reference.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_template() -> dict[str, Any]:
    template = _template()
    WorkflowGraph.model_validate(template["graph"])
    ExtractionConfig.model_validate(template["extraction"])
    return template


@router.get("/her2-advanced")
def get_her2_template(
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    return _validated_template()


@router.post("/her2-advanced/clone", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def clone_her2_template(
    payload: TemplateCloneRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> WorkflowRead:
    template = _validated_template()
    try:
        workflow = create_workflow(
            db,
            WorkflowCreate(name=payload.name, description=payload.description),
            current_user.id,
        )
        draft = get_draft(db, workflow.id)
        if draft is None:
            raise RuntimeError("template clone draft was not created")
        update_draft(
            db,
            workflow,
            draft,
            WorkflowDraftPatch(
                graph=template["graph"],
                extraction=ExtractionConfig.model_validate(template["extraction"]),
                metadata=template["metadata"] | {"review_warning": template["warning"]},
            ),
            current_user.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return WorkflowRead(
        id=workflow.id,
        owner_id=workflow.owner_id,
        name=workflow.name,
        description=workflow.description,
        draft_version_number=0,
    )
