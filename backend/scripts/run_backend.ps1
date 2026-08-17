$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $BackendDir "data"

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$env:PYTHONPATH = $BackendDir

Push-Location $BackendDir
try {
    python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
