import json

from sqlalchemy import select

from app.profiles.models import ModelProfile
from app.runtime.models import NodeTrace, PromptOptimization, RunEvidence, WorkflowRun
from app.runtime.service import append_trace, create_run, store_evidence
from app.users.models import User
from app.workflows.models import Workflow, WorkflowVersion


def _records(db):
    user = User(
        username="runtime-owner",
        display_name="Runtime Owner",
        password_hash="test-hash",
        role="admin_developer",
    )
    db.add(user)
    db.flush()
    workflow = Workflow(owner_id=user.id, name="Runtime workflow")
    db.add(workflow)
    db.flush()
    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        definition_json={"graph": {"nodes": [], "edges": []}},
        extraction_json={"groups": []},
        status="published",
        definition_sha256="a" * 64,
    )
    db.add(version)
    db.flush()
    return user, workflow, version


def test_create_run_hashes_input_and_stores_bounded_summary(client):
    db = client.app.state.db_factory()
    try:
        user, workflow, version = _records(db)
        raw_input = {"患者": {"年龄": 52, "病历": "x" * 5000}}

        run = create_run(
            db,
            workflow,
            version,
            user.id,
            {"mode": "sync", "input": raw_input},
        )
        db.commit()

        assert run.status == "queued"
        assert len(run.input_sha256) == 64
        summary = run.input_summary_json
        assert len(json.dumps(summary, ensure_ascii=False)) < 1200
        assert "病历" not in summary.get("患者", {})
    finally:
        db.close()


def test_trace_and_evidence_are_linked_to_run(client):
    db = client.app.state.db_factory()
    try:
        user, workflow, version = _records(db)
        run = create_run(db, workflow, version, user.id, {"input": {"x": 1}})
        db.flush()
        trace = append_trace(
            db,
            run.id,
            {
                "node_id": "rag-1",
                "status": "succeeded",
                "output": {"evidence_refs": ["ev-1"]},
                "evidence_refs": ["ev-1"],
            },
        )
        evidence = store_evidence(
            db,
            run.id,
            trace.id,
            {
                "evidence_id": "ev-1",
                "raw_chunk_id": "chunk-1",
                "text": "Guideline evidence",
                "score": 0.88,
                "source_title": "Breast guideline",
                "guideline_id": "caca",
                "version_id": "caca-v1",
                "locator": "PDF page 1",
                "source_level": "primary_guideline",
                "open_url": None,
            },
        )
        db.commit()

        loaded_trace = db.scalar(select(NodeTrace).where(NodeTrace.id == trace.id))
        loaded_evidence = db.scalar(select(RunEvidence).where(RunEvidence.id == evidence.id))
        assert loaded_trace is not None
        assert loaded_trace.run_id == run.id
        assert loaded_trace.evidence_refs_json == ["ev-1"]
        assert loaded_evidence is not None
        assert loaded_evidence.trace_id == trace.id
        assert loaded_evidence.text == "Guideline evidence"
    finally:
        db.close()


def test_prompt_optimization_persists_candidate_and_model_reference(client):
    db = client.app.state.db_factory()
    try:
        user, workflow, version = _records(db)
        profile = ModelProfile(
            name="Optimizer model",
            technical_config_json={},
            medical_options_json={},
            exposed_to_medical=True,
            is_active=True,
        )
        db.add(profile)
        db.flush()
        run = create_run(db, workflow, version, user.id, {"input": {"x": 1}})
        db.flush()
        candidate = PromptOptimization(
            workflow_id=workflow.id,
            node_id="llm-1",
            source_run_id=run.id,
            original_prompt="Original",
            candidate_prompt="Improved",
            instruction="Make the evidence request explicit",
            model_profile_id=profile.id,
            test_input_sha256="b" * 64,
            result_diff_json={"changed": ["prompt"]},
            status="candidate",
            created_by=user.id,
        )
        db.add(candidate)
        db.commit()

        loaded = db.scalar(select(PromptOptimization).where(PromptOptimization.id == candidate.id))
        assert loaded is not None
        assert loaded.workflow_id == workflow.id
        assert loaded.model_profile_id == profile.id
        assert loaded.status == "candidate"
    finally:
        db.close()
