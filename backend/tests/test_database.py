from sqlalchemy import inspect

from app.audit.models import AuditLog
from app.audit.service import record_audit
from app.core.config import Settings
from app.core.database import Base, get_engine, session_factory


def test_metadata_contains_governance_and_workflow_tables(tmp_path) -> None:
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
