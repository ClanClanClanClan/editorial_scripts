import pytest
from httpx import AsyncClient

try:
    from httpx import ASGITransport
except Exception:
    ASGITransport = None
from src.ecc.main import app


@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app) if ASGITransport else None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        # Check a few headers
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
