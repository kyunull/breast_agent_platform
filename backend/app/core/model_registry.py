"""Import every mapped model so Alembic sees the complete metadata."""

from app.audit.models import AuditLog
from app.profiles.models import KnowledgeProfile, ModelProfile
from app.runtime.models import NodeTrace, PromptOptimization, RunEvidence, WorkflowRun
from app.users.models import AuthSession, User
from app.workflows.models import Workflow, WorkflowVersion

__all__ = [
    "AuditLog",
    "AuthSession",
    "KnowledgeProfile",
    "ModelProfile",
    "NodeTrace",
    "PromptOptimization",
    "RunEvidence",
    "User",
    "Workflow",
    "WorkflowRun",
    "WorkflowVersion",
]
