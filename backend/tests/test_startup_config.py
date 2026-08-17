from pathlib import Path

from app.core.config import Settings


def test_default_database_is_local_sqlite() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.startswith("sqlite:///")


def test_database_url_can_select_postgres() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@db/platform",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_startup_assets_are_checked_in() -> None:
    backend_dir = Path(__file__).resolve().parents[1]

    for relative_path in (
        ".env.example",
        "Dockerfile",
        "compose.yml",
        "scripts/run_backend.ps1",
        "scripts/run_backend.sh",
    ):
        assert (backend_dir / relative_path).is_file(), relative_path
