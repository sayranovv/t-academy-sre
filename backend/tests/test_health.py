import asyncio
from unittest.mock import AsyncMock

import psycopg
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_live_and_status_do_not_require_database(monkeypatch):
    connect = AsyncMock(side_effect=psycopg.OperationalError("unavailable"))
    monkeypatch.setattr(psycopg.AsyncConnection, "connect", connect)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/api/v1/status").json()["service"] == "equipment-api"
    connect.assert_not_called()


def test_ready_uses_real_postgres():
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_ready_returns_503_without_exposing_connection_details(monkeypatch):
    monkeypatch.setattr(
        psycopg.AsyncConnection,
        "connect",
        AsyncMock(side_effect=psycopg.OperationalError("private connection details")),
    )
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_readiness_has_total_deadline(monkeypatch):
    async def stalled_connection(*args, **kwargs):
        await asyncio.Event().wait()

    settings = get_settings().model_copy(update={"readiness_timeout": 0.02})
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr(psycopg.AsyncConnection, "connect", stalled_connection)
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503
