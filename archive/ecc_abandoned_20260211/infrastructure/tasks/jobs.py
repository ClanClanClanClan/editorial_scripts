"""ECC background jobs for journal sync and enrichment."""

import asyncio
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from src.ecc.infrastructure.tasks.celery_app import celery_app


async def _run_sync(
    journal_id: str, enrich: bool = False, headless: bool = True, max_manuscripts: int = 0
) -> dict[str, Any]:
    from src.ecc.adapters.storage.repository import ManuscriptRepository
    from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database

    # Initialize DB
    try:
        from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

        host = get_secret_with_vault("DB_HOST")
        name = get_secret_with_vault("DB_NAME")
        user = get_secret_with_vault("DB_USER")
        password = get_secret_with_vault("DB_PASSWORD")
        port = get_secret_with_vault("DB_PORT") or "5433"
        if all([host, name, user, password]):
            db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
        else:
            db_url = get_secret_with_vault("DATABASE_URL") or os.getenv(
                "DATABASE_URL", "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
            )
    except Exception:
        db_url = os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
        )
    await initialize_database(db_url, echo=False)

    # Select adapter
    adapter = None
    jid = journal_id.upper()
    if jid == "MF":
        from src.ecc.adapters.journals.mf import MFAdapter

        adapter = MFAdapter(headless=headless)
    elif jid == "MOR":
        from src.ecc.adapters.journals.mor import MORAdapter

        adapter = MORAdapter(headless=headless)
    elif jid == "FS":
        from src.ecc.adapters.journals.fs import FSAdapter

        adapter = FSAdapter()
    else:
        raise ValueError(f"Unsupported journal id: {journal_id}")

    processed = 0
    total = 0
    errors = []
    async with adapter:
        auth_ok = await adapter.authenticate()
        if not auth_ok:
            return {"status": "failed", "error": "authentication_failed"}

        fetched = await adapter.fetch_all_manuscripts()
        manuscripts = fetched if not max_manuscripts else fetched[:max_manuscripts]
        total = len(manuscripts)

        dbm = await get_database_manager()
        async with dbm.get_session() as session:
            repo = ManuscriptRepository(session)
            for ms in manuscripts:
                try:
                    # ScholarOne adapters can extract details
                    if hasattr(adapter, "extract_manuscript_details"):
                        ms = await adapter.extract_manuscript_details(ms.external_id)
                    if enrich and hasattr(adapter, "enrich_people_with_orcid"):
                        await adapter.enrich_people_with_orcid(ms)
                    await repo.save_full(ms)
                    # Schedule uploads for files
                    from sqlalchemy import select

                    from src.ecc.infrastructure.database.models import FileModel, ManuscriptModel

                    ms_row = (
                        await session.execute(
                            select(ManuscriptModel).where(
                                ManuscriptModel.journal_id == ms.journal_id,
                                ManuscriptModel.external_id == ms.external_id,
                            )
                        )
                    ).scalar_one_or_none()
                    if ms_row:
                        files = (
                            (
                                await session.execute(
                                    select(FileModel).where(FileModel.manuscript_id == ms_row.id)
                                )
                            )
                            .scalars()
                            .all()
                        )
                        for f in files:
                            sp = f.storage_path or ""
                            if (not f.s3_url) and sp and not sp.startswith("quarantine://"):
                                upload_file_to_s3.delay(str(f.id))
                    processed += 1
                except Exception as e:
                    errors.append(str(e))
                    continue

    return {
        "status": "completed",
        "journal_id": journal_id,
        "processed": processed,
        "total": total,
        "errors": errors,
        "finished_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(bind=True, name="ecc.sync_journal")
def sync_journal(
    self, journal_id: str, enrich: bool = False, headless: bool = True, max_manuscripts: int = 0
):
    """Celery task to sync a journal. Returns a summary dict."""
    try:
        return asyncio.run(
            _run_sync(journal_id, enrich=enrich, headless=headless, max_manuscripts=max_manuscripts)
        )
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True, name="ecc.reprocess_files")
def reprocess_files(self, journal_id: str | None = None, only_missing: bool = True):
    """Scan & upload existing files; optionally filter by journal and missing s3_url."""
    try:
        import asyncio

        return asyncio.run(_reprocess_files_async(journal_id, only_missing))
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def _reprocess_files_async(journal_id: str | None, only_missing: bool):
    from sqlalchemy import select

    from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database
    from src.ecc.infrastructure.database.models import FileModel, ManuscriptModel
    from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

    db_url = get_secret_with_vault("DATABASE_URL") or os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
    )
    await initialize_database(db_url)
    dbm = await get_database_manager()
    async with dbm.get_session() as session:
        q = select(FileModel)
        if only_missing:
            q = q.where(FileModel.s3_url == None)  # noqa: E711
        if journal_id:
            q = q.join(ManuscriptModel, FileModel.manuscript_id == ManuscriptModel.id).where(
                ManuscriptModel.journal_id == journal_id
            )
        files = (await session.execute(q)).scalars().all()
        count = 0
        for f in files:
            upload_file_to_s3.delay(str(f.id))
            count += 1
        return {"status": "queued", "files": count}


def _create_s3_client():
    try:
        import boto3  # type: ignore
    except Exception:
        return None
    from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

    key = get_secret_with_vault("AWS_ACCESS_KEY_ID")
    secret = get_secret_with_vault("AWS_SECRET_ACCESS_KEY")
    region = get_secret_with_vault("AWS_S3_REGION") or "us-east-1"
    endpoint = get_secret_with_vault("AWS_S3_ENDPOINT")
    cfg = {
        "aws_access_key_id": key,
        "aws_secret_access_key": secret,
        "region_name": region,
    }
    if endpoint:
        cfg["endpoint_url"] = endpoint
    return boto3.client("s3", **cfg)


def _scan_with_clamd(path: Path) -> tuple[bool, str]:
    """Scan file with clamd if available. Returns (ok, result)."""
    try:
        import clamd  # type: ignore
    except Exception:
        return True, "not_scanned"
    host = os.getenv("CLAMD_HOST")
    port = int(os.getenv("CLAMD_PORT", "3310"))
    sock = os.getenv("CLAMD_UNIX_SOCKET")
    try:
        cd = (
            clamd.ClamdUnixSocket(sock)
            if sock
            else clamd.ClamdNetworkSocket(host or "127.0.0.1", port)
        )
        res = cd.scan(str(path))
        # res: {'/path': ('OK'|'FOUND', 'malware-name'|None)}
        status, name = res.get(str(path), ("OK", None))
        return status == "OK", name or "OK"
    except Exception:
        return True, "not_scanned"


@celery_app.task(bind=True, name="ecc.upload_file_to_s3")
def upload_file_to_s3(self, file_id: str):
    """Upload a file to S3/MinIO and update DB storage_path to the public URL. Scans before upload."""
    try:
        # Lazy import to avoid async context issues
        import asyncio

        return asyncio.run(_upload_file_to_s3_async(UUID(file_id)))
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def _upload_file_to_s3_async(file_id: UUID):
    from sqlalchemy import select

    from src.ecc.infrastructure.database.connection import get_database_manager, initialize_database
    from src.ecc.infrastructure.database.models import FileModel, ManuscriptModel
    from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

    # Initialize DB
    db_url = get_secret_with_vault("DATABASE_URL") or os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
    )
    await initialize_database(db_url)
    dbm = await get_database_manager()
    async with dbm.get_session() as session:
        f = (
            await session.execute(select(FileModel).where(FileModel.id == file_id))
        ).scalar_one_or_none()
        if not f:
            return {"status": "not_found"}
        local_path = Path(f.storage_path)
        if not local_path.exists():
            return {"status": "no_local_file"}

        # Scan with clamd
        ok, result = _scan_with_clamd(local_path)
        if not ok:
            # Move to quarantine and mark path
            qdir = Path("downloads/quarantine")
            qdir.mkdir(parents=True, exist_ok=True)
            qpath = qdir / local_path.name
            try:
                shutil.move(str(local_path), str(qpath))
            except Exception:
                pass
            f.storage_path = f"quarantine://{qpath}"
            f.scan_status = "quarantined"
            f.scan_result = result
            await session.flush()
            return {"status": "quarantined", "reason": result}

        # Upload to S3
        client = _create_s3_client()
        bucket = get_secret_with_vault("AWS_S3_BUCKET")
        if not client or not bucket:
            return {"status": "skipped", "reason": "s3_not_configured"}

        # Determine key from journal/external_id/filename
        # Need manuscript to build prefix
        m = (
            await session.execute(
                select(ManuscriptModel).where(ManuscriptModel.id == f.manuscript_id)
            )
        ).scalar_one_or_none()
        prefix = os.getenv("ECC_S3_PREFIX", "files")
        key = (
            f"{prefix}/{m.journal_id}/{m.external_id}/{f.filename}"
            if m
            else f"{prefix}/{f.filename}"
        )
        extra = {"ContentType": f.mime_type or "application/octet-stream"}
        try:
            client.upload_file(str(local_path), bucket, key, ExtraArgs=extra)
            endpoint = os.getenv("AWS_S3_PUBLIC_ENDPOINT") or get_secret_with_vault(
                "AWS_S3_PUBLIC_ENDPOINT"
            )
            if endpoint:
                url = f"{endpoint.rstrip('/')}/{bucket}/{key}"
            else:
                region = os.getenv("AWS_S3_REGION", "us-east-1")
                url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
            f.s3_url = url
            f.scan_status = f.scan_status or "clean"
            f.scan_result = f.scan_result or "OK"
            await session.flush()
            return {"status": "uploaded", "url": url}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
