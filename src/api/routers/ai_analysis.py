"""
AI Analysis API endpoints - Migrated and enhanced for new architecture
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from pydantic import BaseModel, Field

from ...ai.services import create_ai_orchestrator
from ...ai.models.manuscript_analysis import ComprehensiveAnalysis
from ...infrastructure.config import get_settings

logger = logging.getLogger(__name__)

# Initialize AI orchestrator
settings = get_settings()
ai_orchestrator = create_ai_orchestrator(
    openai_api_key=settings.openai_api_key,
    cache_enabled=True
)

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


# Request/Response Models
class ManuscriptAnalysisRequest(BaseModel):
    """Request model for manuscript analysis"""
    manuscript_id: str
    title: str
    abstract: str = ""
    journal_code: str
    keywords: List[str] = Field(default_factory=list)
    exclude_authors: List[str] = Field(default_factory=list)
    pdf_path: Optional[str] = None


class DeskRejectionRequest(BaseModel):
    """Request model for desk rejection analysis"""
    manuscript_id: str
    title: str
    abstract: str
    journal_code: str
    pdf_path: Optional[str] = None


class RefereeRecommendationRequest(BaseModel):
    """Request model for referee recommendations"""
    manuscript_id: str
    title: str
    abstract: str
    journal_code: str
    research_area: str
    keywords: List[str]
    exclude_authors: List[str] = Field(default_factory=list)
    include_performance_data: bool = True


class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    success: bool
    manuscript_id: str
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.now)


# API Endpoints

@router.post("/analyze/comprehensive", response_model=AnalysisResponse)
async def analyze_manuscript_comprehensively(
    request: ManuscriptAnalysisRequest
) -> AnalysisResponse:
    """
    Perform comprehensive AI-powered manuscript analysis
    Includes desk rejection analysis, metadata extraction, and referee recommendations
    """
    logger.info(f"🔬 Starting comprehensive analysis for manuscript: {request.manuscript_id}")
    
    start_time = datetime.now()
    
    try:
        analysis = await ai_orchestrator.analyze_manuscript_comprehensively(
            manuscript_id=request.manuscript_id,
            title=request.title,
            abstract=request.abstract,
            journal_code=request.journal_code,
            pdf_path=request.pdf_path,
            keywords=request.keywords,
            exclude_authors=request.exclude_authors
        )
        
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        return AnalysisResponse(
            success=True,
            manuscript_id=request.manuscript_id,
            analysis=analysis.get_analysis_summary(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"❌ Comprehensive analysis failed: {e}")
        end_time = datetime.now()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        
        return AnalysisResponse(
            success=False,
            manuscript_id=request.manuscript_id,
            error=str(e),
            processing_time_ms=processing_time
        )


@router.post("/analyze/desk-rejection")
async def analyze_desk_rejection(
    request: DeskRejectionRequest
) -> Dict[str, Any]:
    """
    Perform AI-powered desk rejection analysis
    """
    logger.info(f"⚖️ Starting desk rejection analysis for: {request.manuscript_id}")
    
    try:
        # Use the AI client directly for desk rejection only
        desk_analysis = await ai_orchestrator.ai_client.analyze_for_desk_rejection(
            title=request.title,
            abstract=request.abstract,
            full_text_sample="",  # Would extract from PDF if available
            journal_code=request.journal_code
        )
        
        return {
            "success": True,
            "manuscript_id": request.manuscript_id,
            "recommendation": desk_analysis.recommendation.value,
            "confidence": desk_analysis.confidence,
            "overall_score": desk_analysis.overall_score,
            "rejection_reasons": desk_analysis.rejection_reasons,
            "quality_issues": [
                {
                    "type": issue.issue_type.value,
                    "severity": issue.severity,
                    "description": issue.description,
                    "location": issue.location,
                    "suggestion": issue.suggestion
                }
                for issue in desk_analysis.quality_issues
            ],
            "scope_issues": desk_analysis.scope_issues,
            "technical_issues": desk_analysis.technical_issues,
            "summary": desk_analysis.recommendation_summary,
            "detailed_explanation": desk_analysis.detailed_explanation,
            "analysis_timestamp": desk_analysis.analysis_timestamp.isoformat(),
            "processing_time_seconds": desk_analysis.processing_time_seconds
        }
        
    except Exception as e:
        logger.error(f"❌ Desk rejection analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/recommend/referees")
async def recommend_referees(
    request: RefereeRecommendationRequest
) -> Dict[str, Any]:
    """
    Get AI-powered referee recommendations with optional historical analytics
    """
    logger.info(f"👥 Getting referee recommendations for: {request.manuscript_id}")
    
    try:
        recommendations = await ai_orchestrator.get_referee_suggestions_with_analytics(
            manuscript_id=request.manuscript_id,
            title=request.title,
            abstract=request.abstract,
            journal_code=request.journal_code,
            research_area=request.research_area,
            keywords=request.keywords,
            exclude_authors=request.exclude_authors,
            include_performance_data=request.include_performance_data
        )
        
        return {
            "success": True,
            "manuscript_id": request.manuscript_id,
            "journal_code": request.journal_code,
            "total_recommendations": len(recommendations),
            "recommendations": recommendations,
            "generation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Referee recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.get("/explain/{manuscript_id}")
async def explain_ai_decision(
    manuscript_id: str
) -> Dict[str, Any]:
    """
    Get human-readable explanation of AI analysis decision
    """
    logger.info(f"📝 Generating explanation for manuscript: {manuscript_id}")
    
    try:
        # This would need to retrieve the stored analysis first
        # For now, return a placeholder
        return {
            "success": True,
            "manuscript_id": manuscript_id,
            "explanation": "AI decision explanation feature is being enhanced. Please check back soon.",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate explanation: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")


@router.get("/insights/journal/{journal_code}")
async def get_journal_ai_insights(
    journal_code: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
) -> Dict[str, Any]:
    """
    Get AI-powered insights for journal performance
    """
    logger.info(f"📊 Getting AI insights for journal: {journal_code}")
    
    try:
        insights = await ai_orchestrator.get_journal_ai_insights(
            journal_code=journal_code,
            days=days
        )
        
        if not insights:
            raise HTTPException(status_code=404, detail=f"No insights available for journal {journal_code}")
        
        return {
            "success": True,
            "journal_code": journal_code,
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get journal insights: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


@router.get("/status")
async def get_ai_service_status() -> Dict[str, Any]:
    """
    Get AI service availability and status
    """
    try:
        # Check AI client availability
        ai_available = await ai_orchestrator.ai_client.check_model_availability(
            ai_orchestrator.default_model
        )
        
        # Get usage stats (if available)
        usage_stats = await ai_orchestrator.ai_client.get_usage_stats()
        
        return {
            "ai_service_available": ai_available,
            "default_model": ai_orchestrator.default_model.value,
            "features_enabled": {
                "desk_rejection_analysis": ai_available,
                "referee_recommendations": ai_available,
                "metadata_extraction": ai_available,
                "quality_assessment": ai_available,
                "decision_explanation": ai_available
            },
            "usage_stats": usage_stats,
            "cache_enabled": ai_orchestrator.cache_enabled,
            "confidence_threshold": ai_orchestrator.confidence_threshold,
            "status_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get AI service status: {e}")
        return {
            "ai_service_available": False,
            "error": str(e),
            "status_timestamp": datetime.now().isoformat()
        }


@router.post("/upload/analyze")
async def analyze_uploaded_manuscript(
    title: str,
    abstract: str,
    journal_code: str,
    file: UploadFile = File(...),
    keywords: List[str] = Query(default=[])
) -> Dict[str, Any]:
    """
    Analyze uploaded PDF manuscript
    """
    logger.info(f"📄 Analyzing uploaded manuscript: {title[:50]}...")
    
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Generate manuscript ID
            import uuid
            manuscript_id = f"upload_{uuid.uuid4().hex[:8]}"
            
            # Perform comprehensive analysis
            analysis = await ai_orchestrator.analyze_manuscript_comprehensively(
                manuscript_id=manuscript_id,
                title=title,
                abstract=abstract,
                journal_code=journal_code,
                pdf_path=temp_file_path,
                keywords=keywords
            )
            
            return {
                "success": True,
                "manuscript_id": manuscript_id,
                "filename": file.filename,
                "analysis": analysis.get_analysis_summary(),
                "processing_time_ms": analysis.processing_time_ms,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat()
            }
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to analyze uploaded manuscript: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# Health check endpoint
@router.get("/health")
async def ai_health_check() -> Dict[str, str]:
    """AI service health check"""
    try:
        ai_available = await ai_orchestrator.ai_client.check_model_availability(
            ai_orchestrator.default_model
        )
        
        status = "healthy" if ai_available else "degraded"
        
        return {
            "status": status,
            "ai_available": str(ai_available),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }