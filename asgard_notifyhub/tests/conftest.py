import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.client import DemoHomeAssistantClient
from app.main import create_app
from app.service import NotifyHubService
from app.settings import Settings
from app.storage import Storage

SUPERVISOR_PROXY = ("172.30.32.2", 40000)


class _ClientInjectionMiddleware:
    def __init__(self, app, client):
        self.app = app
        self.client = client

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and self.client is not None:
            scope = dict(scope)
            scope["client"] = self.client
        await self.app(scope, receive, send)


def make_test_client(app, client=SUPERVISOR_PROXY):
    try:
        return TestClient(app, client=client)
    except TypeError:
        wrapped = _ClientInjectionMiddleware(app, client)
        return TestClient(wrapped)


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_notifyhub.db")


@pytest.fixture
def storage(temp_db_path):
    return Storage(temp_db_path)


@pytest.fixture
def demo_client():
    return DemoHomeAssistantClient()


@pytest.fixture
def service(storage, demo_client):
    return NotifyHubService(storage=storage, ha_client=demo_client, demo_mode=True)


@pytest.fixture
def settings(temp_db_path):
    return Settings(
        db_path=temp_db_path,
        demo_mode=True,
        allowed_source_ips="127.0.0.1,172.30.32.2",
        supervisor_token="mock_token",
        default_timezone="UTC",
        dedup_window_seconds=120,
    )


@pytest.fixture
def app(settings, service):
    return create_app(settings=settings, service=service)


@pytest.fixture
def client(app):
    return make_test_client(app)
