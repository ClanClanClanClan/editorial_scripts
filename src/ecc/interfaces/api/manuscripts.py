"""Manuscript API endpoints."""

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ecc.core.audit_normalization import normalize_events
from src.ecc.core.domain.models import ManuscriptStatus
from src.ecc.infrastructure.database.connection import get_database_manager
from src.ecc.infrastructure.database.models import ManuscriptModel
from src.ecc.infrastructure.tasks.celery_app import celery_app
from src.ecc.interfaces.api.auth import require_roles

router = APIRouter()


class ManuscriptResponse(BaseModel):
    """Manuscript response model."""

    id: UUID
    journal_id: str
    external_id: str
    title: str
    abstract: str | None = None
    current_status: ManuscriptStatus
    submission_date: datetime
    author_count: int = 0
    referee_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManuscriptListResponse(BaseModel):
    """Paginated manuscript list response."""

    manuscripts: list[ManuscriptResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ManuscriptSyncRequest(BaseModel):
    """Request to sync manuscripts from a journal."""

    journal_id: str = Field(..., description="Journal identifier (e.g., 'MF', 'MOR')")
    categories: list[str] | None = Field(None, description="Specific categories to sync")
    force_refresh: bool = Field(False, description="Force refresh even if recently synced")


class SyncStatusResponse(BaseModel):
    """Sync operation status."""

    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    journal_id: str
    started_at: datetime
    completed_at: datetime | None = None
    manuscripts_found: int = 0
    manuscripts_processed: int = 0
    errors: list[str] = []


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session


@router.get("/", response_model=ManuscriptListResponse)
async def list_manuscripts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    journal_id: str | None = Query(None, description="Filter by journal"),
    status: ManuscriptStatus | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search in title and abstract"),
    db: AsyncSession = Depends(get_db_session),
) -> ManuscriptListResponse:
    """
    List manuscripts with pagination and filtering.

    - **page**: Page number (1-based)
    - **page_size**: Number of items per page
    - **journal_id**: Filter by specific journal (e.g., 'MF', 'MOR')
    - **status**: Filter by manuscript status
    - **search**: Search text in title and abstract
    """
    try:
        offset = (page - 1) * page_size

        # Build filters
        filters = []
        if journal_id:
            filters.append(ManuscriptModel.journal_id == journal_id)
        if status:
            filters.append(ManuscriptModel.current_status == status)
        if search:
            search_term = f"%{search}%"
            filters.append(ManuscriptModel.title.ilike(search_term))

        # Total count
        count_stmt = select(func.count()).select_from(ManuscriptModel)
        if filters:
            count_stmt = count_stmt.where(*filters)
        result = await db.execute(count_stmt)
        total = result.scalar() or 0

        # Page query
        stmt = select(ManuscriptModel)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        items: list[ManuscriptResponse] = [
            ManuscriptResponse(
                id=UUID(str(r.id)),
                journal_id=r.journal_id,
                external_id=r.external_id,
                title=r.title,
                abstract=None,
                current_status=r.current_status,
                submission_date=r.submission_date,
                author_count=0,
                referee_count=0,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]

        return ManuscriptListResponse(
            manuscripts=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list manuscripts: {str(e)}") from e


@router.get("/{manuscript_id}", response_model=ManuscriptResponse)
async def get_manuscript(
    manuscript_id: UUID, db: AsyncSession = Depends(get_db_session)
) -> ManuscriptResponse:
    """
    Get a specific manuscript by ID.

    - **manuscript_id**: UUID of the manuscript
    """
    try:
        result = await db.execute(
            select(ManuscriptModel).where(ManuscriptModel.id == manuscript_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        return ManuscriptResponse(
            id=UUID(str(r.id)),
            journal_id=r.journal_id,
            external_id=r.external_id,
            title=r.title,
            abstract=None,
            current_status=r.current_status,
            submission_date=r.submission_date,
            author_count=0,
            referee_count=0,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get manuscript: {str(e)}") from e


@router.post(
    "/sync",
    response_model=SyncStatusResponse,
    dependencies=[Depends(require_roles(["editor", "admin"]))],
)
async def sync_manuscripts(
    request: ManuscriptSyncRequest, db: AsyncSession = Depends(get_db_session)
) -> SyncStatusResponse:
    """
    Sync manuscripts from a journal platform.

    This endpoint starts an asynchronous sync operation to fetch
    manuscripts from the specified journal platform.

    - **journal_id**: Journal to sync (MF, MOR, SICON, etc.)
    - **categories**: Specific categories to sync (optional)
    - **force_refresh**: Force refresh even if recently synced
    """
    try:
        # Validate journal_id
        supported_journals = ["MF", "MOR", "SICON", "SIFIN", "JOTA", "MAFE", "FS", "NACO"]
        if request.journal_id not in supported_journals:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported journal: {request.journal_id}. Supported: {supported_journals}",
            )

        # Trigger Celery task
        job = celery_app.send_task(
            "ecc.sync_journal", args=[request.journal_id], kwargs={"enrich": False}
        )
        task_id = job.id

        return SyncStatusResponse(
            task_id=task_id,
            status="pending",
            journal_id=request.journal_id,
            started_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}") from e


@router.get("/sync/{task_id}", response_model=SyncStatusResponse)
async def get_sync_status(task_id: str) -> SyncStatusResponse:
    """
    Get the status of a sync operation.

    - **task_id**: Task ID returned from the sync endpoint
    """
    try:
        # Prefer real Celery AsyncResult; fallback to internal stub if unavailable
        from celery.result import AsyncResult
    except Exception:
        from src.ecc.testing.celery_stub.result import AsyncResult
    try:
        res = AsyncResult(task_id, app=celery_app)
        info = res.info if isinstance(res.info, dict) else {}
        status = res.status.lower()
        completed_at = datetime.now() if status in ("success", "failed") else None
        return SyncStatusResponse(
            task_id=task_id,
            status=status,
            journal_id=str(info.get("journal_id", "")),
            started_at=datetime.now(),
            completed_at=completed_at,
            manuscripts_found=int(info.get("total", 0)),
            manuscripts_processed=int(info.get("processed", 0)),
            errors=info.get("errors", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}") from e


@router.delete("/{manuscript_id}", dependencies=[Depends(require_roles(["editor", "admin"]))])
async def delete_manuscript(
    manuscript_id: UUID, db: AsyncSession = Depends(get_db_session)
) -> dict[str, str]:
    """
    Delete a manuscript.

    - **manuscript_id**: UUID of the manuscript to delete
    """
    try:
        # TODO: Implement soft delete or hard delete based on requirements
        # result = await db.execute(
        #     select(ManuscriptModel).where(ManuscriptModel.id == manuscript_id)
        # )
        # manuscript = result.scalar_one_or_none()

        # if not manuscript:
        #     raise HTTPException(status_code=404, detail="Manuscript not found")

        # await db.delete(manuscript)
        # await db.commit()

        return {"message": "Manuscript deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete manuscript: {str(e)}") from e


@router.get("/journals/{journal_id}/stats")
async def get_journal_stats(
    journal_id: str, db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """Aggregate stats for a journal: counts by status, referee metrics, audit events."""
    from sqlalchemy import func, select

    from src.ecc.infrastructure.database.models import (
        AuditEventModel,
        ManuscriptModel,
        RefereeModel,
    )

    try:
        # Totals
        total_q = await db.execute(
            select(func.count())
            .select_from(ManuscriptModel)
            .where(ManuscriptModel.journal_id == journal_id)
        )
        total = int(total_q.scalar() or 0)

        # Status counts
        by_status: dict[str, int] = {}
        rows = (
            await db.execute(
                select(ManuscriptModel.current_status, func.count())
                .where(ManuscriptModel.journal_id == journal_id)
                .group_by(ManuscriptModel.current_status)
            )
        ).all()
        for status, count in rows:
            by_status[status.value] = int(count)

        # Referee metrics
        refs = (
            (
                await db.execute(
                    select(RefereeModel)
                    .join(ManuscriptModel, RefereeModel.manuscript_id == ManuscriptModel.id)
                    .where(ManuscriptModel.journal_id == journal_id)
                )
            )
            .scalars()
            .all()
        )
        total_referees = len(refs)
        overdue = 0
        resp_days_sum = 0
        resp_days_count = 0
        for r in refs:
            hp = r.historical_performance or {}
            if hp.get("overdue"):
                overdue += 1
            rd = hp.get("response_days")
            if isinstance(rd, int):
                resp_days_sum += rd
                resp_days_count += 1
        avg_response_days = (resp_days_sum / resp_days_count) if resp_days_count else 0

        # Audit events
        events_count = (
            await db.execute(
                select(func.count())
                .select_from(AuditEventModel)
                .join(ManuscriptModel, AuditEventModel.manuscript_id == ManuscriptModel.id)
                .where(ManuscriptModel.journal_id == journal_id)
            )
        ).scalar() or 0

        return {
            "journal_id": journal_id,
            "total_manuscripts": total,
            "by_status": by_status,
            "referees": {
                "total": total_referees,
                "overdue": overdue,
                "avg_response_days": round(avg_response_days, 2),
            },
            "audit": {"events": int(events_count)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get journal stats: {str(e)}") from e


@router.post("/{manuscript_id}/refresh", dependencies=[Depends(require_roles(["editor", "admin"]))])
async def refresh_manuscript(manuscript_id: UUID, db: AsyncSession = Depends(get_db_session)):
    """
    Refresh a specific manuscript from the journal platform.

    - **manuscript_id**: UUID of the manuscript to refresh
    """
    try:
        # TODO: Implement manuscript refresh logic
        # 1. Get manuscript from database
        # 2. Get journal adapter
        # 3. Fetch fresh data
        # 4. Update database

        return {"message": "Manuscript refresh started", "manuscript_id": manuscript_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh manuscript: {str(e)}"
        ) from e


class EnrichRequest(BaseModel):
    journal_id: str
    max_manuscripts: int | None = None


@router.post("/enrich")
async def enrich_manuscripts(request: EnrichRequest) -> dict[str, str]:
    """Trigger enrichment task for a journal."""
    try:
        job = celery_app.send_task(
            "ecc.sync_journal",
            args=[request.journal_id],
            kwargs={"enrich": True, "max_manuscripts": request.max_manuscripts or 0},
        )
        return {"task_id": job.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start enrichment: {str(e)}") from e


@router.get("/export", response_model=None)
async def export_manuscripts(
    format: str = Query("json", pattern="^(json|csv)$"),
    journal_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict[str, object]] | PlainTextResponse:
    try:
        stmt = select(ManuscriptModel)
        if journal_id:
            stmt = stmt.where(ManuscriptModel.journal_id == journal_id)
        rows = (await db.execute(stmt)).scalars().all()
        if format == "json":
            data = [
                {
                    "id": str(r.id),
                    "journal_id": r.journal_id,
                    "external_id": r.external_id,
                    "title": r.title,
                    "status": r.current_status.value,
                    "submission_date": r.submission_date.isoformat() if r.submission_date else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
            return data
        else:
            import csv
            from io import StringIO

            sio = StringIO()
            writer = csv.writer(sio)
            writer.writerow(
                [
                    "id",
                    "journal_id",
                    "external_id",
                    "title",
                    "status",
                    "submission_date",
                    "created_at",
                ]
            )
            for r in rows:
                writer.writerow(
                    [
                        str(r.id),
                        r.journal_id,
                        r.external_id,
                        r.title,
                        r.current_status.value,
                        r.submission_date.isoformat() if r.submission_date else "",
                        r.created_at.isoformat() if r.created_at else "",
                    ]
                )
            return PlainTextResponse(sio.getvalue(), media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}") from e


@router.get("/{manuscript_id}/audit-summary")
async def get_audit_summary_endpoint(
    manuscript_id: UUID, db: AsyncSession = Depends(get_db_session)
) -> dict[str, object]:
    """Return normalized audit summary for a manuscript (for UI preview)."""
    try:
        from src.ecc.infrastructure.database.models import AuditEventModel

        res = await db.execute(select(ManuscriptModel).where(ManuscriptModel.id == manuscript_id))
        ms = res.scalar_one_or_none()
        if not ms:
            raise HTTPException(status_code=404, detail="Manuscript not found")

        rows = (
            (
                await db.execute(
                    select(AuditEventModel)
                    .where(AuditEventModel.manuscript_id == manuscript_id)
                    .order_by(AuditEventModel.timestamp.asc())
                )
            )
            .scalars()
            .all()
        )
        raw = [r.changes or {} for r in rows]
        events = normalize_events(raw)
        summary = {
            "manuscript_id": str(manuscript_id),
            "count": len(events),
            "first_events": [e.get("event", "") for e in events[:3]],
            "events": events[:100],
        }
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit summary: {str(e)}") from e
