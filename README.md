# Breast Cancer Decision Agent Platform

This repository currently contains the backend foundation for a breast-cancer decision workflow platform. It provides two-role authentication, governed model and knowledge-base profiles, JSON extraction preview, validated workflow graphs, immutable workflow versions, and a native HER2 reference template.

Runtime execution, RAG retrieval, OpenAI-compatible Chat Completions calls, restricted Python rules, node traces, online tests, and prompt optimization belong to the next backend phase.

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

Copy `backend/.env.example` to `backend/.env` for non-Docker use. The default database is `backend/data/platform.db`. Set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL such as `postgresql+psycopg://user:password@host/database` to use PostgreSQL outside Compose.

## Verification

Run from `backend/`:

```sh
python -m pytest -q
python -m ruff check app tests
```
