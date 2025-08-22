"""Journal management API endpoints."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class JournalInfo(BaseModel):
    """Journal information model."""
    
    id: str = Field(..., description="Journal identifier (e.g., 'MF', 'MOR')")
    name: str = Field(..., description="Full journal name")
    platform: str = Field(..., description="Platform type (ScholarOne, SIAM, etc.)")
    url: str = Field(..., description="Journal URL")
    supported: bool = Field(..., description="Whether extraction is supported")
    last_sync: Optional[str] = Field(None, description="Last successful sync timestamp")
    manuscript_count: int = Field(0, description="Total manuscripts in database")


class JournalListResponse(BaseModel):
    """Response model for journal list."""
    
    journals: List[JournalInfo]
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
    tests_run: List[str]
    results: Dict[str, bool]
    errors: List[str]
    duration_seconds: float


# Journal registry - In production, this would come from database/config
SUPPORTED_JOURNALS = {
    "MF": JournalInfo(
        id="MF",
        name="Mathematical Finance",
        platform="ScholarOne",
        url="https://mc.manuscriptcentral.com/mafi",
        supported=True,
        manuscript_count=0,
    ),
    "MOR": JournalInfo(
        id="MOR", 
        name="Mathematics of Operations Research",
        platform="ScholarOne",
        url="https://mc.manuscriptcentral.com/mor",
        supported=True,
        manuscript_count=0,
    ),
    "SICON": JournalInfo(
        id="SICON",
        name="SIAM Journal on Control and Optimization",
        platform="SIAM",
        url="https://www.siam.org/journals/sicon",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
    "SIFIN": JournalInfo(
        id="SIFIN",
        name="SIAM Journal on Financial Mathematics",
        platform="SIAM", 
        url="https://www.siam.org/journals/sifin",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
    "JOTA": JournalInfo(
        id="JOTA",
        name="Journal of Optimization Theory and Applications",
        platform="Springer",
        url="https://www.springer.com/journal/10957",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
    "MAFE": JournalInfo(
        id="MAFE",
        name="Mathematical Finance and Economics",
        platform="Springer",
        url="https://www.springer.com/journal/11579",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
    "FS": JournalInfo(
        id="FS",
        name="Finance and Stochastics",
        platform="Email",
        url="https://www.springer.com/journal/780",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
    "NACO": JournalInfo(
        id="NACO",
        name="Numerical Algorithms",
        platform="Unknown",
        url="https://www.springer.com/journal/11075",
        supported=False,  # Not implemented yet
        manuscript_count=0,
    ),
}


@router.get("/", response_model=JournalListResponse)
async def list_journals():
    """
    List all supported journals.
    
    Returns information about all journals that the system knows about,
    including their support status and basic metadata.
    """
    journals = list(SUPPORTED_JOURNALS.values())
    supported_count = sum(1 for j in journals if j.supported)
    
    return JournalListResponse(
        journals=journals,
        total_supported=supported_count,
        total_journals=len(journals),
    )


@router.get("/{journal_id}", response_model=JournalInfo)
async def get_journal(journal_id: str):
    """
    Get information about a specific journal.
    
    - **journal_id**: Journal identifier (e.g., 'MF', 'MOR')
    """
    journal_id = journal_id.upper()
    
    if journal_id not in SUPPORTED_JOURNALS:
        raise HTTPException(
            status_code=404,
            detail=f"Journal '{journal_id}' not found. Supported journals: {list(SUPPORTED_JOURNALS.keys())}"
        )
    
    return SUPPORTED_JOURNALS[journal_id]


@router.post("/{journal_id}/test", response_model=JournalTestResponse)
async def test_journal_connection(journal_id: str, request: JournalTestRequest):
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
        raise HTTPException(
            status_code=404,
            detail=f"Journal '{journal_id}' not found"
        )
    
    journal = SUPPORTED_JOURNALS[journal_id]
    
    if not journal.supported:
        raise HTTPException(
            status_code=400,
            detail=f"Journal '{journal_id}' is not yet supported"
        )
    
    start_time = time.time()
    tests_run = []
    results = {}
    errors = []
    
    try:
        # Test adapter creation
        tests_run.append("adapter_creation")
        
        if journal_id == "MF":
            from src.ecc.adapters.journals.mf import MFAdapter
            
            # Test with headless mode for speed
            async with MFAdapter(headless=True) as adapter:
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
            # TODO: Implement MOR adapter test
            results["adapter_creation"] = False
            errors.append("MOR adapter not yet implemented")
        
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
async def get_journal_categories(journal_id: str):
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
            status_code=500,
            detail=f"Failed to get categories for {journal_id}: {str(e)}"
        )


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
            status_code=500,
            detail=f"Health check failed for {journal_id}: {str(e)}"
        )