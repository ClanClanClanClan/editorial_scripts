"""
Manuscript management API endpoints
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...infrastructure.database.engine import get_session
from ...infrastructure.database.models import ManuscriptModel
from ...core.domain.models import ManuscriptStatus

router = APIRouter()


@router.get("/")
async def list_manuscripts(
    journal: Optional[str] = Query(None, description="Filter by journal"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """List manuscripts with optional filters"""
    # Build query
    query = select(ManuscriptModel)
    
    # Apply filters
    if journal:
        query = query.where(ManuscriptModel.journal_code == journal)
    if status:
        query = query.where(ManuscriptModel.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(ManuscriptModel)
    if journal:
        count_query = count_query.where(ManuscriptModel.journal_code == journal)
    if status:
        count_query = count_query.where(ManuscriptModel.status == status)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(ManuscriptModel.submission_date.desc())
    result = await session.execute(query)
    manuscripts = result.scalars().all()
    
    return {
        "total": total,
        "manuscripts": [
            {
                "id": str(m.id),
                "manuscript_id": m.manuscript_id,
                "title": m.title,
                "journal_code": m.journal_code,
                "status": m.status,
                "submission_date": m.submission_date.isoformat() if m.submission_date else None,
                "authors": m.authors,
                "abstract": m.abstract[:200] + "..." if m.abstract and len(m.abstract) > 200 else m.abstract
            }
            for m in manuscripts
        ],
        "skip": skip,
        "limit": limit
    }


@router.get("/{manuscript_id}")
async def get_manuscript(
    manuscript_id: str,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get manuscript details by ID"""
    # Try to find by UUID first
    try:
        uuid_id = UUID(manuscript_id)
        query = select(ManuscriptModel).where(ManuscriptModel.id == uuid_id)
    except ValueError:
        # Not a UUID, try manuscript_id field
        query = select(ManuscriptModel).where(ManuscriptModel.manuscript_id == manuscript_id)
    
    result = await session.execute(query)
    manuscript = result.scalar_one_or_none()
    
    if not manuscript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manuscript {manuscript_id} not found"
        )
    
    return {
        "id": str(manuscript.id),
        "manuscript_id": manuscript.manuscript_id,
        "title": manuscript.title,
        "journal_code": manuscript.journal_code,
        "status": manuscript.status,
        "submission_date": manuscript.submission_date.isoformat() if manuscript.submission_date else None,
        "authors": manuscript.authors,
        "abstract": manuscript.abstract,
        "keywords": manuscript.keywords,
        "referee_count": manuscript.referee_count,
        "review_deadline": manuscript.review_deadline.isoformat() if manuscript.review_deadline else None,
        "metadata": manuscript.metadata,
        "created_at": manuscript.created_at.isoformat() if manuscript.created_at else None,
        "updated_at": manuscript.updated_at.isoformat() if manuscript.updated_at else None
    }


@router.post("/{manuscript_id}/analyze")
async def analyze_manuscript(
    manuscript_id: str,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Analyze manuscript for desk rejection and referee recommendations"""
    # First get the manuscript
    try:
        uuid_id = UUID(manuscript_id)
        query = select(ManuscriptModel).where(ManuscriptModel.id == uuid_id)
    except ValueError:
        query = select(ManuscriptModel).where(ManuscriptModel.manuscript_id == manuscript_id)
    
    result = await session.execute(query)
    manuscript = result.scalar_one_or_none()
    
    if not manuscript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manuscript {manuscript_id} not found"
        )
    
    # Import AI services
    from ...ai.services import create_ai_orchestrator
    from ...infrastructure.config import settings
    
    # Check if AI is configured
    if not settings.openai.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured. Please set OPENAI_API_KEY."
        )
    
    try:
        # Create AI orchestrator
        orchestrator = create_ai_orchestrator(
            openai_api_key=settings.openai.api_key,
            cache_enabled=True
        )
        
        # Perform comprehensive analysis
        analysis_result = await orchestrator.analyze_manuscript_comprehensive(
            manuscript_id=manuscript.manuscript_id,
            journal_code=manuscript.journal_code,
            title=manuscript.title,
            abstract=manuscript.abstract,
            pdf_path=None  # Would need PDF path from metadata
        )
        
        return {
            "manuscript_id": manuscript.manuscript_id,
            "analysis": {
                "recommendation": analysis_result.desk_rejection_analysis.recommendation.value,
                "confidence": analysis_result.desk_rejection_analysis.confidence,
                "quality_score": analysis_result.metadata.overall_quality_score(),
                "reasons": analysis_result.desk_rejection_analysis.rejection_reasons,
                "quality_issues": [
                    {
                        "type": issue.issue_type.value,
                        "description": issue.description,
                        "severity": issue.severity
                    }
                    for issue in analysis_result.desk_rejection_analysis.quality_issues
                ],
                "suggested_referees": [
                    {
                        "name": ref.referee_name,
                        "expertise_match": ref.expertise_match,
                        "overall_score": ref.overall_score,
                        "rationale": ref.rationale
                    }
                    for ref in analysis_result.get_top_referees(5)
                ]
            },
            "processing_time": analysis_result.processing_time_seconds,
            "timestamp": analysis_result.analysis_timestamp.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )