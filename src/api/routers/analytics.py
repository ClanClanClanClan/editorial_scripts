"""
Analytics API endpoints
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ...infrastructure.database.engine import get_session
from ...infrastructure.database.models import ManuscriptModel, RefereeModel, ReviewModel
from ...infrastructure.database.referee_models import RefereeAnalyticsModel
from ...core.domain.models import ManuscriptStatus, ReviewQuality

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get overall dashboard statistics"""
    # Get total manuscripts
    total_manuscripts_result = await session.execute(
        select(func.count()).select_from(ManuscriptModel)
    )
    total_manuscripts = total_manuscripts_result.scalar() or 0
    
    # Get active referees (those who reviewed in last 90 days)
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    active_referees_result = await session.execute(
        select(func.count(func.distinct(ReviewModel.referee_id)))
        .where(ReviewModel.submitted_at >= ninety_days_ago)
    )
    active_referees = active_referees_result.scalar() or 0
    
    # Get pending reviews
    pending_reviews_result = await session.execute(
        select(func.count()).select_from(ReviewModel)
        .where(ReviewModel.submitted_at.is_(None))
    )
    pending_reviews = pending_reviews_result.scalar() or 0
    
    # Get average review time for completed reviews
    avg_review_time_result = await session.execute(
        select(func.avg(ReviewModel.review_time_days))
        .where(ReviewModel.review_time_days.isnot(None))
    )
    avg_review_time = avg_review_time_result.scalar() or 0
    
    # Get manuscripts by status
    status_counts_result = await session.execute(
        select(
            ManuscriptModel.status,
            func.count().label('count')
        )
        .group_by(ManuscriptModel.status)
    )
    status_counts = {row.status: row.count for row in status_counts_result}
    
    # Get recent activity
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_submissions_result = await session.execute(
        select(func.count()).select_from(ManuscriptModel)
        .where(ManuscriptModel.submission_date >= seven_days_ago)
    )
    recent_submissions = recent_submissions_result.scalar() or 0
    
    recent_reviews_result = await session.execute(
        select(func.count()).select_from(ReviewModel)
        .where(ReviewModel.submitted_at >= seven_days_ago)
    )
    recent_reviews = recent_reviews_result.scalar() or 0
    
    return {
        "total_manuscripts": total_manuscripts,
        "active_referees": active_referees,
        "pending_reviews": pending_reviews,
        "average_review_time_days": round(avg_review_time, 1),
        "manuscripts_by_status": status_counts,
        "recent_activity": {
            "new_submissions_7d": recent_submissions,
            "completed_reviews_7d": recent_reviews
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/referee-performance")
async def get_referee_performance_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    journal: Optional[str] = Query(None, description="Filter by journal code"),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get referee performance analytics"""
    # Default to last 90 days if no dates provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=90)
    
    # Build base query for reviews in period
    reviews_query = select(ReviewModel).where(
        and_(
            ReviewModel.submitted_at >= datetime.combine(start_date, datetime.min.time()),
            ReviewModel.submitted_at <= datetime.combine(end_date, datetime.max.time())
        )
    )
    
    # Apply journal filter if provided
    if journal:
        reviews_query = reviews_query.join(ManuscriptModel).where(
            ManuscriptModel.journal_code == journal
        )
    
    # Get performance metrics
    result = await session.execute(reviews_query)
    reviews = result.scalars().all()
    
    if not reviews:
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "journal": journal
            },
            "metrics": {
                "total_reviews": 0,
                "average_review_time": 0,
                "on_time_rate": 0,
                "quality_distribution": {},
                "top_performers": []
            }
        }
    
    # Calculate metrics
    total_reviews = len(reviews)
    review_times = [r.review_time_days for r in reviews if r.review_time_days]
    on_time_reviews = sum(1 for r in reviews if r.review_time_days and r.review_time_days <= 21)
    
    # Quality distribution
    quality_counts = {}
    for review in reviews:
        quality = review.quality or ReviewQuality.UNKNOWN
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
    
    # Get top performers
    referee_stats = {}
    for review in reviews:
        if review.referee_id:
            if review.referee_id not in referee_stats:
                referee_stats[review.referee_id] = {
                    'count': 0,
                    'total_time': 0,
                    'on_time': 0
                }
            referee_stats[review.referee_id]['count'] += 1
            if review.review_time_days:
                referee_stats[review.referee_id]['total_time'] += review.review_time_days
                if review.review_time_days <= 21:
                    referee_stats[review.referee_id]['on_time'] += 1
    
    # Get referee names for top performers
    top_referee_ids = sorted(
        referee_stats.keys(),
        key=lambda x: referee_stats[x]['count'],
        reverse=True
    )[:10]
    
    top_performers = []
    if top_referee_ids:
        referees_result = await session.execute(
            select(RefereeModel).where(RefereeModel.id.in_(top_referee_ids))
        )
        referees_map = {r.id: r for r in referees_result.scalars()}
        
        for ref_id in top_referee_ids:
            referee = referees_map.get(ref_id)
            stats = referee_stats[ref_id]
            if referee:
                top_performers.append({
                    'referee_id': str(ref_id),
                    'name': referee.name,
                    'review_count': stats['count'],
                    'average_time': round(stats['total_time'] / stats['count'], 1) if stats['count'] > 0 else 0,
                    'on_time_rate': round(stats['on_time'] / stats['count'] * 100, 1) if stats['count'] > 0 else 0
                })
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "journal": journal
        },
        "metrics": {
            "total_reviews": total_reviews,
            "average_review_time": round(sum(review_times) / len(review_times), 1) if review_times else 0,
            "on_time_rate": round(on_time_reviews / total_reviews * 100, 1) if total_reviews > 0 else 0,
            "quality_distribution": quality_counts,
            "top_performers": top_performers
        }
    }


@router.get("/journal-comparison")
async def get_journal_comparison(
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Compare metrics across journals"""
    # Get all journals with manuscripts
    journals_result = await session.execute(
        select(
            ManuscriptModel.journal_code,
            func.count().label('manuscript_count')
        )
        .group_by(ManuscriptModel.journal_code)
        .having(func.count() > 0)
    )
    
    journal_comparisons = []
    
    for row in journals_result:
        journal_code = row.journal_code
        manuscript_count = row.manuscript_count
        
        # Get review metrics for this journal
        review_stats_result = await session.execute(
            select(
                func.count().label('review_count'),
                func.avg(ReviewModel.review_time_days).label('avg_review_time'),
                func.count(func.distinct(ReviewModel.referee_id)).label('unique_referees')
            )
            .select_from(ReviewModel)
            .join(ManuscriptModel)
            .where(ManuscriptModel.journal_code == journal_code)
        )
        review_stats = review_stats_result.first()
        
        # Get referee analytics if available
        analytics_result = await session.execute(
            select(
                func.avg(RefereeAnalyticsModel.overall_score).label('avg_referee_score'),
                func.avg(RefereeAnalyticsModel.reliability_score).label('avg_reliability')
            )
            .where(RefereeAnalyticsModel.journal_code == journal_code)
        )
        analytics_stats = analytics_result.first()
        
        journal_comparisons.append({
            "journal_code": journal_code,
            "manuscript_count": manuscript_count,
            "review_metrics": {
                "total_reviews": review_stats.review_count or 0,
                "average_review_time": round(review_stats.avg_review_time or 0, 1),
                "unique_referees": review_stats.unique_referees or 0
            },
            "referee_quality": {
                "average_score": round(analytics_stats.avg_referee_score or 0, 2) if analytics_stats else None,
                "average_reliability": round(analytics_stats.avg_reliability or 0, 2) if analytics_stats else None
            }
        })
    
    # Sort by manuscript count
    journal_comparisons.sort(key=lambda x: x['manuscript_count'], reverse=True)
    
    return journal_comparisons