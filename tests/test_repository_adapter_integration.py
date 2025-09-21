import asyncio
import os
from datetime import UTC, datetime

import pytest

from src.ecc.adapters.storage.repository import ManuscriptRepository
from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database


class _StubPage:
    def __init__(self, html: str):
        self._html = html

    async def content(self) -> str:
        return self._html


def _read_fixture(path: str) -> str:
    from pathlib import Path

    return (Path("tests/fixtures") / path).read_text()


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DB_URL"), reason="Integration DB not configured")
async def test_adapter_parsed_manuscript_persist_roundtrip(monkeypatch):
    db_url = os.getenv("TEST_DB_URL")
    await initialize_database(db_url)
    dbm = await get_database_manager()

    # Use SICON adapter with stubbed details page
    from src.ecc.adapters.journals.sicon import SICONAdapter

    adapter = SICONAdapter(headless=True)
    adapter.page = _StubPage(_read_fixture("siam_details_simple.html"))
    ms = await adapter.extract_manuscript_details("SICON-2025-0123")
    ms.title = "Control with Constraints"
    ms.submission_date = datetime.now(UTC)

    async with dbm.get_session() as session:
        repo = ManuscriptRepository(session)
        await repo.save_full(ms)

    # Verify saved
    async with dbm.get_session() as session:
        from sqlalchemy import select

        from src.ecc.infrastructure.database.models import AuthorModel, FileModel, ManuscriptModel

        row = (
            await session.execute(
                select(ManuscriptModel).where(ManuscriptModel.external_id == "SICON-2025-0123")
            )
        ).scalar_one_or_none()
        assert row is not None
        ms_id = row.id
        a_count = (
            (await session.execute(select(AuthorModel).where(AuthorModel.manuscript_id == ms_id)))
            .scalars()
            .all()
        )
        f_count = (
            (await session.execute(select(FileModel).where(FileModel.manuscript_id == ms_id)))
            .scalars()
            .all()
        )
        assert len(a_count) == 2
        assert len(f_count) >= 1
