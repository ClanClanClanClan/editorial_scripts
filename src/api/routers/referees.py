"""
Referee management API endpoints
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field, EmailStr

from ...infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
from analytics.models.referee_metrics import (
    RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
    ReliabilityMetrics, ExpertiseMetrics
)

router = APIRouter()


# Pydantic models for API
class TimeMetricsResponse(BaseModel):
    avg_response_time: float = Field(..., description="Average days to respond")
    avg_review_time: float = Field(..., description="Average days to complete review")
    fastest_review: float = Field(..., description="Fastest review time in days")
    slowest_review: float = Field(..., description="Slowest review time in days")
    response_time_std: float = Field(..., description="Response time standard deviation")
    review_time_std: float = Field(..., description="Review time standard deviation")
    on_time_rate: float = Field(..., ge=0, le=1, description="Rate of on-time submissions")
    consistency_score: float = Field(..., ge=0, le=1, description="Overall consistency score")


class QualityMetricsResponse(BaseModel):
    avg_quality_score: float = Field(..., ge=0, le=10, description="Average quality score")
    quality_consistency: float = Field(..., description="Quality consistency measure")
    report_thoroughness: float = Field(..., ge=0, le=1, description="Report thoroughness")
    constructiveness_score: float = Field(..., ge=0, le=10, description="Constructiveness score")
    technical_accuracy: float = Field(..., ge=0, le=10, description="Technical accuracy")
    clarity_score: float = Field(..., ge=0, le=10, description="Clarity score")
    actionability_score: float = Field(..., ge=0, le=10, description="Actionability score")
    overall_quality: float = Field(..., ge=0, le=10, description="Overall quality score")


class WorkloadMetricsResponse(BaseModel):
    current_reviews: int = Field(..., ge=0, description="Current active reviews")
    completed_reviews_30d: int = Field(..., ge=0, description="Reviews completed in last 30 days")
    completed_reviews_90d: int = Field(..., ge=0, description="Reviews completed in last 90 days")
    completed_reviews_365d: int = Field(..., ge=0, description="Reviews completed in last year")
    monthly_average: float = Field(..., ge=0, description="Average reviews per month")
    peak_capacity: int = Field(..., ge=0, description="Maximum concurrent reviews handled")
    availability_score: float = Field(..., ge=0, le=1, description="Current availability")
    burnout_risk_score: float = Field(..., ge=0, le=1, description="Burnout risk assessment")
    capacity_utilization: float = Field(..., ge=0, le=1, description="Current capacity utilization")


class ReliabilityMetricsResponse(BaseModel):
    acceptance_rate: float = Field(..., ge=0, le=1, description="Review invitation acceptance rate")
    completion_rate: float = Field(..., ge=0, le=1, description="Review completion rate")
    ghost_rate: float = Field(..., ge=0, le=1, description="No-response rate")
    decline_after_accept_rate: float = Field(..., ge=0, le=1, description="Withdrawal rate")
    reminder_effectiveness: float = Field(..., ge=0, le=1, description="Response rate after reminders")
    communication_score: float = Field(..., ge=0, le=1, description="Communication responsiveness")
    excuse_frequency: float = Field(..., ge=0, le=1, description="Extension request frequency")
    reliability_score: float = Field(..., ge=0, le=1, description="Overall reliability score")


class ExpertiseMetricsResponse(BaseModel):
    expertise_areas: List[str] = Field(default_factory=list, description="Areas of expertise")
    h_index: Optional[int] = Field(None, description="H-index")
    recent_publications: int = Field(0, description="Recent publication count")
    citation_count: int = Field(0, description="Total citations")
    years_experience: int = Field(0, description="Years of experience")
    expertise_score: float = Field(..., ge=0, le=1, description="Overall expertise score")


class RefereeMetricsResponse(BaseModel):
    referee_id: str = Field(..., description="Unique referee identifier")
    name: str = Field(..., description="Referee name")
    email: EmailStr = Field(..., description="Referee email")
    institution: str = Field(..., description="Referee institution")
    overall_score: float = Field(..., ge=0, le=10, description="Overall performance score")
    time_metrics: TimeMetricsResponse
    quality_metrics: QualityMetricsResponse
    workload_metrics: WorkloadMetricsResponse
    reliability_metrics: ReliabilityMetricsResponse
    expertise_metrics: ExpertiseMetricsResponse
    last_updated: datetime
    data_completeness: float = Field(..., ge=0, le=1, description="Data completeness percentage")


class CreateRefereeMetricsRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    institution: str = Field(..., max_length=500)
    time_metrics: TimeMetricsResponse
    quality_metrics: QualityMetricsResponse
    workload_metrics: WorkloadMetricsResponse
    reliability_metrics: ReliabilityMetricsResponse
    expertise_metrics: ExpertiseMetricsResponse


class UpdateRefereeMetricsRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    institution: Optional[str] = Field(None, max_length=500)
    time_metrics: Optional[TimeMetricsResponse] = None
    quality_metrics: Optional[QualityMetricsResponse] = None
    workload_metrics: Optional[WorkloadMetricsResponse] = None
    reliability_metrics: Optional[ReliabilityMetricsResponse] = None
    expertise_metrics: Optional[ExpertiseMetricsResponse] = None


class RefereeListResponse(BaseModel):
    id: UUID
    name: str
    email: str
    institution: str
    overall_score: float
    total_reviews: int
    last_review_date: Optional[datetime]


class PerformanceStatsResponse(BaseModel):
    total_referees: int
    average_score: float
    scored_referees: int
    top_performers_count: int
    active_referees_30d: int
    active_referees_90d: int


# Dependency to get repository
async def get_repository() -> RefereeRepositoryFixed:
    return RefereeRepositoryFixed()


@router.post("/", response_model=UUID, status_code=status.HTTP_201_CREATED)
async def create_referee_metrics(
    request: CreateRefereeMetricsRequest,
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> UUID:
    """Create new referee metrics"""
    try:
        # Convert request to domain model
        metrics = RefereeMetrics(
            referee_id=str(uuid.uuid4()),  # Generate new ID
            name=request.name,
            email=request.email,
            institution=request.institution,
            time_metrics=TimeMetrics(
                avg_response_time=request.time_metrics.avg_response_time,
                avg_review_time=request.time_metrics.avg_review_time,
                fastest_review=request.time_metrics.fastest_review,
                slowest_review=request.time_metrics.slowest_review,
                response_time_std=request.time_metrics.response_time_std,
                review_time_std=request.time_metrics.review_time_std,
                on_time_rate=request.time_metrics.on_time_rate
            ),
            quality_metrics=QualityMetrics(
                avg_quality_score=request.quality_metrics.avg_quality_score,
                quality_consistency=request.quality_metrics.quality_consistency,
                report_thoroughness=request.quality_metrics.report_thoroughness,
                constructiveness_score=request.quality_metrics.constructiveness_score,
                technical_accuracy=request.quality_metrics.technical_accuracy,
                clarity_score=request.quality_metrics.clarity_score,
                actionability_score=request.quality_metrics.actionability_score
            ),
            workload_metrics=WorkloadMetrics(
                current_reviews=request.workload_metrics.current_reviews,
                completed_reviews_30d=request.workload_metrics.completed_reviews_30d,
                completed_reviews_90d=request.workload_metrics.completed_reviews_90d,
                completed_reviews_365d=request.workload_metrics.completed_reviews_365d,
                monthly_average=request.workload_metrics.monthly_average,
                peak_capacity=request.workload_metrics.peak_capacity,
                availability_score=request.workload_metrics.availability_score,
                burnout_risk_score=request.workload_metrics.burnout_risk_score
            ),
            reliability_metrics=ReliabilityMetrics(
                acceptance_rate=request.reliability_metrics.acceptance_rate,
                completion_rate=request.reliability_metrics.completion_rate,
                ghost_rate=request.reliability_metrics.ghost_rate,
                decline_after_accept_rate=request.reliability_metrics.decline_after_accept_rate,
                reminder_effectiveness=request.reliability_metrics.reminder_effectiveness,
                communication_score=request.reliability_metrics.communication_score,
                excuse_frequency=request.reliability_metrics.excuse_frequency
            ),
            expertise_metrics=ExpertiseMetrics(
                expertise_areas=request.expertise_metrics.expertise_areas,
                h_index=request.expertise_metrics.h_index,
                recent_publications=request.expertise_metrics.recent_publications,
                citation_count=request.expertise_metrics.citation_count,
                years_experience=request.expertise_metrics.years_experience
            )
        )
        
        # Save to database
        referee_id = await repo.save_referee_metrics(metrics)
        return referee_id
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create referee metrics: {str(e)}")


# SPECIFIC ROUTES MUST COME BEFORE GENERIC {referee_id} ROUTE

@router.get("/top-performers", response_model=List[Dict[str, Any]])
async def get_top_performers(
    limit: int = Query(10, ge=1, le=100, description="Number of top performers to return"),
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> List[Dict[str, Any]]:
    """Get top performing referees"""
    try:
        performers = await repo.get_top_performers(limit=limit)
        return performers
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top performers: {str(e)}")


@router.get("/stats", response_model=PerformanceStatsResponse)
async def get_performance_stats(
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> PerformanceStatsResponse:
    """Get overall performance statistics"""
    try:
        stats = await repo.get_performance_stats()
        return PerformanceStatsResponse(
            total_referees=stats.get("total_referees", 0),
            average_score=stats.get("avg_score", 0.0),
            scored_referees=stats.get("scored_referees", 0),
            top_performers_count=len(await repo.get_top_performers(limit=10)),
            active_referees_30d=await repo.get_active_referee_count(days=30),
            active_referees_90d=await repo.get_active_referee_count(days=90)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")


@router.get("/by-email/{email}", response_model=RefereeMetricsResponse)
async def get_referee_by_email(
    email: EmailStr,
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> RefereeMetricsResponse:
    """Get referee metrics by email"""
    try:
        metrics = await repo.get_referee_by_email(email)
        if not metrics:
            raise HTTPException(status_code=404, detail="Referee not found")
            
        # Reuse the same conversion logic
        return await get_referee_metrics(UUID(metrics.referee_id), repo)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get referee by email: {str(e)}")


@router.get("/{referee_id}", response_model=RefereeMetricsResponse)
async def get_referee_metrics(
    referee_id: UUID,
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> RefereeMetricsResponse:
    """Get referee metrics by ID"""
    try:
        metrics = await repo.get_referee_metrics(referee_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Referee not found")
            
        # Convert domain model to response
        return RefereeMetricsResponse(
            referee_id=metrics.referee_id,
            name=metrics.name,
            email=metrics.email,
            institution=metrics.institution,
            overall_score=metrics.get_overall_score(),
            time_metrics=TimeMetricsResponse(
                avg_response_time=metrics.time_metrics.avg_response_time,
                avg_review_time=metrics.time_metrics.avg_review_time,
                fastest_review=metrics.time_metrics.fastest_review,
                slowest_review=metrics.time_metrics.slowest_review,
                response_time_std=metrics.time_metrics.response_time_std,
                review_time_std=metrics.time_metrics.review_time_std,
                on_time_rate=metrics.time_metrics.on_time_rate,
                consistency_score=metrics.time_metrics.get_consistency_score()
            ),
            quality_metrics=QualityMetricsResponse(
                avg_quality_score=metrics.quality_metrics.avg_quality_score,
                quality_consistency=metrics.quality_metrics.quality_consistency,
                report_thoroughness=metrics.quality_metrics.report_thoroughness,
                constructiveness_score=metrics.quality_metrics.constructiveness_score,
                technical_accuracy=metrics.quality_metrics.technical_accuracy,
                clarity_score=metrics.quality_metrics.clarity_score,
                actionability_score=metrics.quality_metrics.actionability_score,
                overall_quality=metrics.quality_metrics.get_overall_quality()
            ),
            workload_metrics=WorkloadMetricsResponse(
                current_reviews=metrics.workload_metrics.current_reviews,
                completed_reviews_30d=metrics.workload_metrics.completed_reviews_30d,
                completed_reviews_90d=metrics.workload_metrics.completed_reviews_90d,
                completed_reviews_365d=metrics.workload_metrics.completed_reviews_365d,
                monthly_average=metrics.workload_metrics.monthly_average,
                peak_capacity=metrics.workload_metrics.peak_capacity,
                availability_score=metrics.workload_metrics.availability_score,
                burnout_risk_score=metrics.workload_metrics.burnout_risk_score,
                capacity_utilization=metrics.workload_metrics.get_capacity_utilization()
            ),
            reliability_metrics=ReliabilityMetricsResponse(
                acceptance_rate=metrics.reliability_metrics.acceptance_rate,
                completion_rate=metrics.reliability_metrics.completion_rate,
                ghost_rate=metrics.reliability_metrics.ghost_rate,
                decline_after_accept_rate=metrics.reliability_metrics.decline_after_accept_rate,
                reminder_effectiveness=metrics.reliability_metrics.reminder_effectiveness,
                communication_score=metrics.reliability_metrics.communication_score,
                excuse_frequency=metrics.reliability_metrics.excuse_frequency,
                reliability_score=metrics.reliability_metrics.get_reliability_score()
            ),
            expertise_metrics=ExpertiseMetricsResponse(
                expertise_areas=metrics.expertise_metrics.expertise_areas,
                h_index=metrics.expertise_metrics.h_index,
                recent_publications=metrics.expertise_metrics.recent_publications,
                citation_count=metrics.expertise_metrics.citation_count,
                years_experience=metrics.expertise_metrics.years_experience,
                expertise_score=metrics.expertise_metrics.get_expertise_score()
            ),
            last_updated=metrics.last_updated,
            data_completeness=metrics.data_completeness
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get referee metrics: {str(e)}")


@router.post("/{referee_id}/activity")
async def record_referee_activity(
    referee_id: UUID,
    activity_type: str,
    manuscript_id: str,
    details: Optional[Dict[str, Any]] = None,
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> Dict[str, str]:
    """Record referee activity"""
    try:
        await repo.record_referee_activity(
            referee_id=referee_id,
            activity_type=activity_type,
            manuscript_id=manuscript_id,
            details=details
        )
        return {"status": "activity recorded"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record activity: {str(e)}")


@router.put("/{referee_id}", response_model=UUID)
async def update_referee_metrics(
    referee_id: UUID,
    request: UpdateRefereeMetricsRequest,
    repo: RefereeRepositoryFixed = Depends(get_repository)
) -> UUID:
    """Update existing referee metrics"""
    try:
        # Simplified update - just basic fields for now
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.institution is not None:
            update_data["institution"] = request.institution
            
        success = await repo.update_referee_basic(referee_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Referee not found or update failed")
            
        return referee_id
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update referee metrics: {str(e)}")