"""Journal management API endpoints."""

from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ecc.infrastructure.database.connection import get_database_manager
from src.ecc.infrastructure.database.models import (
    AuditEventModel,
    ManuscriptModel,
    RefereeModel,
)

router = APIRouter()


class JournalInfo(BaseModel):
    """Journal information model."""

    id: str = Field(..., description="Journal identifier (e.g., 'MF', 'MOR')")
    name: str = Field(..., description="Full journal name")
    platform: str = Field(..., description="Platform type (ScholarOne, SIAM, etc.)")
    url: str = Field(..., description="Journal URL")
    supported: bool = Field(..., description="Whether extraction is supported")
    last_sync: str | None = Field(None, description="Last successful sync timestamp")
    manuscript_count: int = Field(0, description="Total manuscripts in database")


class JournalListResponse(BaseModel):
    """Response model for journal list."""

    journals: list[JournalInfo]
    total_supported: int
    total_journals: int


class JournalTestRequest(BaseModel):
    """Request to test journal connection."""

    journal_id: str = Field(..., description="Journal identifier")
    test_auth: bool = Field(True, description="Test authentication")
    test_categories: bool = Field(True, description="Test category fetching")


class JournalTestResponse(BaseModel):
    """Response from journal connection test."""

    journal_id: str
    success: bool
    tests_run: list[str]
    results: dict[str, bool]
    errors: list[str]
    duration_seconds: float


# Journal registry - In production, this would come from database/config
SUPPORTED_JOURNALS = {
    "MF": JournalInfo(
        id="MF",
        name="Mathematical Finance",
        platform="ScholarOne",
        url="https://mc.manuscriptcentral.com/mafi",
        supported=True,
        last_sync=None,
        manuscript_count=0,
    ),
    "MOR": JournalInfo(
        id="MOR",
        name="Mathematics of Operations Research",
        platform="ScholarOne",
        url="https://mc.manuscriptcentral.com/mor",
        supported=True,
        last_sync=None,
        manuscript_count=0,
    ),
    "SICON": JournalInfo(
        id="SICON",
        name="SIAM Journal on Control and Optimization",
        platform="SIAM",
        url="https://www.siam.org/journals/sicon",
        supported=False,  # Not implemented yet
        last_sync=None,
        manuscript_count=0,
    ),
    "SIFIN": JournalInfo(
        id="SIFIN",
        name="SIAM Journal on Financial Mathematics",
        platform="SIAM",
        url="https://www.siam.org/journals/sifin",
        supported=False,  # Not implemented yet
        last_sync=None,
        manuscript_count=0,
    ),
    "JOTA": JournalInfo(
        id="JOTA",
        name="Journal of Optimization Theory and Applications",
        platform="Springer",
        url="https://www.springer.com/journal/10957",
        supported=False,  # Not implemented yet
        last_sync=None,
        manuscript_count=0,
    ),
    "MAFE": JournalInfo(
        id="MAFE",
        name="Mathematical Finance and Economics",
        platform="Springer",
        url="https://www.springer.com/journal/11579",
        supported=False,  # Not implemented yet
        last_sync=None,
        manuscript_count=0,
    ),
    "FS": JournalInfo(
        id="FS",
        name="Finance and Stochastics",
        platform="Email",
        url="https://www.springer.com/journal/780",
        supported=True,
        last_sync=None,
        manuscript_count=0,
    ),
    "NACO": JournalInfo(
        id="NACO",
        name="Numerical Algorithms",
        platform="Unknown",
        url="https://www.springer.com/journal/11075",
        supported=False,  # Not implemented yet
        last_sync=None,
        manuscript_count=0,
    ),
}


@router.get("/", response_model=JournalListResponse)
async def list_journals() -> JournalListResponse:
    """
    List all supported journals.

    Returns information about all journals that the system knows about,
    including their support status and basic metadata.
    """
    # Compute live manuscript_count and last_sync from DB
    journals_cfg = list(SUPPORTED_JOURNALS.values())
    try:
        db_manager = await get_database_manager()
        async with db_manager.get_session() as db:
            enriched: list[JournalInfo] = []
            for j in journals_cfg:
                # Count manuscripts
                total_q = await db.execute(
                    select(func.count())
                    .select_from(ManuscriptModel)
                    .where(ManuscriptModel.journal_id == j.id)
                )
                total = int(total_q.scalar() or 0)
                # Last sync = max(updated_at)
                last_q = await db.execute(
                    select(func.max(ManuscriptModel.updated_at)).where(
                        ManuscriptModel.journal_id == j.id
                    )
                )
                last = last_q.scalar()
                enriched.append(
                    JournalInfo(
                        id=j.id,
                        name=j.name,
                        platform=j.platform,
                        url=j.url,
                        supported=j.supported,
                        manuscript_count=total,
                        last_sync=(last.isoformat() if last else None),
                    )
                )
            supported_count = sum(1 for j in enriched if j.supported)
            return JournalListResponse(
                journals=enriched,
                total_supported=supported_count,
                total_journals=len(enriched),
            )
    except Exception:
        # Fallback to static if DB unavailable
        journals = journals_cfg
        supported_count = sum(1 for j in journals if j.supported)
        return JournalListResponse(
            journals=journals,
            total_supported=supported_count,
            total_journals=len(journals),
        )


@router.get("/{journal_id}", response_model=JournalInfo)
async def get_journal(journal_id: str) -> JournalInfo:
    """
    Get information about a specific journal.

    - **journal_id**: Journal identifier (e.g., 'MF', 'MOR')
    """
    journal_id = journal_id.upper()

    if journal_id not in SUPPORTED_JOURNALS:
        raise HTTPException(
            status_code=404,
            detail=f"Journal '{journal_id}' not found. Supported journals: {list(SUPPORTED_JOURNALS.keys())}",
        )

    return SUPPORTED_JOURNALS[journal_id]


@router.post("/{journal_id}/test", response_model=JournalTestResponse)
async def test_journal_connection(
    journal_id: str, request: JournalTestRequest
) -> JournalTestResponse:
    """
    Test connection to a journal platform.

    This endpoint tests the ability to connect to and extract data
    from the specified journal platform.

    - **journal_id**: Journal identifier
    - **test_auth**: Whether to test authentication
    - **test_categories**: Whether to test category fetching
    """
    import time

    journal_id = journal_id.upper()

    if journal_id not in SUPPORTED_JOURNALS:
        raise HTTPException(status_code=404, detail=f"Journal '{journal_id}' not found")

    journal = SUPPORTED_JOURNALS[journal_id]

    if not journal.supported:
        raise HTTPException(status_code=400, detail=f"Journal '{journal_id}' is not yet supported")

    start_time = time.time()
    tests_run = []
    results = {}
    errors = []

    try:
        # Test adapter creation
        tests_run.append("adapter_creation")

        if journal_id == "MF":
            from src.ecc.adapters.journals.factory import get_adapter

            async with get_adapter("MF", headless=True) as adapter:
                results["adapter_creation"] = True

                # Test authentication if requested
                if request.test_auth:
                    tests_run.append("authentication")
                    try:
                        auth_result = await adapter.authenticate()
                        results["authentication"] = auth_result
                        if not auth_result:
                            errors.append("Authentication failed - check credentials")
                    except Exception as e:
                        results["authentication"] = False
                        errors.append(f"Authentication error: {str(e)}")

                # Test category fetching if requested
                if request.test_categories:
                    tests_run.append("category_fetching")
                    try:
                        categories = await adapter.get_default_categories()
                        results["category_fetching"] = len(categories) > 0
                        if not categories:
                            errors.append("No categories found")
                    except Exception as e:
                        results["category_fetching"] = False
                        errors.append(f"Category fetching error: {str(e)}")

        elif journal_id == "MOR":
            from src.ecc.adapters.journals.factory import get_adapter

            async with get_adapter("MOR", headless=True) as adapter:
                results["adapter_creation"] = True
                if request.test_auth:
                    tests_run.append("authentication")
                    try:
                        auth_result = await adapter.authenticate()
                        results["authentication"] = auth_result
                        if not auth_result:
                            errors.append("Authentication failed - check credentials")
                    except Exception as e:
                        results["authentication"] = False
                        errors.append(f"Authentication error: {str(e)}")
                if request.test_categories:
                    tests_run.append("category_fetching")
                    try:
                        categories = await adapter.get_default_categories()
                        results["category_fetching"] = len(categories) > 0
                        if not categories:
                            errors.append("No categories found")
                    except Exception as e:
                        results["category_fetching"] = False
                        errors.append(f"Category fetching error: {str(e)}")

        else:
            results["adapter_creation"] = False
            errors.append(f"No adapter implemented for {journal_id}")

    except Exception as e:
        results["adapter_creation"] = False
        errors.append(f"Adapter creation failed: {str(e)}")

    duration = time.time() - start_time
    success = all(results.values()) and len(errors) == 0

    return JournalTestResponse(
        journal_id=journal_id,
        success=success,
        tests_run=tests_run,
        results=results,
        errors=errors,
        duration_seconds=round(duration, 2),
    )


@router.get("/{journal_id}/categories")
async def get_journal_categories(journal_id: str) -> dict[str, Any]:
    """
    Get available manuscript categories for a journal.

    - **journal_id**: Journal identifier
    """
    journal_id = journal_id.upper()

    if journal_id not in SUPPORTED_JOURNALS:
        raise HTTPException(status_code=404, detail=f"Journal '{journal_id}' not found")

    journal = SUPPORTED_JOURNALS[journal_id]

    if not journal.supported:
        raise HTTPException(status_code=400, detail=f"Journal '{journal_id}' is not yet supported")

    try:
        if journal_id == "MF":
            from src.ecc.adapters.journals.mf import MFAdapter

            async with MFAdapter(headless=True) as adapter:
                categories = await adapter.get_default_categories()
                return {
                    "journal_id": journal_id,
                    "categories": categories,
                    "count": len(categories),
                }

        else:
            return {
                "journal_id": journal_id,
                "categories": [],
                "count": 0,
                "error": "Adapter not implemented",
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get categories for {journal_id}: {str(e)}"
        ) from e


@router.get("/{journal_id}/health")
async def check_journal_health(journal_id: str):
    """
    Quick health check for a journal platform.

    This is a lightweight check that verifies the journal
    platform is accessible.

    - **journal_id**: Journal identifier
    """
    journal_id = journal_id.upper()

    if journal_id not in SUPPORTED_JOURNALS:
        raise HTTPException(status_code=404, detail=f"Journal '{journal_id}' not found")

    journal = SUPPORTED_JOURNALS[journal_id]

    try:
        # TODO: Implement actual health check (ping URL, check response)
        # For now, just return basic info

        return {
            "journal_id": journal_id,
            "name": journal.name,
            "platform": journal.platform,
            "url": journal.url,
            "supported": journal.supported,
            "status": "healthy" if journal.supported else "not_supported",
            "timestamp": "2025-08-22T23:00:00Z",  # TODO: Use actual timestamp
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health check failed for {journal_id}: {str(e)}"
        ) from e


@router.get("/{journal_id}/stats")
async def journal_stats(
    journal_id: str,
    days: int = Query(
        90, ge=1, le=3650, description="Time window in days for recent decision stats"
    ),
    db: AsyncSession = Depends(lambda: get_database_manager().__await__()),
) -> dict[str, Any]:
    """Aggregate statistics for a journal across manuscripts/referees/audit events."""

    def _mask_email(email: str | None) -> str | None:
        if not email:
            return email
        try:
            name, domain = email.split("@", 1)
            if not name:
                return f"*@{domain}"
            return f"{name[0]}***@{domain}"
        except Exception:
            return email

    try:
        # Total manuscripts
        total_q = await db.execute(
            select(func.count())
            .select_from(ManuscriptModel)
            .where(ManuscriptModel.journal_id == journal_id)
        )
        total = int(total_q.scalar() or 0)

        # By status
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
        top_overdue: list[dict] = []
        from datetime import datetime

        now = datetime.now(UTC)
        for r in refs:
            hp = r.historical_performance or {}
            if hp.get("overdue"):
                overdue += 1
            rd = hp.get("response_days")
            if isinstance(rd, int):
                resp_days_sum += rd
                resp_days_count += 1
            # Compute days overdue if applicable
            if r.report_due_date and r.report_submitted_date is None:
                try:
                    # Ensure tz-aware comparison
                    due = r.report_due_date
                    if due.tzinfo is None:
                        due = due.replace(tzinfo=UTC)
                    if due < now:
                        days_over = (now - due).days
                        top_overdue.append(
                            {
                                "name": r.name,
                                "email": _mask_email(r.email),
                                "days_overdue": int(days_over),
                            }
                        )
                except Exception:
                    pass
        avg_response_days = (resp_days_sum / resp_days_count) if resp_days_count else 0

        # Audit events & recent decision counts within window
        from datetime import timedelta

        cutoff = now - timedelta(days=days)
        events_count = (
            await db.execute(
                select(func.count())
                .select_from(AuditEventModel)
                .join(ManuscriptModel, AuditEventModel.manuscript_id == ManuscriptModel.id)
                .where(ManuscriptModel.journal_id == journal_id)
            )
        ).scalar() or 0
        # Pull recent events
        recent_events = (
            (
                await db.execute(
                    select(AuditEventModel)
                    .join(ManuscriptModel, AuditEventModel.manuscript_id == ManuscriptModel.id)
                    .where(ManuscriptModel.journal_id == journal_id)
                    .where(AuditEventModel.timestamp >= cutoff)
                    .order_by(AuditEventModel.timestamp.desc())
                )
            )
            .scalars()
            .all()
        )

        decisions = {
            "accept": 0,
            "reject": 0,
            "revise": 0,
            "desk_reject": 0,
            "major_revise": 0,
            "minor_revise": 0,
        }
        for ev in recent_events:
            try:
                ch = ev.changes or {}
                ev_text = " ".join(
                    [
                        str(ch.get("event", "")),
                        str(ch.get("letter", {}).get("raw", "")),
                    ]
                ).lower()
                if (
                    "decision" in ev_text
                    or "revise" in ev_text
                    or "accept" in ev_text
                    or "reject" in ev_text
                ):
                    if "desk" in ev_text and "reject" in ev_text:
                        decisions["desk_reject"] += 1
                    elif "accept" in ev_text or "accepted" in ev_text:
                        decisions["accept"] += 1
                    elif "reject" in ev_text or "rejected" in ev_text:
                        decisions["reject"] += 1
                    elif "revise" in ev_text or "revision" in ev_text:
                        decisions["revise"] += 1
                        if "major" in ev_text:
                            decisions["major_revise"] += 1
                        if "minor" in ev_text:
                            decisions["minor_revise"] += 1
            except Exception:
                continue

        # Sort top overdue by days
        top_overdue_sorted = sorted(top_overdue, key=lambda x: x["days_overdue"], reverse=True)[:10]

        return {
            "journal_id": journal_id,
            "total_manuscripts": total,
            "by_status": by_status,
            "referees": {
                "total": total_referees,
                "overdue": overdue,
                "avg_response_days": round(avg_response_days, 2),
                "top_overdue": top_overdue_sorted,
            },
            "audit": {
                "events": int(events_count),
                "recent_decisions": {"window_days": days, **decisions},
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute stats: {str(e)}") from e
