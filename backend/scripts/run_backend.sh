#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND_DIR=$(dirname "$SCRIPT_DIR")

mkdir -p "$BACKEND_DIR/data"
export PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$BACKEND_DIR"
python -m alembic upgrade head
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
