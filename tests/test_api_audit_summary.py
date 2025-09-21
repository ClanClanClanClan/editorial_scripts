import os

import pytest
from httpx import AsyncClient

try:
    from httpx import ASGITransport
except Exception:
    ASGITransport = None

from src.ecc.main import app


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DB_URL"), reason="Integration DB not configured")
async def test_audit_summary_endpoint_smoke():
    transport = ASGITransport(app=app) if ASGITransport else None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Unknown manuscript should 404
        resp = await ac.get("/api/manuscripts/00000000-0000-0000-0000-000000000000/audit-summary")
        assert resp.status_code in (400, 404)
