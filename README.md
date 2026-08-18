# Breast Cancer Decision Agent Platform

This repository contains the backend for a breast-cancer decision workflow platform. It provides two-role authentication, governed model and knowledge-base profiles, JSON extraction preview, validated workflow graphs, immutable workflow versions, a native HER2 reference template, runtime graph execution, RAG retrieval, OpenAI-compatible Chat Completions calls, restricted Python rules, node traces, clickable evidence, online tests, and prompt optimization.

## Local startup (Windows)

Python 3.12 is required.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
cd ..
powershell -ExecutionPolicy Bypass -File backend\scripts\run_backend.ps1
```

The API listens on `http://127.0.0.1:8000`. OpenAPI documentation is at `http://127.0.0.1:8000/docs`.

The runtime endpoints are available under `/api/v1` and are directly testable from Swagger UI:

- `POST /runs` executes a published workflow synchronously, or queues it with `mode=async`.
- `GET /runs/{run_id}` and `GET /runs/{run_id}/traces` poll status and inspect every node result/error.
- `GET /runs/{run_id}/evidence/{evidence_id}` opens the normalized guideline text and source URL.
- `POST /knowledge/retrieve/preview` tests a knowledge profile without generating an answer.
- `POST /prompt-optimizations` creates a candidate from a successful LLM trace; `.../{id}/apply` writes only the current draft.

For a model profile, set `technical_config.api_key_ref` to `OPENAI_API_KEY_REF` and `base_url` to the OpenAI-compatible service root. For the local breast knowledge base, use provider `knowledgebase` and its `/search` contract; generic HTTP adapters can be selected with provider `generic_http`. The medical user receives only exposed profiles and semantic options; model temperature, retrieval `top_k`/BM25, thresholds, retries, and timeouts remain administrator/developer settings.

`mode=async` is an in-process local background task intended for development and single-process deployments. A process restart cannot resume the job because patient input is deliberately not persisted; use synchronous runs until a durable encrypted queue is deployed.

In another terminal, create the first administrator:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python scripts\create_admin.py
```

## Local startup (macOS/Linux)

```sh
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
cd ..
bash backend/scripts/run_backend.sh
```

## Docker Compose

Docker Compose starts the API with PostgreSQL and applies database migrations automatically.

```sh
cd backend
docker compose up --build
```

The published API port is bound to `127.0.0.1:8000`. The PostgreSQL port is not exposed to the host.

Create the first administrator inside the running backend container:

```sh
docker compose exec backend python scripts/create_admin.py
```

## Configuration

Copy `backend/.env.example` to `backend/.env` for non-Docker use. The default database is `backend/data/platform.db`. The launcher loads this file before resolving provider secret references. Set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL such as `postgresql+psycopg://user:password@host/database` to use PostgreSQL outside Compose.

## Verification

Run from `backend/`:

```sh
python -m pytest -q
python -m ruff check app tests
python -m compileall -q app tests alembic scripts
python -m alembic upgrade head
```
