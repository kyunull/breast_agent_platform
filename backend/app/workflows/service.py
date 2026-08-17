from copy import deepcopy
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.core.governance import validate_governed_payload, validate_medical_node_configs
from app.extraction.schemas import ExtractionConfig
from app.graph.schemas import WorkflowGraph
from app.graph.validation import assert_valid_graph
from app.workflows.models import Workflow, WorkflowVersion, canonical_definition_sha256
from app.workflows.schemas import WorkflowCreate, WorkflowDraftPatch


def empty_definition() -> dict[str, Any]:
    return {"graph": {"nodes": [], "edges": []}, "metadata": {}, "template_refs": []}


def _draft_query(workflow_id: str):
    return select(WorkflowVersion).where(
        WorkflowVersion.workflow_id == workflow_id,
        WorkflowVersion.status == "draft",
    )


def get_workflow(db: Session, workflow_id: str) -> Workflow | None:
    return db.get(Workflow, workflow_id)


def get_draft(
    db: Session,
    workflow_id: str,
    *,
    for_update: bool = False,
) -> WorkflowVersion | None:
    statement = _draft_query(workflow_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def create_workflow(db: Session, payload: WorkflowCreate, actor_id: str) -> Workflow:
    workflow = Workflow(owner_id=actor_id, name=payload.name, description=payload.description)
    db.add(workflow)
    db.flush()
    draft = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=0,
        definition_json=empty_definition(),
        extraction_json={"groups": []},
        status="draft",
        definition_sha256=canonical_definition_sha256(empty_definition(), {"groups": []}),
    )
    db.add(draft)
    db.flush()
    record_audit(
        db,
        actor_id=actor_id,
        action="workflow.create",
        entity_type="workflow",
        entity_id=workflow.id,
        metadata={"workflow_id": workflow.id, "changed_fields": ["name", "description"]},
    )
    return workflow


def update_draft(
    db: Session,
    workflow: Workflow,
    draft: WorkflowVersion,
    payload: WorkflowDraftPatch,
    actor_id: str,
    *,
    allow_technical_parameters: bool = False,
) -> WorkflowVersion:
    validate_governed_payload(
        payload.model_dump(exclude_unset=True),
        allow_technical_parameters=allow_technical_parameters,
        path="workflow.patch",
    )
    if payload.graph is not None and not allow_technical_parameters:
        graph_payload = (
            payload.graph.model_dump()
            if isinstance(payload.graph, WorkflowGraph)
            else payload.graph
        )
        validate_medical_node_configs(graph_payload)
    changed_fields: list[str] = []
    if payload.name is not None:
        workflow.name = payload.name
        changed_fields.append("name")
    if payload.description is not None:
        workflow.description = payload.description
        changed_fields.append("description")

    definition = deepcopy(draft.definition_json)
    if payload.graph is not None:
        graph = payload.graph.model_dump() if isinstance(payload.graph, WorkflowGraph) else payload.graph
        definition["graph"] = graph
        changed_fields.append("graph")
    if payload.metadata is not None:
        definition["metadata"] = payload.metadata
        changed_fields.append("metadata")
    if payload.template_refs is not None:
        definition["template_refs"] = payload.template_refs
        changed_fields.append("template_refs")
    extraction_json = draft.extraction_json
    if payload.extraction is not None:
        extraction_json = payload.extraction.model_dump()
        changed_fields.append("extraction")
    validate_governed_payload(
        {
            "name": workflow.name,
            "description": workflow.description,
            "definition": definition,
            "extraction": extraction_json,
        },
        allow_technical_parameters=True,
        path="workflow",
    )
    if changed_fields:
        draft.definition_json = definition
        draft.extraction_json = extraction_json
    draft.definition_sha256 = canonical_definition_sha256(draft.definition_json, draft.extraction_json)
    if changed_fields:
        record_audit(
            db,
            actor_id=actor_id,
            action="workflow.draft.update",
            entity_type="workflow",
            entity_id=workflow.id,
            metadata={"workflow_id": workflow.id, "changed_fields": changed_fields},
        )
    db.flush()
    return draft


def publish_workflow(
    db: Session,
    workflow: Workflow,
    draft: WorkflowVersion,
    actor_id: str,
) -> tuple[WorkflowVersion, WorkflowVersion]:
    graph = WorkflowGraph.model_validate(draft.definition_json.get("graph"))
    extraction = ExtractionConfig.model_validate(draft.extraction_json)
    assert_valid_graph(graph)
    definition = deepcopy(draft.definition_json)
    extraction_json = extraction.model_dump()
    validate_governed_payload(
        {
            "name": workflow.name,
            "description": workflow.description,
            "definition": definition,
            "extraction": extraction_json,
        },
        allow_technical_parameters=True,
        path="workflow",
    )
    draft.version_number = int(
        db.scalar(
            select(func.coalesce(func.max(WorkflowVersion.version_number), 0)).where(
                WorkflowVersion.workflow_id == workflow.id,
                WorkflowVersion.status == "published",
            )
        )
        or 0
    ) + 1
    draft.status = "published"
    draft.definition_sha256 = canonical_definition_sha256(definition, extraction_json)
    fresh_draft = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=0,
        definition_json=deepcopy(definition),
        extraction_json=deepcopy(extraction_json),
        status="draft",
        definition_sha256=draft.definition_sha256,
    )
    db.add(fresh_draft)
    db.flush()
    record_audit(
        db,
        actor_id=actor_id,
        action="workflow.publish",
        entity_type="workflow_version",
        entity_id=draft.id,
        metadata={"workflow_id": workflow.id, "version_id": draft.id, "changed_fields": ["status", "version_number"]},
    )
    return draft, fresh_draft


def list_published_versions(db: Session, workflow_id: str) -> list[WorkflowVersion]:
    statement = select(WorkflowVersion).where(
        WorkflowVersion.workflow_id == workflow_id,
        WorkflowVersion.status == "published",
    ).order_by(WorkflowVersion.version_number)
    return list(db.scalars(statement))


def get_published_version(
    db: Session,
    workflow_id: str,
    version_number: int,
) -> WorkflowVersion | None:
    return db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == version_number,
            WorkflowVersion.status == "published",
        )
    )
