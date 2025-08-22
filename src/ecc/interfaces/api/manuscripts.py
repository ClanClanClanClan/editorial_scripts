"""Manuscript API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.ecc.core.domain.models import ManuscriptStatus
from src.ecc.infrastructure.database.connection import get_database_manager

router = APIRouter()


class ManuscriptResponse(BaseModel):
    """Manuscript response model."""
    
    id: UUID
    journal_id: str
    external_id: str
    title: str
    abstract: Optional[str] = None
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
    
    manuscripts: List[ManuscriptResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ManuscriptSyncRequest(BaseModel):
    """Request to sync manuscripts from a journal."""
    
    journal_id: str = Field(..., description="Journal identifier (e.g., 'MF', 'MOR')")
    categories: Optional[List[str]] = Field(None, description="Specific categories to sync")
    force_refresh: bool = Field(False, description="Force refresh even if recently synced")


class SyncStatusResponse(BaseModel):
    """Sync operation status."""
    
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    journal_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    manuscripts_found: int = 0
    manuscripts_processed: int = 0
    errors: List[str] = []


async def get_db_session():
    """Dependency to get database session."""
    db_manager = await get_database_manager()
    async with db_manager.get_session() as session:
        yield session


@router.get("/", response_model=ManuscriptListResponse)
async def list_manuscripts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    journal_id: Optional[str] = Query(None, description="Filter by journal"),
    status: Optional[ManuscriptStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and abstract"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List manuscripts with pagination and filtering.
    
    - **page**: Page number (1-based)
    - **page_size**: Number of items per page
    - **journal_id**: Filter by specific journal (e.g., 'MF', 'MOR')
    - **status**: Filter by manuscript status
    - **search**: Search text in title and abstract
    """
    try:
        # TODO: Implement actual database queries using SQLAlchemy
        # This is a placeholder implementation
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Build query based on filters
        # query = select(ManuscriptModel)
        # if journal_id:
        #     query = query.where(ManuscriptModel.journal_id == journal_id)
        # if status:
        #     query = query.where(ManuscriptModel.current_status == status)
        # if search:
        #     search_term = f"%{search}%"
        #     query = query.where(
        #         or_(
        #             ManuscriptModel.title.ilike(search_term),
        #             ManuscriptModel.abstract.ilike(search_term)
        #         )
        #     )
        
        # For now, return empty response
        manuscripts = []
        total = 0
        
        return ManuscriptListResponse(
            manuscripts=manuscripts,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_prev=page > 1,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list manuscripts: {str(e)}")


@router.get("/{manuscript_id}", response_model=ManuscriptResponse)
async def get_manuscript(
    manuscript_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific manuscript by ID.
    
    - **manuscript_id**: UUID of the manuscript
    """
    try:
        # TODO: Implement database lookup
        # result = await db.execute(
        #     select(ManuscriptModel).where(ManuscriptModel.id == manuscript_id)
        # )
        # manuscript = result.scalar_one_or_none()
        
        # if not manuscript:
        #     raise HTTPException(status_code=404, detail="Manuscript not found")
        
        # return ManuscriptResponse.from_orm(manuscript)
        
        # Placeholder
        raise HTTPException(status_code=404, detail="Manuscript not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get manuscript: {str(e)}")


@router.post("/sync", response_model=SyncStatusResponse)
async def sync_manuscripts(
    request: ManuscriptSyncRequest,
    db: AsyncSession = Depends(get_db_session)
):
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
                detail=f"Unsupported journal: {request.journal_id}. Supported: {supported_journals}"
            )
        
        # TODO: Start async sync task
        # task_id = await start_sync_task(request.journal_id, request.categories, request.force_refresh)
        
        task_id = f"sync_{request.journal_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return SyncStatusResponse(
            task_id=task_id,
            status="pending",
            journal_id=request.journal_id,
            started_at=datetime.now(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")


@router.get("/sync/{task_id}", response_model=SyncStatusResponse)
async def get_sync_status(task_id: str):
    """
    Get the status of a sync operation.
    
    - **task_id**: Task ID returned from the sync endpoint
    """
    try:
        # TODO: Check actual task status from task queue/database
        # status = await get_task_status(task_id)
        
        # Placeholder response
        return SyncStatusResponse(
            task_id=task_id,
            status="completed",
            journal_id="MF",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            manuscripts_found=5,
            manuscripts_processed=5,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.delete("/{manuscript_id}")
async def delete_manuscript(
    manuscript_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
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
        raise HTTPException(status_code=500, detail=f"Failed to delete manuscript: {str(e)}")


@router.get("/journals/{journal_id}/stats")
async def get_journal_stats(
    journal_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get statistics for a specific journal.
    
    - **journal_id**: Journal identifier (e.g., 'MF', 'MOR')
    """
    try:
        # TODO: Implement actual statistics queries
        # stats = await calculate_journal_stats(journal_id, db)
        
        # Placeholder stats
        stats = {
            "journal_id": journal_id,
            "total_manuscripts": 0,
            "by_status": {
                "submitted": 0,
                "under_review": 0,
                "awaiting_decision": 0,
                "accepted": 0,
                "rejected": 0,
            },
            "avg_review_time_days": 0,
            "last_sync": None,
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get journal stats: {str(e)}")


@router.post("/{manuscript_id}/refresh")
async def refresh_manuscript(
    manuscript_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
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
        raise HTTPException(status_code=500, detail=f"Failed to refresh manuscript: {str(e)}")