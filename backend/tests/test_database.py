import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.audit.models import AuditLog
from app.audit.service import record_audit
from app.core.config import Settings
from app.core.database import Base, get_engine, initialize_models, session_factory
from app.users.models import User
from app.workflows.models import Workflow, WorkflowVersion


def test_metadata_contains_governance_and_workflow_tables(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) >= {
        "app_user",
        "auth_session",
        "model_profile",
        "knowledge_profile",
        "workflow",
        "workflow_version",
        "audit_log",
    }


def test_record_audit_flushes_without_sensitive_metadata(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'audit.db'}"))
    Base.metadata.create_all(engine)
    db = session_factory(engine)()

    audit = record_audit(
        db,
        actor_id=None,
        action="workflow.update",
        entity_type="workflow",
        entity_id="workflow-1",
        metadata={
            "changed_fields": ["name"],
            "password": "secret",
            "access_token": "token",
            "api_key": "key",
            "database_url": "sqlite:///credentials.db",
            "patient_json": {"full_name": "Patient"},
            "patient": {"full_name": "Patient"},
            "payload": {"full_name": "Patient"},
        },
    )

    assert audit.id is not None
    stored = db.get(AuditLog, audit.id)
    assert stored is audit
    assert stored.metadata_json == {"changed_fields": ["name"]}


def test_model_registry_initializes_on_database_import() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    expected_tables = {
        "app_user",
        "auth_session",
        "model_profile",
        "knowledge_profile",
        "workflow",
        "workflow_version",
        "audit_log",
    }
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.database import Base\n"
            + f"expected = {expected_tables!r}\n"
            + "assert expected <= set(Base.metadata.tables), sorted(Base.metadata.tables)\n",
        ],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_audit_model_can_be_imported_before_database_registry() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    expected_tables = {
        "app_user",
        "auth_session",
        "model_profile",
        "knowledge_profile",
        "workflow",
        "workflow_version",
        "audit_log",
    }
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.audit.models import AuditLog\n"
            "from app.core.database import Base\n"
            + f"expected = {expected_tables!r}\n"
            + "assert expected <= set(Base.metadata.tables), sorted(Base.metadata.tables)\n",
        ],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_user_role_constraint_is_named_and_enforced(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'role.db'}"))
    Base.metadata.create_all(engine)

    checks = inspect(engine).get_check_constraints("app_user")
    assert {check["name"] for check in checks} >= {"ck_app_user_role"}

    db = session_factory(engine)()
    db.add(
        User(
            username="invalid-role",
            display_name="Invalid",
            password_hash="hash",
            role="not-a-supported-role",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_workflow_version_hash_is_non_null_and_deterministic(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'hash.db'}"))
    Base.metadata.create_all(engine)

    assert WorkflowVersion.__table__.c.definition_sha256.nullable is False
    reflected = {
        column["name"]: column
        for column in inspect(engine).get_columns("workflow_version")
    }
    assert reflected["definition_sha256"]["nullable"] is False

    db = session_factory(engine)()
    version = WorkflowVersion(
        workflow=Workflow(name="hash-test"),
        version_number=0,
        definition_json={"nodes": []},
        extraction_json={"groups": []},
        status="draft",
    )
    db.add(version)
    db.flush()

    assert version.definition_sha256
    assert len(version.definition_sha256) == 64


def test_record_audit_drops_nested_and_scalar_secret_values(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'audit-secrets.db'}"))
    Base.metadata.create_all(engine)
    db = session_factory(engine)()

    audit = record_audit(
        db,
        actor_id="97fd7ed7-ecfb-41ca-8f9a-8512e44ea7f9",
        action="workflow.update",
        entity_type="workflow",
        entity_id="workflow-1",
        metadata={
            "actor_id": "97fd7ed7-ecfb-41ca-8f9a-8512e44ea7f9",
            "changed_fields": ["name"],
            "version_number": 1,
            "status": "token=raw-session-token",
            "notes": "api_key=raw-api-key",
            "context": {"password": "raw-password"},
            "items": [{"database_url": "sqlite:///secret.db"}],
        },
    )

    assert audit.metadata_json == {
        "actor_id": "97fd7ed7-ecfb-41ca-8f9a-8512e44ea7f9",
        "changed_fields": ["name"],
        "version_number": 1,
    }


def test_record_audit_only_persists_allowlisted_metadata_shapes(tmp_path) -> None:
    initialize_models()
    engine = get_engine(Settings(database_url=f"sqlite:///{tmp_path / 'audit-shapes.db'}"))
    Base.metadata.create_all(engine)
    db = session_factory(engine)()

    audit = record_audit(
        db,
        actor_id=None,
        action="workflow.update",
        entity_type="workflow",
        entity_id="workflow-1",
        metadata={
            "workflow_id": "97fd7ed7-ecfb-41ca-8f9a-8512e44ea7f9",
            "version_id": "not-a-uuid patient_name=Jane Doe",
            "changed_fields": [
                "name",
                "password",
                "api_key",
                '{"patient": {"full_name": "Jane Doe", "mrn": "MRN-1"}}',
            ],
            "status": "Jane Doe metastatic breast cancer payload",
            "action": "sk-live-raw-token",
        },
    )

    assert audit.metadata_json == {
        "workflow_id": "97fd7ed7-ecfb-41ca-8f9a-8512e44ea7f9",
        "changed_fields": ["name"],
    }
