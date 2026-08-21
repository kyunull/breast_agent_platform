from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_request_db
from app.profiles.models import KnowledgeProfile, ModelProfile
from app.runtime.engine import WorkflowEngine
from app.runtime.knowledge_gateway import (
    BreastKnowledgebaseAdapter,
    GenericHttpKnowledgeBaseAdapter,
)
from app.runtime.model_gateway import OpenAICompatibleGateway
from app.runtime.models import NodeTrace, RunEvidence, WorkflowRun
from app.runtime.optimization import (
    PromptOptimizationError,
    apply_prompt_optimization,
    create_prompt_optimization,
)
from app.runtime.schemas import (
    EvidenceRead,
    KnowledgePreviewRead,
    KnowledgePreviewRequest,
    PromptOptimizationCreate,
    PromptOptimizationRead,
    RunCreate,
    RunRead,
    TraceRead,
)
from app.runtime.service import append_trace, create_run, store_evidence, summarize_input
from app.users.models import User
from app.workflows.models import Workflow, WorkflowVersion

router = APIRouter(prefix="/api/v1", tags=["runtime"])


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=403, detail={"code": "forbidden", "message": message})


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "not_found", "message": message})


def _can_access_workflow(workflow: Workflow, user: User) -> bool:
    return user.role == "admin_developer" or workflow.owner_id == user.id


def _require_workflow(db: Session, workflow_id: str, user: User) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise _not_found("workflow not found")
    if not _can_access_workflow(workflow, user):
        raise _forbidden("workflow access denied")
    return workflow


def _require_version(
    db: Session,
    workflow_id: str,
    version_number: int | None,
) -> WorkflowVersion:
    if version_number == 0:
        version = db.scalar(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_id == workflow_id,
                WorkflowVersion.status == "draft",
            )
        )
    else:
        statement = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.status == "published",
        )
        if version_number is not None:
            statement = statement.where(WorkflowVersion.version_number == version_number)
        else:
            statement = statement.order_by(WorkflowVersion.version_number.desc())
        version = db.scalar(statement)
    if version is None:
        raise _not_found("workflow version not found")
    return version


def _require_profile(db: Session, model: type[Any], profile_id: str, user: User) -> Any:
    profile = db.get(model, profile_id)
    if profile is None:
        raise _not_found("profile not found")
    if not profile.is_active:
        raise _forbidden("profile is inactive")
    if user.role != "admin_developer" and not profile.exposed_to_medical:
        raise _forbidden("profile is not available to medical users")
    return profile


def _profile_refs(version: WorkflowVersion, node_type: str, field: str) -> list[str]:
    graph = version.definition_json.get("graph", {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    profile_ids: list[str] = []
    for node in nodes:
        if not isinstance(node, dict) or node.get("type") != node_type:
            continue
        config = node.get("config", {})
        if isinstance(config, dict) and config.get(field):
            profile_id = str(config[field])
            if profile_id not in profile_ids:
                profile_ids.append(profile_id)
    return profile_ids


def _node_profile_ref(
    version: WorkflowVersion,
    node_id: str,
    node_type: str,
    field: str,
) -> str | None:
    graph = version.definition_json.get("graph", {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    for node in nodes:
        if not isinstance(node, dict) or node.get("id") != node_id:
            continue
        if node.get("type") != node_type:
            return None
        config = node.get("config", {})
        return str(config[field]) if isinstance(config, dict) and config.get(field) else None
    return None


def _default_providers(model_profile: Any | None, knowledge_profile: Any | None, credential_manager: Any | None = None) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    if model_profile is not None:
        providers["model"] = OpenAICompatibleGateway(credential_manager=credential_manager)
        providers["model_profile"] = model_profile
    if knowledge_profile is not None:
        config = knowledge_profile.technical_config_json
        provider = str(config.get("provider", "knowledgebase"))
        adapter = (
            GenericHttpKnowledgeBaseAdapter(knowledge_profile)
            if provider in {"generic_http", "http"}
            else BreastKnowledgebaseAdapter(knowledge_profile)
        )
        providers["knowledge"] = adapter
    return providers


def _provider_bundle(
    app: Any,
    db: Session,
    version: WorkflowVersion | None,
    user: User,
    model_profile: Any | None,
    knowledge_profile: Any | None,
) -> dict[str, Any]:
    factory = getattr(app.state, "runtime_provider_factory", None)
    result = (
        factory(
            db=db,
            workflow_version=version,
            actor=user,
            model_profile=model_profile,
            knowledge_profile=knowledge_profile,
        )
        if callable(factory)
        else _default_providers(model_profile, knowledge_profile, app.state.credential_manager)
    )
    return dict(result or {})


def _build_providers(
    app: Any,
    db: Session,
    version: WorkflowVersion | None,
    user: User,
    *,
    model_profile_id: str | None = None,
    knowledge_profile_id: str | None = None,
) -> dict[str, Any]:
    model_profile_ids = (
        [model_profile_id]
        if model_profile_id is not None
        else (_profile_refs(version, "llm", "model_profile_ref") if version is not None else [])
    )
    knowledge_profile_ids = (
        [knowledge_profile_id]
        if knowledge_profile_id is not None
        else (_profile_refs(version, "rag", "knowledge_profile_ref") if version is not None else [])
    )
    model_profiles = {
        profile_id: _require_profile(db, ModelProfile, profile_id, user)
        for profile_id in model_profile_ids
    }
    knowledge_profiles = {
        profile_id: _require_profile(db, KnowledgeProfile, profile_id, user)
        for profile_id in knowledge_profile_ids
    }
    if not model_profiles and not knowledge_profiles:
        return _provider_bundle(app, db, version, user, None, None)

    providers: dict[str, Any] = {}
    model_providers: dict[str, tuple[Any, Any]] = {}
    knowledge_providers: dict[str, Any] = {}
    for profile_id, profile in model_profiles.items():
        bundle = _provider_bundle(app, db, version, user, profile, None)
        model_providers[profile_id] = (bundle.get("model"), bundle.get("model_profile", profile))
    for profile_id, profile in knowledge_profiles.items():
        bundle = _provider_bundle(app, db, version, user, None, profile)
        knowledge_providers[profile_id] = bundle.get("knowledge")
    if model_providers:
        first_model_provider, first_model_profile = next(iter(model_providers.values()))
        providers["model"] = first_model_provider
        providers["model_profile"] = first_model_profile
        providers["models_by_profile"] = model_providers
    if knowledge_providers:
        providers["knowledge"] = next(iter(knowledge_providers.values()))
        providers["knowledge_by_profile"] = knowledge_providers
    if model_profile_id is not None:
        providers["model_override_profile_id"] = model_profile_id
    return providers


def _run_read(run: WorkflowRun) -> RunRead:
    return RunRead(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_version_id=run.workflow_version_id,
        model_profile_id=run.model_profile_id,
        mode=run.mode,
        status=run.status,
        input_sha256=run.input_sha256,
        input_summary=run.input_summary_json,
        output=run.output_json,
        error=run.error_json,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


def _trace_read(trace: NodeTrace) -> TraceRead:
    return TraceRead(
        id=trace.id,
        run_id=trace.run_id,
        node_id=trace.node_id,
        parent_trace_id=trace.parent_trace_id,
        status=trace.status,
        sequence=trace.sequence,
        attempt=trace.attempt,
        input_summary=trace.input_summary_json,
        output=trace.output_json,
        error=trace.error_json,
        evidence_refs=trace.evidence_refs_json,
        duration_ms=trace.duration_ms,
        started_at=trace.started_at,
        finished_at=trace.finished_at,
        created_at=trace.created_at,
    )


def _evidence_read(evidence: RunEvidence) -> EvidenceRead:
    return EvidenceRead.model_validate(evidence)


def _optimization_read(optimization: Any) -> PromptOptimizationRead:
    return PromptOptimizationRead(
        id=optimization.id,
        workflow_id=optimization.workflow_id,
        node_id=optimization.node_id,
        source_run_id=optimization.source_run_id,
        original_prompt=optimization.original_prompt,
        candidate_prompt=optimization.candidate_prompt,
        instruction=optimization.instruction,
        model_profile_id=optimization.model_profile_id,
        test_input_sha256=optimization.test_input_sha256,
        result_diff=optimization.result_diff_json,
        status=optimization.status,
        created_by=optimization.created_by,
        created_at=optimization.created_at,
        applied_at=optimization.applied_at,
    )


def _run_actor(db: Session, actor_id: str) -> User:
    actor = db.get(User, actor_id)
    if actor is None:
        raise RuntimeError("run actor no longer exists")
    return actor


def execute_persisted_run(app: Any, run_id: str, raw_input: dict[str, Any]) -> WorkflowRun | None:
    db = app.state.db_factory()
    try:
        run = db.get(WorkflowRun, run_id)
        if run is None or run.status == "cancelled":
            return run
        version = db.get(WorkflowVersion, run.workflow_version_id)
        if version is None:
            run.status = "failed"
            run.error_json = {"code": "version_not_found", "message": "workflow version not found"}
            run.finished_at = datetime.now(UTC)
            db.commit()
            return run
        actor = _run_actor(db, run.created_by) if run.created_by else None
        if actor is None:
            run.status = "failed"
            run.error_json = {"code": "actor_not_found", "message": "run actor not found"}
            run.finished_at = datetime.now(UTC)
            db.commit()
            return run
        run.status = "running"
        run.started_at = datetime.now(UTC)
        db.commit()
        trace_ids: dict[str, str] = {}
        evidence_trace_ids: dict[str, str] = {}
        trace_sequence = 0

        def trace_sink(data: dict[str, Any]) -> None:
            nonlocal trace_sequence
            trace_sequence += 1
            safe = dict(data)
            safe["sequence"] = trace_sequence
            parent_node_id = safe.get("parent_trace_id")
            safe["parent_trace_id"] = (
                trace_ids.get(str(parent_node_id)) if parent_node_id is not None else None
            )
            safe["input_summary"] = summarize_input(safe.pop("input", {}))
            trace = append_trace(db, run.id, safe)
            trace_ids[safe["node_id"]] = trace.id
            for evidence_ref in safe.get("evidence_refs", []):
                evidence_trace_ids[str(evidence_ref)] = trace.id
            db.commit()

        def cancel_check() -> bool:
            db.refresh(run, ["status"])
            return run.status == "cancelled"

        try:
            providers = _build_providers(
                app,
                db,
                version,
                actor,
                model_profile_id=run.model_profile_id,
            )
            result = WorkflowEngine(
                providers=providers,
                trace_sink=trace_sink,
                cancel_check=cancel_check,
            ).execute(
                version.definition_json.get("graph", {}),
                version.extraction_json,
                raw_input,
                run_id=run.id,
            )
            for evidence in result.evidence.values():
                store_evidence(
                    db,
                    run.id,
                    evidence_trace_ids.get(evidence.evidence_id),
                    evidence.to_dict(),
                )
            db.refresh(run)
            if run.status != "cancelled":
                run.status = result.status
                run.output_json = result.output
                run.error_json = result.error
                run.finished_at = datetime.now(UTC)
        except Exception:  # noqa: BLE001 - convert every runtime provider failure to a run result
            db.rollback()
            run = db.get(WorkflowRun, run_id)
            if run is None:
                return None
            if run.status != "cancelled":
                run.status = "failed"
                run.error_json = {
                    "code": "runtime_execution_failed",
                    "message": "runtime execution failed",
                }
                run.finished_at = datetime.now(UTC)
        db.commit()
        return run
    finally:
        db.close()


def _require_run(db: Session, run_id: str, user: User) -> WorkflowRun:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise _not_found("run not found")
    if user.role != "admin_developer" and run.created_by != user.id:
        raise _forbidden("run access denied")
    return run


def _require_optimization(db: Session, optimization_id: str, user: User) -> Any:
    from app.runtime.models import PromptOptimization

    optimization = db.get(PromptOptimization, optimization_id)
    if optimization is None:
        raise _not_found("prompt optimization not found")
    _require_workflow(db, optimization.workflow_id, user)
    return optimization


@router.post(
    "/prompt-optimizations",
    response_model=PromptOptimizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt_optimization_endpoint(
    payload: PromptOptimizationCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> PromptOptimizationRead:
    run = _require_run(db, payload.run_id, current_user)
    _require_workflow(db, run.workflow_id, current_user)
    version = db.get(WorkflowVersion, run.workflow_version_id)
    if version is None:
        raise _not_found("workflow version not found")
    selected_model_profile_id = payload.model_profile_id or _node_profile_ref(
        version,
        payload.node_id,
        "llm",
        "model_profile_ref",
    )
    providers = _build_providers(
        request.app,
        db,
        version,
        current_user,
        model_profile_id=selected_model_profile_id,
    )
    try:
        optimization = create_prompt_optimization(
            db,
            run.id,
            payload.node_id,
            payload.instruction,
            current_user.id,
            model_provider=providers.get("model"),
            model_profile=providers.get("model_profile"),
        )
        db.commit()
    except PromptOptimizationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_prompt_optimization", "message": str(exc)},
        ) from exc
    return _optimization_read(optimization)


@router.get("/prompt-optimizations/{optimization_id}", response_model=PromptOptimizationRead)
def get_prompt_optimization_endpoint(
    optimization_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> PromptOptimizationRead:
    return _optimization_read(_require_optimization(db, optimization_id, current_user))


@router.post("/prompt-optimizations/{optimization_id}/apply", response_model=PromptOptimizationRead)
def apply_prompt_optimization_endpoint(
    optimization_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> PromptOptimizationRead:
    _require_optimization(db, optimization_id, current_user)
    try:
        optimization, _draft = apply_prompt_optimization(db, optimization_id, current_user.id)
        db.commit()
    except PromptOptimizationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "prompt_optimization_not_applicable", "message": str(exc)},
        ) from exc
    return _optimization_read(optimization)


@router.post(
    "/runs",
    response_model=RunRead,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_202_ACCEPTED: {"model": RunRead, "description": "Run queued"}},
)
def create_run_endpoint(
    payload: RunCreate,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
):
    workflow = _require_workflow(db, payload.workflow_id, current_user)
    version = _require_version(db, workflow.id, payload.version_number)
    _build_providers(
        request.app,
        db,
        version,
        current_user,
        model_profile_id=payload.model_profile_id,
    )
    run = create_run(db, workflow, version, current_user.id, payload.model_dump())
    db.commit()
    if payload.mode == "async":
        response.status_code = status.HTTP_202_ACCEPTED
        background_tasks.add_task(execute_persisted_run, request.app, run.id, payload.input)
        return _run_read(run)
    completed = execute_persisted_run(request.app, run.id, payload.input)
    if completed is None:
        raise HTTPException(status_code=500, detail={"code": "run_missing", "message": "run disappeared"})
    return _run_read(completed)


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run_endpoint(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> RunRead:
    return _run_read(_require_run(db, run_id, current_user))


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run_endpoint(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> RunRead:
    run = _require_run(db, run_id, current_user)
    if run.status in {"succeeded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail={"code": "terminal_run", "message": "completed runs cannot be cancelled"},
        )
    run.status = "cancelled"
    run.finished_at = datetime.now(UTC)
    db.commit()
    return _run_read(run)


@router.get("/runs/{run_id}/traces", response_model=list[TraceRead])
def list_traces_endpoint(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> list[TraceRead]:
    run = _require_run(db, run_id, current_user)
    traces = list(
        db.scalars(
            select(NodeTrace)
            .where(NodeTrace.run_id == run.id)
            .order_by(NodeTrace.sequence, NodeTrace.created_at, NodeTrace.id)
        )
    )
    return [_trace_read(trace) for trace in traces]


@router.get("/runs/{run_id}/evidence/{evidence_id}", response_model=EvidenceRead)
def get_evidence_endpoint(
    run_id: str,
    evidence_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> EvidenceRead:
    run = _require_run(db, run_id, current_user)
    evidence = db.scalar(
        select(RunEvidence).where(
            RunEvidence.run_id == run.id,
            RunEvidence.evidence_id == evidence_id,
        )
    )
    if evidence is None:
        raise _not_found("evidence not found")
    return _evidence_read(evidence)


@router.post("/knowledge/retrieve/preview", response_model=KnowledgePreviewRead)
def preview_knowledge_endpoint(
    payload: KnowledgePreviewRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_request_db)],
) -> KnowledgePreviewRead:
    providers = _build_providers(
        request.app,
        db,
        None,
        current_user,
        knowledge_profile_id=payload.knowledge_profile_id,
    )
    provider = providers.get("knowledge")
    if provider is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "knowledge_provider_missing", "message": "knowledge provider is not configured"},
        )
    filters = {
        "guideline_ids": payload.guideline_ids,
        "version_ids": payload.version_ids,
        "language": payload.language,
    }
    records = provider.search(payload.query, filters)
    response = [
        EvidenceRead(
            id=record.evidence_id,
            run_id="preview",
            trace_id=None,
            evidence_id=record.evidence_id,
            raw_chunk_id=record.raw_chunk_id,
            text=record.text,
            score=record.score,
            source_title=record.source_title,
            guideline_id=record.guideline_id,
            version_id=record.version_id,
            locator=record.locator,
            source_level=record.source_level,
            open_url=record.open_url,
            created_at=datetime.now(UTC),
        )
        for record in records
    ]
    return KnowledgePreviewRead(evidence=response)
