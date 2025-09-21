import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.ecc.adapters.storage.repository import ManuscriptRepository
from src.ecc.core.domain.models import Author, DocumentType, File, Manuscript, ManuscriptStatus
from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_DB_URL"), reason="Integration DB not configured")
async def test_upsert_idempotency_authors_files():
    db_url = os.getenv("TEST_DB_URL")
    await initialize_database(db_url)
    dbm = await get_database_manager()

    ms = Manuscript(
        journal_id="TEST",
        external_id="TEST-2025-0002",
        title="Upsert Idempotency",
        current_status=ManuscriptStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
    )
    ms.authors.append(Author(name="Alice", email="alice@example.org"))
    # Fake file metadata (no real file read needed for repo layer)
    ms.files.append(
        File(
            manuscript_id=ms.id,
            document_type=DocumentType.MANUSCRIPT,
            filename="paper.pdf",
            mime_type="application/pdf",
            size_bytes=123,
            storage_path=str(Path("/tmp/paper.pdf")),
            checksum="deadbeef",
        )
    )

    async with dbm.get_session() as session:
        repo = ManuscriptRepository(session)
        await repo.save_full(ms)

    # Save the same snapshot again
    async with dbm.get_session() as session:
        repo = ManuscriptRepository(session)
        await repo.save_full(ms)

    # Verify counts are stable (no duplicates after two saves)
    async with dbm.get_session() as session:
        from sqlalchemy import func, select

        from src.ecc.infrastructure.database.models import AuthorModel, FileModel, ManuscriptModel

        res = await session.execute(
            select(ManuscriptModel).where(
                ManuscriptModel.journal_id == "TEST",
                ManuscriptModel.external_id == "TEST-2025-0002",
            )
        )
        row = res.scalar_one_or_none()
        assert row is not None
        ms_id = row.id

        a_count = (
            await session.execute(
                select(func.count())
                .select_from(AuthorModel)
                .where(AuthorModel.manuscript_id == ms_id)
            )
        ).scalar()
        f_count = (
            await session.execute(
                select(func.count()).select_from(FileModel).where(FileModel.manuscript_id == ms_id)
            )
        ).scalar()
        assert int(a_count or 0) == 1
        assert int(f_count or 0) == 1
