import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client
