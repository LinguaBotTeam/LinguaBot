"""Общие настройки тестов: отдельная база и клиент приложения."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_linguabot.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes!")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from linguabot.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
