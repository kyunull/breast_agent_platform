# Runtime Workflow Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local runtime layer that executes workflow graphs, calls OpenAI-compatible models and knowledge bases, records node traces/evidence, and creates prompt-optimization drafts.

**Architecture:** Keep the existing FastAPI modular monolith. Add persistence for runs, traces, evidence, and prompt candidates; keep provider-specific calls behind model and knowledge adapters; execute the graph through a deterministic scheduler with bounded reassessment edges and an in-process async mode.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, httpx, pytest, existing JSON extraction and graph validation modules.

## Global Constraints

- The synchronous `POST /api/v1/runs` path returns a completed result; `mode=async` returns a `run_id` and uses in-process background execution.
- OpenAI calls use `POST {base_url}/chat/completions`; secrets are environment references only.
- The local Breast Knowledgebase contract is `POST /search` with evidence-only responses; no generated answer is accepted from the knowledgebase.
- Medical users cannot see or submit temperature, top_k, BM25, score threshold, deduplication, timeout, or retry settings.
- Patient input is hashed and summarized; raw patient JSON is not persisted by default.
- Every production behavior is introduced by a failing test first and then a minimal implementation.
- Existing 69 foundation tests must remain passing.

---

### Task 1: Runtime Persistence and Contracts

**Files:**
- Create: `backend/app/runtime/models.py`
- Create: `backend/app/runtime/schemas.py`
- Create: `backend/app/runtime/service.py`
- Create: `backend/alembic/versions/0002_runtime_execution.py`
- Modify: `backend/app/core/database.py`, `backend/app/api.py`
- Test: `backend/tests/test_runtime_models.py`

**Interfaces:**
- `WorkflowRun`, `NodeTrace`, `RunEvidence`, and `PromptOptimization` SQLAlchemy models.
- `create_run(db, workflow, version, actor_id, payload) -> WorkflowRun`.
- `append_trace(db, run_id, trace_data) -> NodeTrace`.
- `store_evidence(db, run_id, trace_id, evidence) -> RunEvidence`.
- Pydantic schemas `RunCreate`, `RunRead`, `TraceRead`, `EvidenceRead`, and `PromptOptimizationRead`.

- [ ] **Step 1: Write failing persistence tests** for run status transitions, trace/evidence foreign keys, input hash stability, and prompt candidate storage.
- [ ] **Step 2: Run `python -m pytest tests/test_runtime_models.py -q` and confirm missing-model failures.**
- [ ] **Step 3: Implement models, repository helpers, schemas, and Alembic migration with status constraints and indexes.**
- [ ] **Step 4: Run the focused tests and `python -m alembic upgrade head`; expect all persistence tests to pass.**
- [ ] **Step 5: Commit `feat: add runtime execution persistence`.**

### Task 2: Model and Knowledge Adapters

**Files:**
- Create: `backend/app/runtime/model_gateway.py`
- Create: `backend/app/runtime/knowledge_gateway.py`
- Modify: `backend/pyproject.toml`, `backend/app/profiles/schemas.py`
- Test: `backend/tests/test_runtime_adapters.py`

**Interfaces:**
- `OpenAICompatibleGateway.complete(profile, messages, response_format=None) -> ChatCompletionResult`.
- `KnowledgeBaseAdapter.search(profile, query, filters) -> list[EvidenceRecord]`.
- `normalize_knowledge_response(payload) -> list[EvidenceRecord]`.

- [ ] **Step 1: Write failing adapter tests** using `httpx.MockTransport` for the exact `/chat/completions` request, API-key environment reference, retry/timeout failure, KB `/search` response normalization, stable evidence IDs, and malformed responses.
- [ ] **Step 2: Run `python -m pytest tests/test_runtime_adapters.py -q` and verify the gateway modules are absent.**
- [ ] **Step 3: Add runtime `httpx` dependency and implement redacted request logging, Chat Completions conversion, KB profile mapping, and evidence normalization.**
- [ ] **Step 4: Run focused adapter tests and Ruff.**
- [ ] **Step 5: Commit `feat: add model and knowledge gateways`.**

### Task 3: Node Executors and Scheduler

**Files:**
- Create: `backend/app/runtime/context.py`
- Create: `backend/app/runtime/conditions.py`
- Create: `backend/app/runtime/python_runner.py`
- Create: `backend/app/runtime/executors.py`
- Create: `backend/app/runtime/engine.py`
- Test: `backend/tests/test_runtime_engine.py`, `backend/tests/test_python_runner.py`

**Interfaces:**
- `ExecutionContext` and `NodeResult` from the design spec.
- `evaluate_condition(config, context) -> ConditionResult`.
- `RestrictedPythonRunner.run(source, inputs, timeout_seconds) -> dict[str, object]`.
- `WorkflowEngine.execute(graph, extraction, raw_input, providers, trace_sink) -> ExecutionResult`.

- [ ] **Step 1: Write failing tests** for condition operators and unknown values, forbidden Python AST constructs, Python list/text extraction, topological execution, branch labels, bounded reassessment, parallel agents, RAG-to-LLM evidence inheritance, output transfer, and node failure traces.
- [ ] **Step 2: Run the focused engine and runner tests and confirm failures.**
- [ ] **Step 3: Implement the pure condition evaluator, subprocess Python runner, node executors, deterministic scheduler, and bounded loop counter.**
- [ ] **Step 4: Run focused tests, then the existing graph/extraction test suites.**
- [ ] **Step 5: Commit `feat: execute workflow graph nodes`.**

### Task 4: Run, Trace, Evidence, and Preview APIs

**Files:**
- Create: `backend/app/runtime/router.py`
- Modify: `backend/app/api.py`, `backend/app/main.py`
- Test: `backend/tests/test_runtime_api.py`

**Interfaces:**
- `POST /api/v1/runs`, `GET /api/v1/runs/{run_id}`, `POST /api/v1/runs/{run_id}/cancel`, `GET /api/v1/runs/{run_id}/traces`, `GET /api/v1/runs/{run_id}/evidence/{evidence_id}`.
- `POST /api/v1/knowledge/retrieve/preview`.

- [ ] **Step 1: Write failing API tests** for sync success, async status polling, unauthorized/foreign access, node traces, evidence detail, RAG preview, model/profile governance, failed nodes, and cancellation.
- [ ] **Step 2: Run `python -m pytest tests/test_runtime_api.py -q` and confirm missing routes.**
- [ ] **Step 3: Wire repositories, provider factories, engine execution, FastAPI background tasks, role filtering, and response redaction.**
- [ ] **Step 4: Run runtime API tests plus the complete backend suite.**
- [ ] **Step 5: Commit `feat: add workflow runtime APIs`.**

### Task 5: Prompt Optimization API

**Files:**
- Create: `backend/app/runtime/optimization.py`
- Modify: `backend/app/runtime/router.py`, `backend/app/runtime/schemas.py`
- Test: `backend/tests/test_prompt_optimization.py`

**Interfaces:**
- `create_prompt_optimization(db, run_id, node_id, instruction, actor_id) -> PromptOptimization`.
- `apply_prompt_optimization(db, candidate_id, actor_id) -> WorkflowVersion`.
- `POST /api/v1/prompt-optimizations`, `GET /api/v1/prompt-optimizations/{id}`, `POST /api/v1/prompt-optimizations/{id}/apply`.

- [ ] **Step 1: Write failing tests** for extracting the selected LLM trace, candidate generation through the model gateway, input hash recording, role access, and applying a candidate to a new draft without changing a published version.
- [ ] **Step 2: Run the focused optimization tests and confirm missing endpoints.**
- [ ] **Step 3: Implement candidate generation, redacted result diffing, persistence, and draft-only apply.**
- [ ] **Step 4: Run focused tests and the complete suite.**
- [ ] **Step 5: Commit `feat: add prompt optimization APIs`.**

### Task 6: Integration Verification and Documentation

**Files:**
- Modify: `README.md`, `backend/.env.example`, `docs/superpowers/specs/2026-08-18-runtime-execution-design.md`
- Test: `backend/tests/test_runtime_integration.py`

- [ ] **Step 1: Write an integration test** that runs a native graph through extraction, condition, Python rule, mock RAG, mock Chat Completions, output transfer, trace lookup, and evidence lookup.
- [ ] **Step 2: Run the integration test and confirm it fails before wiring all providers.**
- [ ] **Step 3: Add environment examples for `MODEL_API_KEY_REF`, `KNOWLEDGEBASE_BASE_URL`, and runtime limits; document Swagger usage and mock-provider testing.**
- [ ] **Step 4: Run `python -m pytest -q`, `python -m ruff check app tests alembic scripts`, `python -m compileall -q app tests alembic scripts`, `python -m alembic upgrade head`, and `docker compose -f compose.yml config --quiet`.**
- [ ] **Step 5: Commit `docs: document runtime execution and verification`.**

## Self-Review Checklist

- [ ] The plan covers every approved runtime endpoint and node family.
- [ ] Evidence can be opened from a run without relying on a knowledgebase-generated answer.
- [ ] Ordinary-user technical parameters remain hidden at both schema and response layers.
- [ ] Raw patient JSON and credentials are excluded from traces and prompt candidates.
- [ ] Sync and explicit async paths are independently tested.
- [ ] Existing foundation tests remain part of every final verification run.
