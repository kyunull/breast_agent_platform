from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_request_db
from app.core.governance import redact_hidden_parameters
from app.graph.schemas import GraphValidationError
from app.users.models import User
from app.workflows.models import Workflow, WorkflowVersion
from app.workflows.schemas import (
    DraftRead,
    PublishedVersionRead,
    WorkflowCreate,
    WorkflowDraftPatch,
    WorkflowRead,
)
from app.workflows.service import (
    create_workflow,
    get_draft,
    get_published_version,
    get_workflow,
    list_published_versions,
    publish_workflow,
    update_draft,
)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


def _can_manage(workflow: Workflow, user: User) -> bool:
    return user.role == "admin_developer" or workflow.owner_id == user.id


def _require_workflow(db: Session, workflow_id: str, user: User) -> Workflow:
    workflow = get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "workflow not found"})
    if not _can_manage(workflow, user):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "workflow access denied"})
    return workflow


def _draft_read(workflow: Workflow, draft: WorkflowVersion, user: User) -> DraftRead:
    definition = draft.definition_json
    extraction = draft.extraction_json
    if user.role != "admin_developer":
        definition = redact_hidden_parameters(definition)
        extraction = redact_hidden_parameters(extraction)
    return DraftRead(
        id=draft.id,
        workflow_id=workflow.id,
        version_number=draft.version_number,
        status=draft.status,
        name=workflow.name,
        description=workflow.description,
        graph=definition.get("graph", {"nodes": [], "edges": []}),
        extraction=extraction,
        metadata=definition.get("metadata", {}),
        template_refs=definition.get("template_refs", []),
        definition_sha256=(draft.definition_sha256 if user.role == "admin_developer" else None),
    )


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow_endpoint(
    payload: WorkflowCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> WorkflowRead:
    try:
        workflow = create_workflow(db, payload, current_user.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "workflow name conflict"}) from exc
    return WorkflowRead(
        id=workflow.id,
        owner_id=workflow.owner_id,
        name=workflow.name,
        description=workflow.description,
        draft_version_number=0,
    )


@router.get("", response_model=list[WorkflowRead])
def list_workflows(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> list[WorkflowRead]:
    statement = select(Workflow).order_by(Workflow.updated_at.desc())
    if current_user.role != "admin_developer":
        statement = statement.where(Workflow.owner_id == current_user.id)
    workflows = list(db.scalars(statement))
    return [
        WorkflowRead(
            id=workflow.id,
            owner_id=workflow.owner_id,
            name=workflow.name,
            description=workflow.description,
            draft_version_number=0,
        )
        for workflow in workflows
    ]


@router.get("/{workflow_id}/draft", response_model=DraftRead)
def read_draft(
    workflow_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> DraftRead:
    workflow = _require_workflow(db, workflow_id, current_user)
    draft = get_draft(db, workflow.id)
    if draft is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "draft not found"})
    return _draft_read(workflow, draft, current_user)


@router.patch("/{workflow_id}/draft", response_model=DraftRead)
def patch_draft(
    workflow_id: str,
    payload: WorkflowDraftPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> DraftRead:
    workflow = _require_workflow(db, workflow_id, current_user)
    draft = get_draft(db, workflow.id)
    if draft is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "draft not found"})
    update_draft(
        db,
        workflow,
        draft,
        payload,
        current_user.id,
        allow_technical_parameters=current_user.role == "admin_developer",
    )
    db.commit()
    return _draft_read(workflow, draft, current_user)


@router.post("/{workflow_id}/publish", response_model=PublishedVersionRead, status_code=status.HTTP_201_CREATED)
def publish(
    workflow_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> PublishedVersionRead:
    workflow = _require_workflow(db, workflow_id, current_user)
    draft = get_draft(db, workflow.id, for_update=True)
    if draft is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "draft not found"})
    try:
        published, _ = publish_workflow(
            db,
            workflow,
            draft,
            current_user.id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "publish_conflict",
                "message": "workflow was published concurrently; reload the draft and retry",
            },
        ) from exc
    except (ValueError, GraphValidationError) as exc:
        db.rollback()
        detail: Any = {"code": "invalid_workflow", "message": str(exc)}
        if isinstance(exc, GraphValidationError):
            detail["issues"] = [issue.model_dump() for issue in exc.issues]
        raise HTTPException(status_code=422, detail=detail) from exc
    return PublishedVersionRead(
        id=published.id,
        workflow_id=published.workflow_id,
        version_number=published.version_number,
        status=published.status,
        definition=(
            published.definition_json
            if current_user.role == "admin_developer"
            else redact_hidden_parameters(published.definition_json)
        ),
        extraction=(
            published.extraction_json
            if current_user.role == "admin_developer"
            else redact_hidden_parameters(published.extraction_json)
        ),
        definition_sha256=(
            published.definition_sha256
            if current_user.role == "admin_developer"
            else None
        ),
        created_at=published.created_at,
    )


@router.get("/{workflow_id}/versions", response_model=list[PublishedVersionRead])
def versions(
    workflow_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> list[PublishedVersionRead]:
    workflow = _require_workflow(db, workflow_id, current_user)
    return [
        PublishedVersionRead(
            id=version.id,
            workflow_id=workflow.id,
            version_number=version.version_number,
            status=version.status,
            definition=(
                version.definition_json
                if current_user.role == "admin_developer"
                else redact_hidden_parameters(version.definition_json)
            ),
            extraction=(
                version.extraction_json
                if current_user.role == "admin_developer"
                else redact_hidden_parameters(version.extraction_json)
            ),
            definition_sha256=(
                version.definition_sha256
                if current_user.role == "admin_developer"
                else None
            ),
            created_at=version.created_at,
        )
        for version in list_published_versions(db, workflow.id)
    ]


@router.patch("/{workflow_id}/versions/{version_number}")
def reject_published_patch(
    workflow_id: str,
    version_number: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> Response:
    _require_workflow(db, workflow_id, current_user)
    if get_published_version(db, workflow_id, version_number) is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "version not found"})
    raise HTTPException(status_code=405, detail={"code": "immutable_version", "message": "published versions are immutable"})


@router.delete("/{workflow_id}/versions/{version_number}")
def reject_published_delete(
    workflow_id: str,
    version_number: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> Response:
    _require_workflow(db, workflow_id, current_user)
    if get_published_version(db, workflow_id, version_number) is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "version not found"})
    raise HTTPException(status_code=405, detail={"code": "immutable_version", "message": "published versions are immutable"})
