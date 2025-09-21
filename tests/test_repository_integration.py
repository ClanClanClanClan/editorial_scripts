import os
from datetime import datetime

import pytest

from src.ecc.adapters.storage.repository import ManuscriptRepository
from src.ecc.core.domain.models import Manuscript, ManuscriptStatus
from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DB_URL"), reason="Integration DB not configured")
async def test_save_full_roundtrip():
    db_url = os.getenv("TEST_DB_URL")
    await initialize_database(db_url)
    dbm = await get_database_manager()
    async with dbm.get_session() as session:
        repo = ManuscriptRepository(session)
        ms = Manuscript(
            journal_id="TEST",
            external_id="TEST-2025-0001",
            title="Test Manuscript",
            current_status=ManuscriptStatus.SUBMITTED,
            submission_date=datetime.utcnow(),
        )
        await repo.save_full(ms)

    async with dbm.get_session() as session:
        # Verify manuscript exists
        from sqlalchemy import select

        from src.ecc.infrastructure.database.models import ManuscriptModel

        res = await session.execute(
            select(ManuscriptModel).where(ManuscriptModel.journal_id == "TEST")
        )
        row = res.scalar_one_or_none()
        assert row is not None
