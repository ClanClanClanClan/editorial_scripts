"""
API endpoints for journal extraction operations
"""

import logging
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from ...core.domain.models import ExtractionResult
from ...infrastructure.database.engine import get_session
from ...infrastructure.cache.redis_cache import get_cache, extraction_result_key

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractionRequest(BaseModel):
    """Request model for starting extraction"""
    journal_codes: List[str]
    force_refresh: bool = False
    download_pdfs: bool = True
    

class ExtractionResponse(BaseModel):
    """Response model for extraction status"""
    id: UUID
    journal_code: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    manuscripts_count: int = 0
    referees_count: int = 0
    error_message: Optional[str] = None
    

@router.post("/start", response_model=List[ExtractionResponse])
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
) -> List[ExtractionResponse]:
    """Start extraction for specified journals"""
    
    # Validate journal codes
    valid_journals = ["SICON", "SIFIN", "MF", "MOR", "JOTA", "MAFE", "FS", "NACO"]
    invalid = [j for j in request.journal_codes if j not in valid_journals]
    
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid journal codes: {invalid}"
        )
    
    # Create extraction tasks
    responses = []
    
    for journal_code in request.journal_codes:
        # Check cache if not forcing refresh
        if not request.force_refresh:
            cache = await get_cache()
            cache_key = extraction_result_key(journal_code, datetime.now())
            cached = await cache.get(cache_key)
            
            if cached:
                responses.append(ExtractionResponse(**cached))
                continue
        
        # Create new extraction
        extraction = ExtractionResult(
            journal_code=journal_code,
            started_at=datetime.utcnow(),
            metadata={
                "download_pdfs": request.download_pdfs,
                "requested_by": "api"
            }
        )
        
        # Add to background tasks
        background_tasks.add_task(
            run_extraction,
            journal_code,
            extraction.id,
            request.download_pdfs
        )
        
        responses.append(ExtractionResponse(
            id=extraction.id,
            journal_code=journal_code,
            status="started",
            started_at=extraction.started_at
        ))
    
    return responses


@router.get("/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction_status(extraction_id: UUID) -> ExtractionResponse:
    """Get status of a specific extraction"""
    
    async with get_session() as session:
        # Query database for extraction
        from sqlalchemy import select
        from ...infrastructure.database.models import ExtractionLogModel
        
        result = await session.execute(
            select(ExtractionLogModel).where(ExtractionLogModel.id == extraction_id)
        )
        extraction = result.scalar_one_or_none()
        
        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        return ExtractionResponse(
            id=extraction.id,
            journal_code=extraction.journal_code,
            status="completed" if extraction.completed_at else "running",
            started_at=extraction.started_at,
            completed_at=extraction.completed_at,
            manuscripts_count=extraction.manuscripts_count,
            referees_count=extraction.referees_count,
            error_message=extraction.error_message
        )


@router.get("/", response_model=List[ExtractionResponse])
async def list_extractions(
    journal_code: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ExtractionResponse]:
    """List recent extractions"""
    
    async with get_session() as session:
        from sqlalchemy import select
        from ...infrastructure.database.models import ExtractionLogModel
        
        query = select(ExtractionLogModel)
        
        if journal_code:
            query = query.where(ExtractionLogModel.journal_code == journal_code)
            
        query = query.order_by(ExtractionLogModel.started_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        extractions = result.scalars().all()
        
        return [
            ExtractionResponse(
                id=e.id,
                journal_code=e.journal_code,
                status="completed" if e.completed_at else "running",
                started_at=e.started_at,
                completed_at=e.completed_at,
                manuscripts_count=e.manuscripts_count,
                referees_count=e.referees_count,
                error_message=e.error_message
            )
            for e in extractions
        ]


async def run_extraction(
    journal_code: str, 
    extraction_id: UUID,
    download_pdfs: bool
) -> None:
    """Background task to run extraction"""
    logger.info(f"Starting extraction for {journal_code} (ID: {extraction_id})")
    
    try:
        # Get the appropriate scraper
        if journal_code == "SICON":
            from ...infrastructure.scrapers.sicon_scraper import SICONScraper
            scraper = SICONScraper()
        elif journal_code == "SIFIN":
            from ...infrastructure.scrapers.sifin_scraper import SIFINScraper
            scraper = SIFINScraper()
        else:
            raise NotImplementedError(f"Scraper for {journal_code} not implemented")
        
        # Get credentials
        from ...infrastructure.config import get_settings
        settings = get_settings()
        
        credentials = {
            'orcid_email': settings.credentials.orcid_email,
            'orcid_password': settings.credentials.orcid_password
        }
        
        # Authenticate
        if not await scraper.authenticate(credentials):
            raise Exception("Authentication failed")
        
        # Extract manuscripts
        manuscripts = await scraper.extract_manuscripts()
        
        # Extract referee details for each manuscript
        total_referees = 0
        for manuscript in manuscripts:
            reviews = await scraper.extract_referee_details(manuscript)
            manuscript.reviews = reviews
            total_referees += len(reviews)
            
            # Download PDFs if requested
            if download_pdfs:
                pdf_path = await scraper.download_manuscript_pdf(manuscript)
                if pdf_path:
                    manuscript.pdf_path = pdf_path
        
        # Save to database
        async with get_session() as session:
            # Save manuscripts and reviews
            # ... database save logic ...
            
            # Update extraction log
            from sqlalchemy import update
            from ...infrastructure.database.models import ExtractionLogModel
            
            await session.execute(
                update(ExtractionLogModel)
                .where(ExtractionLogModel.id == extraction_id)
                .values(
                    completed_at=datetime.utcnow(),
                    success=True,
                    manuscripts_count=len(manuscripts),
                    referees_count=total_referees
                )
            )
            
        # Cache the result
        cache = await get_cache()
        cache_key = extraction_result_key(journal_code, datetime.now())
        await cache.set(cache_key, {
            'id': str(extraction_id),
            'journal_code': journal_code,
            'status': 'completed',
            'manuscripts_count': len(manuscripts),
            'referees_count': total_referees
        }, ttl=3600)
        
        logger.info(f"Extraction completed for {journal_code}: {len(manuscripts)} manuscripts, {total_referees} referees")
        
    except Exception as e:
        logger.error(f"Extraction failed for {journal_code}: {e}")
        
        # Update extraction log with error
        async with get_session() as session:
            from sqlalchemy import update
            from ...infrastructure.database.models import ExtractionLogModel
            
            await session.execute(
                update(ExtractionLogModel)
                .where(ExtractionLogModel.id == extraction_id)
                .values(
                    completed_at=datetime.utcnow(),
                    success=False,
                    error_message=str(e)
                )
            )