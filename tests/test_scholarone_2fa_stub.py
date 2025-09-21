import asyncio
import os

import pytest


@pytest.mark.asyncio
async def test_twofa_stub_env_short_circuit(monkeypatch):
    from src.ecc.adapters.journals.base import JournalConfig
    from src.ecc.adapters.journals.scholarone import ScholarOneAdapter

    # Set stub code
    monkeypatch.setenv("ECC_GMAIL_2FA_CODE", "123456")
    cfg = JournalConfig(
        journal_id="TEST", name="Test", url="https://example.test", platform="ScholarOne"
    )
    adapter = ScholarOneAdapter(cfg)

    code = await adapter._fetch_2fa_code()
    assert code == "123456"
