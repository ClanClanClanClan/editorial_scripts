import asyncio
import os

import pytest
from httpx import AsyncClient

try:
    from httpx import ASGITransport
except Exception:  # Older httpx fallback
    ASGITransport = None

from src.ecc.main import app


@pytest.mark.asyncio
async def test_health_endpoint_starts_without_db():
    # Ensure no DATABASE_URL is set to avoid connecting in CI
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://invalid:invalid@localhost:6543/invalid_db"
    )

    transport = ASGITransport(app=app) if ASGITransport else None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data and "checks" in data


@pytest.mark.asyncio
async def test_journals_list():
    transport = ASGITransport(app=app) if ASGITransport else None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/journals/")
        assert resp.status_code == 200
        data = resp.json()
        assert "journals" in data and isinstance(data["journals"], list)
        fs = next((j for j in data["journals"] if j["id"] == "FS"), None)
        assert fs is not None
