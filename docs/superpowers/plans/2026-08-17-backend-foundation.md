# Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable FastAPI backend slice for the breast-cancer decision-agent platform: local two-role authentication, profile governance, immutable workflow versions, full-JSON extraction preview, validated decision graphs, and a reference workflow template.

**Architecture:** A modular FastAPI application under `backend/` uses synchronous SQLAlchemy sessions so SQLite and PostgreSQL share the same code path. Domain modules expose typed Pydantic contracts and service functions; routers perform authentication, authorization, validation, and HTTP translation only. Runtime execution, RAG calls, LLM calls, traces, and prompt optimization are intentionally deferred to the next backend plan, but their node types and stored graph contracts are established here.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, SQLite by default, PostgreSQL via `DATABASE_URL`, `pwdlib[argon2]`, opaque bearer sessions, httpx, pytest, pytest-asyncio, and ruff.

## Global Constraints

- Match the knowledgebase runtime: Python `>=3.12,<3.13`.
- Default local deployment uses SQLite and in-process execution; PostgreSQL is selected with `DATABASE_URL`.
- The only roles in this phase are `admin_developer` and `medical_user`.
- Ordinary users must not receive or submit hidden technical Profile parameters; backend authorization is mandatory even when the frontend hides controls.
- API keys, password hashes, session tokens, and database credentials never enter workflow JSON, logs, exports, or test fixtures.
- Published workflow versions are immutable; edits always target a draft.
- Every write operation records actor and timestamp in `audit_log`.
- Use test-first changes and run focused tests before each commit.

---

## File Map

Create the following backend structure:

```text
backend/
  pyproject.toml
  alembic.ini
  .env.example
  app/
    __init__.py
    main.py
    api.py
    core/
      __init__.py
      config.py
      database.py
      errors.py
      security.py
    audit/
      __init__.py
      models.py
      service.py
    auth/
      __init__.py
      dependencies.py
      router.py
      schemas.py
      service.py
    users/
      __init__.py
      models.py
      router.py
      schemas.py
      service.py
    profiles/
      __init__.py
      models.py
      router.py
      schemas.py
      service.py
    graph/
      __init__.py
      schemas.py
      validation.py
    extraction/
      __init__.py
      schemas.py
      service.py
      router.py
    workflows/
      __init__.py
      models.py
      router.py
      schemas.py
      service.py
    templates/
      her2_reference.json
      router.py
  alembic/
    env.py
    script.py.mako
    versions/
  scripts/
    create_admin.py
tests/
  conftest.py
  test_health.py
  test_auth.py
  test_profiles.py
  test_graph_validation.py
  test_extraction.py
  test_workflows.py
  test_reference_template.py
```

`core` owns infrastructure and cross-cutting policies. `users`, `auth`, and `profiles` own governance. `graph`, `extraction`, and `workflows` contain domain logic and are testable without HTTP. `templates` contains a platform-native reference graph, never a ProcessOn importer.

## Task 1: Scaffold the FastAPI Application

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/api.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/errors.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- `Settings()` reads `DATABASE_URL`, `APP_ENV`, `SESSION_TTL_HOURS`, and `CORS_ORIGINS` through Pydantic Settings.
- `create_app(settings: Settings | None = None) -> FastAPI` returns the application used by both Uvicorn and tests.
- `GET /health` returns `{"status": "ok", "service": "breast-agent-backend"}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_backend_status() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "breast-agent-backend",
    }
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run from `backend/`: `python -m pytest tests/test_health.py -q`

Expected: FAIL because `app.main` and `/health` do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/platform.db"
    session_ttl_hours: int = 12
    cors_origins: str = "http://localhost:5173"


# backend/app/core/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse


async def validation_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"code": "validation_error", "message": str(exc)})


# backend/app/api.py
from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "breast-agent-backend"}


# backend/app/main.py
from fastapi import FastAPI

from app.api import router
from app.core.config import Settings
from app.core.errors import validation_error_handler


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Breast Cancer Decision Agent Backend", version="0.1.0")
    app.state.settings = settings or Settings()
    app.include_router(router)
    app.add_exception_handler(ValueError, validation_error_handler)
    return app


app = create_app()
```

Create `pyproject.toml` with this content:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "breast-agent-backend"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "alembic>=1.14,<2",
  "fastapi>=0.115,<1",
  "jsonpath-ng>=1.7,<2",
  "psycopg[binary]>=3.2,<4",
  "pwdlib[argon2]>=0.2,<1",
  "pydantic-settings>=2.7,<3",
  "sqlalchemy>=2.0,<3",
  "uvicorn[standard]>=0.32,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "ruff>=0.9,<1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m pytest tests/test_health.py -q`

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app backend/tests/test_health.py
git commit -m "feat: scaffold decision agent backend"
```

## Task 2: Add Database Models and Migrations

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/users/models.py`
- Create: `backend/app/profiles/models.py`
- Create: `backend/app/workflows/models.py`
- Create: `backend/app/audit/models.py`
- Create: `backend/app/audit/service.py`
- Create: `backend/app/core/model_registry.py`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `backend/tests/test_database.py`

**Interfaces:**
- `get_engine(settings: Settings) -> Engine` creates SQLite with `check_same_thread=False` or PostgreSQL from `DATABASE_URL`.
- `SessionLocal` is the request-scoped SQLAlchemy session factory.
- `Base.metadata` contains `app_user`, `auth_session`, `model_profile`, `knowledge_profile`, `workflow`, `workflow_version`, and `audit_log`.
- Workflow versions store canonical `definition_json`, `extraction_json`, `status`, `version_number`, and `definition_sha256`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_database.py
from sqlalchemy import inspect

from app.core.database import Base, get_engine
from app.core.config import Settings


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
```

- [ ] **Step 2: Run it and verify failure**

Run: `python -m pytest tests/test_database.py -q`

Expected: FAIL because the database module and models do not exist.

- [ ] **Step 3: Implement the models and session factory**

Use SQLAlchemy 2 typed mappings. The essential columns are:

```python
# backend/app/core/database.py
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session


class Base(DeclarativeBase):
    pass


def get_engine(settings):
    kwargs = {"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, future=True, pool_pre_ping=True, **kwargs)


def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db(factory) -> Generator[Session, None, None]:
    db = factory()
    try:
        yield db
    finally:
        db.close()
```

Use string UUID primary keys and UTC-aware `created_at`/`updated_at`. Map `User` to `app_user` because `user` is reserved by PostgreSQL. `User` has `username`, `display_name`, `password_hash`, `role`, `is_active`. `AuthSession` has `token_hash`, `user_id`, `expires_at`, and `revoked_at`. `ModelProfile` and `KnowledgeProfile` have `name`, `technical_config_json`, `medical_options_json`, `exposed_to_medical`, `is_active`, and audit timestamps. `WorkflowVersion.status` is `draft`, `published`, or `archived`; add a uniqueness constraint on `(workflow_id, version_number)` and an index on `(workflow_id, status)`. `AuditLog` stores actor ID, action, entity type/ID, metadata JSON, and timestamp.

Implement `record_audit(db, actor_id, action, entity_type, entity_id, metadata)` in `app/audit/service.py`; it inserts one `AuditLog`, flushes the session, and never includes passwords, tokens, API keys, or full patient JSON in `metadata`.

Configure Alembic `target_metadata = Base.metadata` after importing every model in `model_registry.py`; generate `0001_initial.py` with `alembic revision --autogenerate -m "initial backend governance"`, then inspect the generated migration before running it.

Update `create_app` to call `get_engine(app.state.settings)`, store the engine as `app.state.engine`, create `app.state.db_factory = session_factory(engine)`, and make `get_db(request)` read that factory from the request application. Extend `backend/tests/conftest.py` with a `client` fixture that creates a temporary SQLite database, calls `Base.metadata.create_all(client.app.state.engine)`, and returns `TestClient(app)`; this fixture is the common database boundary for Tasks 3-8.

- [ ] **Step 4: Run tests and migration**

Run: `python -m pytest tests/test_database.py -q` and `alembic upgrade head` with `DATABASE_URL=sqlite:///./data/test-migration.db`.

Expected: the test passes and Alembic creates all seven tables.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/database.py backend/app/core/model_registry.py backend/app/users backend/app/profiles backend/app/workflows backend/app/audit backend/alembic backend/tests/test_database.py
git commit -m "feat: add backend governance database schema"
```

## Task 3: Implement Local Authentication and Role Enforcement

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/router.py`
- Create: `backend/app/users/schemas.py`
- Create: `backend/app/users/service.py`
- Create: `backend/app/users/router.py`
- Create: `backend/scripts/create_admin.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- `POST /api/v1/auth/login` accepts `{username, password}` and returns `{access_token, token_type, expires_at}`.
- `POST /api/v1/auth/logout` revokes the current opaque bearer session.
- `GET /api/v1/me` returns the current user and role.
- `require_role("admin_developer")` and `get_current_user` are reusable FastAPI dependencies.
- `POST /api/v1/users` is admin/developer-only and creates a medical or admin/developer account.

- [ ] **Step 1: Write failing auth tests**

```python
# backend/tests/test_auth.py
def test_medical_user_can_login_and_read_own_role(client, seed_users):
    response = client.post("/api/v1/auth/login", json={"username": "doctor", "password": "doctor-pass"})
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "medical_user"


def test_medical_user_cannot_create_users(client, medical_token):
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"username": "other", "display_name": "Other", "password": "secret-pass", "role": "medical_user"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_auth.py -q`

Expected: FAIL because the auth routes, fixtures, and dependencies do not exist.

- [ ] **Step 3: Implement secure sessions**

Hash passwords with `pwdlib.PasswordHash.recommended()`. Generate a random bearer token with `secrets.token_urlsafe(32)`, store only `sha256(token)` in `auth_session`, and expire it using `Settings.session_ttl_hours`. `get_current_user` hashes the presented token, rejects missing/expired/revoked sessions, and loads an active user. Implement logout by setting `revoked_at` and return HTTP 204. Never log the raw token or password.

Use this dependency contract:

```python
def require_role(*roles: str):
    def dependency(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "insufficient role"})
        return current_user
    return dependency
```

Extend `backend/tests/conftest.py` with deterministic fixtures: `seed_users` inserts `admin`/`admin-pass` and `doctor`/`doctor-pass`, `admin_token` and `medical_token` call the login endpoint, and `other_medical_token` inserts a second medical user before login. Hash fixture passwords through the same `hash_password` function used by production code so tests never store plaintext hashes.

Also add these reusable fixtures after the workflow routes exist:

```python
@pytest.fixture
def minimal_valid_graph():
    return {
        "nodes": [
            {"id": "input", "type": "input", "name": "输入", "input_ports": [], "output_ports": ["out"]},
            {"id": "output", "type": "output", "name": "输出", "input_ports": ["in"], "output_ports": []},
        ],
        "edges": [{"id": "e1", "source": "input", "target": "output", "source_port": "out", "target_port": "in", "kind": "normal"}],
    }


@pytest.fixture
def workflow_owned_by_other(client, other_medical_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {other_medical_token}"}
    created = client.post("/api/v1/workflows", headers=headers, json={"name": "Other workflow", "description": "fixture"})
    workflow_id = created.json()["id"]
    client.patch(f"/api/v1/workflows/{workflow_id}/draft", headers=headers, json={"graph": minimal_valid_graph})
    return workflow_id
```

The admin creation script prompts for a password without echoing it, creates the first `admin_developer` account, and refuses to overwrite an existing username.

- [ ] **Step 4: Run focused and regression tests**

Run: `python -m pytest tests/test_auth.py tests/test_health.py -q`.

Expected: all tests pass, including 401 for missing tokens, 401 for bad credentials, 403 for role violations, and successful logout invalidation.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/app/auth backend/app/users backend/scripts/create_admin.py backend/app/api.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: add local role-based authentication"
```

## Task 4: Add Model and Knowledge Profile Governance

**Files:**
- Create: `backend/app/profiles/schemas.py`
- Create: `backend/app/profiles/service.py`
- Create: `backend/app/profiles/router.py`
- Create: `backend/tests/test_profiles.py`
- Modify: `backend/app/api.py`

**Interfaces:**
- `GET /api/v1/model-profiles` returns full technical fields only to admin/developer and a redacted approved list to medical users.
- `POST/PATCH /api/v1/model-profiles` and `POST/PATCH /api/v1/knowledge-profiles` require admin/developer.
- `GET /api/v1/knowledge-profiles` exposes only `id`, `name`, `description`, `exposed_to_medical`, and `medical_options` to medical users.
- A Profile’s `technical_config_json` is never included in medical-user responses.

- [ ] **Step 1: Write failing redaction and authorization tests**

```python
def test_medical_profile_list_hides_rag_technical_parameters(client, admin_token, medical_token):
    created = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Breast KB",
            "description": "approved local knowledgebase",
            "technical_config": {"top_k": 5, "bm25": True, "score_threshold": 0.3, "deduplication": True},
            "medical_options": {"scope": "active_guidelines"},
            "exposed_to_medical": True,
        },
    )
    assert created.status_code == 201

    response = client.get("/api/v1/knowledge-profiles", headers={"Authorization": f"Bearer {medical_token}"})
    assert response.status_code == 200
    body = response.json()[0]
    assert body["name"] == "Breast KB"
    assert "top_k" not in body
    assert "bm25" not in body
    assert "score_threshold" not in body
    assert "deduplication" not in body


def test_medical_user_cannot_patch_profile(client, admin_token, medical_token):
    created = client.post(
        "/api/v1/knowledge-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Breast KB", "technical_config": {"top_k": 5}, "medical_options": {}, "exposed_to_medical": True},
    )
    profile_id = created.json()["id"]
    response = client.patch(
        f"/api/v1/knowledge-profiles/{profile_id}",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"technical_config": {"top_k": 100}},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_profiles.py -q`.

Expected: FAIL because profile routers and redaction schemas do not exist.

- [ ] **Step 3: Implement role-specific schemas and services**

Define separate response models rather than deleting fields after serialization:

```python
class MedicalProfileRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    exposed_to_medical: bool
    medical_options: dict[str, Any]


class AdminProfileRead(MedicalProfileRead):
    technical_config: dict[str, Any]
    secret_ref: str | None = None
```

Validate administrator technical configuration before storage: `top_k >= 1`, `score_threshold` in `[0, 1]`, retries non-negative, timeout positive, and only supported providers. Store secrets as environment-variable references such as `KB_API_KEY_REF`, never as values. Medical users may choose only `is_active=True` and `exposed_to_medical=True` Profiles.

Call `record_audit` for Profile create/update/activate/deactivate operations with only profile ID, changed field names, and actor ID in metadata.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_profiles.py tests/test_auth.py -q`.

Expected: all profile visibility, role enforcement, range validation, and audit assertions pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/profiles backend/app/api.py backend/tests/test_profiles.py
git commit -m "feat: govern model and knowledge profiles by role"
```

## Task 5: Define Workflow Graph Contracts and Validation

**Files:**
- Create: `backend/app/graph/schemas.py`
- Create: `backend/app/graph/validation.py`
- Create: `backend/tests/test_graph_validation.py`

**Interfaces:**
- `NodeType` includes `input`, `condition`, `python_rule`, `rag`, `llm`, `parallel_agent`, `output`, `clinical_task`, `subworkflow`, and `annotation`.
- `WorkflowGraph(nodes: list[NodeSpec], edges: list[EdgeSpec])` is the persisted graph contract.
- `validate_graph(graph: WorkflowGraph) -> list[GraphIssue]` returns structured issues; `assert_valid_graph(graph)` raises `GraphValidationError`.

- [ ] **Step 1: Write failing graph tests**

```python
def make_graph(edges):
    node_ids = {name for edge in edges for name in edge[:2]} | {"output"}
    node_types = {"input": "input", "output": "output", "condition": "condition", "task": "clinical_task"}
    nodes = [
        {"id": node_id, "type": node_types.get(node_id, "clinical_task"), "name": node_id, "input_ports": ["in"], "output_ports": ["out"]}
        for node_id in sorted(node_ids)
    ]
    edge_values = []
    for index, edge in enumerate(edges):
        options = edge[3] if len(edge) > 3 else {}
        edge_values.append({
            "id": f"e-{index}",
            "source": edge[0],
            "target": edge[1],
            "kind": edge[2] if len(edge) > 2 else "normal",
            "branch_label": options.get("label"),
            "loop_policy": options if len(edge) > 2 and edge[2] == "reassessment" else None,
        })
    return WorkflowGraph.model_validate({"nodes": nodes, "edges": edge_values})


def test_graph_rejects_normal_cycle():
    graph = make_graph([("input", "condition"), ("condition", "input")])
    issues = validate_graph(graph)
    assert any(issue.code == "normal_cycle" for issue in issues)


def test_graph_allows_bounded_reassessment_cycle():
    graph = make_graph([
        ("input", "condition"),
        ("condition", "task"),
        ("task", "condition", "reassessment", {"max_iterations": 2, "exit_condition": "资料足够"}),
        ("condition", "output"),
    ])
    assert validate_graph(graph) == []


def test_graph_preserves_multibranch_labels():
    graph = make_graph([
        ("input", "condition"),
        ("condition", "output", "branch", {"label": "证据不足"}),
    ])
    assert graph.edges[1].branch_label == "证据不足"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_graph_validation.py -q`.

Expected: FAIL because graph contracts and validation do not exist.

- [ ] **Step 3: Implement typed graph contracts**

`NodeSpec` contains `id`, `type`, `name`, `position`, `input_ports`, `output_ports`, `config`, and `metadata`. `EdgeSpec` contains `source`, `target`, `source_port`, `target_port`, `kind`, `branch_label`, and optional `loop_policy`. `loop_policy` requires `max_iterations` between 1 and 10 plus a non-empty `exit_condition`.

Validation must check unique node IDs, existing edge endpoints, at least one input and output node, no incoming edge to input, no outgoing edge from output, reachable executable nodes, valid ports, and cycles. Remove reassessment edges before ordinary topological cycle checking; reject every remaining cycle. Preserve all labels and return `node_id`/`edge_id` in each issue.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_graph_validation.py -q`.

Expected: all graph tests pass, including missing endpoints, missing output, invalid loop policy, and unreachable node cases.

- [ ] **Step 5: Commit**

```bash
git add backend/app/graph backend/tests/test_graph_validation.py
git commit -m "feat: validate decision workflow graphs"
```

## Task 6: Implement Full-JSON Extraction and Preview

**Files:**
- Create: `backend/app/extraction/schemas.py`
- Create: `backend/app/extraction/service.py`
- Create: `backend/app/extraction/router.py`
- Create: `backend/tests/test_extraction.py`

**Interfaces:**
- `ExtractionConfig(groups: list[ExtractionGroup])` is stored in a workflow version.
- `preview_extraction(payload: dict[str, Any], config: ExtractionConfig) -> ExtractionPreview` returns grouped values, missing fields, and sufficiency status.
- `POST /api/v1/workflows/{workflow_id}/draft/extraction/preview` accepts sample JSON and an extraction config.

- [ ] **Step 1: Write failing extraction tests**

```python
def test_preview_groups_path_values_and_latest_array_record():
    payload = {
        "院内数据": {"住院文书": [
            {"日期": "2026-01-01", "类型": "病程", "文本": "旧"},
            {"日期": "2026-01-03", "类型": "病程", "文本": "新"},
        ]},
        "病理": {"HER2": "IHC 3+"},
    }
    config = ExtractionConfig.model_validate({"groups": [{
        "id": "baseline", "label": "基线资料", "required": ["her2"],
        "fields": [{"alias": "her2", "path": "$.病理.HER2", "type": "string"},
                    {"alias": "latest_record", "path": "$.院内数据.住院文书", "type": "object", "array": {"take": "latest", "sort_by": "日期"}}],
    }]})

    result = preview_extraction(payload, config)

    assert result.groups["baseline"]["her2"] == "IHC 3+"
    assert result.groups["baseline"]["latest_record"]["文本"] == "新"
    assert result.sufficiency["baseline"].status == "sufficient"


def test_preview_reports_missing_required_field():
    config = ExtractionConfig.model_validate({"groups": [{"id": "pathology", "label": "病理信息", "required": ["er"], "fields": [{"alias": "er", "path": "$.病理.ER", "type": "string"}]}]})
    result = preview_extraction({}, config)
    assert result.missing["pathology"] == ["er"]
    assert result.sufficiency["pathology"].status == "insufficient"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_extraction.py -q`.

Expected: FAIL because extraction contracts and resolver do not exist.

- [ ] **Step 3: Implement the extraction contract**

Define `ExtractionField(alias, path, type, required, default, array)`, `ArraySelection(filter, sort_by, order, take, time_from, time_to)`, `ExtractionGroup(id, label, fields, required)`, and `ExtractionPreview(groups, missing, sufficiency, errors)`. Resolve `$.a.b[0]` paths with a structured parser; do not use ad hoc string splitting for array filters. Apply typed conversion only when explicitly configured. For `take=latest`/`first`, require `sort_by` and compare ISO dates or numeric timestamps; for `all`, preserve source order. Return field-level errors rather than silently dropping invalid paths.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_extraction.py -q`.

Expected: all extraction tests pass, including nested objects, arrays, filters, defaults, type mismatch, time windows, and invalid paths.

- [ ] **Step 5: Commit**

```bash
git add backend/app/extraction backend/tests/test_extraction.py
git commit -m "feat: add grouped JSON extraction preview"
```

## Task 7: Add Immutable Workflow Draft and Version APIs

**Files:**
- Create: `backend/app/workflows/schemas.py`
- Create: `backend/app/workflows/service.py`
- Create: `backend/app/workflows/router.py`
- Modify: `backend/app/api.py`
- Create: `backend/tests/test_workflows.py`

**Interfaces:**
- `POST /api/v1/workflows` creates a workflow and its first draft.
- `GET /api/v1/workflows` lists only workflows visible to the current user.
- `GET/PATCH /api/v1/workflows/{workflow_id}/draft` reads or updates draft metadata, graph JSON, extraction JSON, and template references.
- `POST /api/v1/workflows/{workflow_id}/publish` validates and publishes the draft, creates an immutable version number, and starts a fresh draft copy.
- `GET /api/v1/workflows/{workflow_id}/versions` lists immutable versions.

- [ ] **Step 1: Write failing workflow tests**

```python
def test_publish_freezes_definition_and_creates_next_draft(client, medical_token, minimal_valid_graph):
    headers = {"Authorization": f"Bearer {medical_token}"}
    created = client.post("/api/v1/workflows", headers=headers, json={"name": "HER2 test", "description": "demo"})
    workflow_id = created.json()["id"]
    client.patch(f"/api/v1/workflows/{workflow_id}/draft", headers=headers, json={"graph": minimal_valid_graph})

    published = client.post(f"/api/v1/workflows/{workflow_id}/publish", headers=headers)
    assert published.status_code == 201
    assert published.json()["version_number"] == 1

    update = client.patch(f"/api/v1/workflows/{workflow_id}/versions/1", headers=headers, json={"description": "mutate"})
    assert update.status_code == 405


def test_medical_user_cannot_edit_another_users_workflow(client, medical_token, other_medical_token, workflow_owned_by_other):
    response = client.patch(
        f"/api/v1/workflows/{workflow_owned_by_other}/draft",
        headers={"Authorization": f"Bearer {medical_token}"},
        json={"description": "unauthorized"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_workflows.py -q`.

Expected: FAIL because workflow services and routes do not exist.

- [ ] **Step 3: Implement version service**

Canonicalize graph and extraction JSON with sorted keys and compact separators, hash UTF-8 bytes with SHA-256, and store the hash in `workflow_version.definition_sha256`. `publish` must run `assert_valid_graph` and extraction schema validation in one transaction, mark the draft as published, create the next draft with the same definition, and write an audit event. Reject all PATCH/DELETE operations targeting published versions with HTTP 405. Medical users may mutate only workflows they own; admin/developers may mutate any workflow. Create, draft update, publish, archive, and rollback requests must call `record_audit` with actor ID, workflow/version ID, action, and changed field names; never include raw patient JSON.

- [ ] **Step 4: Run focused and regression tests**

Run: `python -m pytest tests/test_workflows.py tests/test_graph_validation.py tests/test_extraction.py -q`.

Expected: all tests pass, including version numbering, hash stability, ownership, admin override, invalid graph rejection, and immutable version behavior.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workflows backend/app/api.py backend/tests/test_workflows.py
git commit -m "feat: add immutable workflow version APIs"
```

## Task 8: Add the Native HER2 Reference Workflow Template

**Files:**
- Create: `backend/app/templates/her2_reference.json`
- Create: `backend/app/templates/router.py`
- Modify: `backend/app/api.py`
- Create: `backend/tests/test_reference_template.py`

**Interfaces:**
- `GET /api/v1/templates/her2-advanced` returns a platform-native `WorkflowGraph` template and its extraction groups.
- `POST /api/v1/templates/her2-advanced/clone` creates a draft owned by the current user.

- [ ] **Step 1: Write failing template tests**

```python
def test_reference_template_contains_required_node_families(client, medical_token):
    response = client.get("/api/v1/templates/her2-advanced", headers={"Authorization": f"Bearer {medical_token}"})
    assert response.status_code == 200
    body = response.json()
    types = {node["type"] for node in body["graph"]["nodes"]}
    assert {"input", "condition", "clinical_task", "rag", "llm", "subworkflow", "output"} <= types
    labels = {edge.get("branch_label") for edge in body["graph"]["edges"]}
    assert {"是", "否", "证据不足", "资料不足"} <= labels


def test_medical_user_can_clone_reference_template(client, medical_token):
    response = client.post("/api/v1/templates/her2-advanced/clone", headers={"Authorization": f"Bearer {medical_token}"}, json={"name": "我的 HER2 流程"})
    assert response.status_code == 201
    assert response.json()["name"] == "我的 HER2 流程"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_reference_template.py -q`.

Expected: FAIL because the template and routes do not exist.

- [ ] **Step 3: Implement the native template**

Create JSON using the platform graph contract, not `.pos`. Include input groups for pathology, baseline, and treatment background; a pathology-confirmed decision; a clinical task for missing pathology; a bounded reassessment edge; a HER2 multi-outcome decision with `是`, `否`, and `证据不足`; a RAG node with an approved Breast Knowledgebase Profile; LLM nodes for acute management, fertility protection, treatment-line/HR assessment, brain-metastasis assessment, and final synthesis; an MDT subworkflow reference; and output/path-transfer nodes. Include branch labels and `metadata.department`, `metadata.risk`, `metadata.external_refs` without embedding patient data or credentials. The template is illustrative and must display a medical-review warning.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_reference_template.py tests/test_workflows.py -q`.

Expected: the template validates, clones as a draft, and retains all branch labels and RAG/LLM configuration references.

- [ ] **Step 5: Commit**

```bash
git add backend/app/templates backend/app/api.py backend/tests/test_reference_template.py
git commit -m "feat: add native HER2 workflow template"
```

## Task 9: Add Local and Docker Backend Startup

**Files:**
- Create: `backend/.env.example`
- Create: `backend/Dockerfile`
- Create: `backend/compose.yml`
- Create: `backend/scripts/run_backend.ps1`
- Create: `backend/scripts/run_backend.sh`
- Modify: `README.md`
- Create: `backend/tests/test_startup_config.py`

**Interfaces:**
- Non-Docker: `powershell -ExecutionPolicy Bypass -File backend/scripts/run_backend.ps1` starts Uvicorn on `127.0.0.1:8000` with SQLite.
- Non-Docker POSIX: `bash backend/scripts/run_backend.sh` uses the same settings.
- Docker image runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`; database URL is injected by Compose or the environment.

- [ ] **Step 1: Write the failing startup configuration test**

```python
from app.core.config import Settings


def test_default_database_is_local_sqlite():
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("sqlite:///")


def test_database_url_can_select_postgres():
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://user:pass@db/platform")
    assert settings.database_url.startswith("postgresql+psycopg://")
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_startup_config.py -q`.

Expected: FAIL until Settings and startup scripts are wired to the backend package.

- [ ] **Step 3: Implement startup assets**

`.env.example` must contain `APP_ENV=development`, `DATABASE_URL=sqlite:///./data/platform.db`, `SESSION_TTL_HOURS=12`, and `CORS_ORIGINS=http://localhost:5173`, with no credentials. The PowerShell and shell scripts create `backend/data`, set `PYTHONPATH` to `backend`, and run Uvicorn on loopback. The Dockerfile installs the project into a slim Python 3.12 image and runs as a non-root user. `backend/compose.yml` starts the backend and PostgreSQL with a named database volume, maps the API to `127.0.0.1:8000`, and reads the application image's `DATABASE_URL` from the Compose service name `postgres`. Do not add Redis to this foundation image; the execution phase will add it only when needed.

- [ ] **Step 4: Run verification**

Run: `python -m pytest -q`, `python -m ruff check app tests`, and start the local server with the PowerShell script; verify `Invoke-RestMethod http://127.0.0.1:8000/health` returns status `ok`.

Expected: all backend foundation tests pass and the documented non-Docker startup works.

- [ ] **Step 5: Commit**

```bash
git add backend/.env.example backend/Dockerfile backend/compose.yml backend/scripts README.md backend/tests/test_startup_config.py
git commit -m "chore: add backend local and docker startup"
```

## Self-Review Checklist

- [ ] The plan covers role-based local auth, Profile redaction, audit records, extraction page behavior, immutable versions, controlled reassessment loops, native node families, and the reference workflow.
- [ ] No `.pos` importer is planned; the supplied file is only a design reference.
- [ ] RAG execution, clickable evidence API implementation, Chat Completions calls, Python sandbox execution, run traces, parallel Agent scheduling, and prompt optimization are explicitly deferred to the next backend execution plan rather than silently omitted.
- [ ] Ordinary users cannot see or submit `temperature`, `top_k`, BM25, score threshold, deduplication, timeout, or retry values.
- [ ] Every task has a failing test, a focused run command, a minimal implementation direction, a passing test command, and a commit.

## Next Backend Plan Boundary

After this foundation is reviewed and complete, create a separate plan for runtime execution: `KnowledgeBaseAdapter` and source-viewer endpoints, RAG node execution, OpenAI Chat Completions model gateway, restricted Python runner, DAG/reassessment scheduler, node traces, online runs, and prompt optimization. This separation keeps the first backend slice independently runnable and reviewable.
