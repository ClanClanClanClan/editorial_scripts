"""
Referee Analytics Repository Implementation
Stores and retrieves referee performance metrics in PostgreSQL
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.domain.ports import CacheService
# Import analytics models using absolute imports
from analytics.models.referee_metrics import (
    RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
    ReliabilityMetrics, ExpertiseMetrics, JournalSpecificMetrics,
    PercentileRanks, PerformanceTier
)
from ..database.engine import get_session
from ..database.referee_models import (
    RefereeAnalyticsModel, RefereeExpertiseModel, ManuscriptAnalyticsModel,
    ReviewHistoryModel, RefereeAnalyticsCacheModel,
    RefereeMetricsHistoryModel, JournalSpecificMetricsModel,
    PerformanceTierModel
)

logger = logging.getLogger(__name__)


class RefereeAnalyticsRepository:
    """Repository for referee analytics with PostgreSQL and caching"""
    
    def __init__(self, cache: Optional[CacheService] = None):
        self.cache = cache
        self.cache_ttl_seconds = 3600 * 24  # 24 hours
    
    async def save_referee_metrics(self, metrics: RefereeMetrics) -> UUID:
        """Save complete referee metrics to database"""
        try:
            async with get_session() as session:
                # Get or create referee
                referee = await self._get_or_create_referee(session, metrics)
                
                # Cache the metrics
                await self._cache_referee_metrics(session, referee.id, metrics)
                
                # Store historical metrics
                await self._store_historical_metrics(session, referee.id, metrics)
                
                # Update journal-specific metrics
                await self._update_journal_metrics(session, referee.id, metrics.journal_metrics)
                
                await session.commit()
                
                # Update cache
                if self.cache:
                    await self.cache.set(
                        f"referee_metrics:{referee.id}",
                        self._serialize_metrics_for_cache(metrics),
                        ttl=self.cache_ttl_seconds
                    )
                
                logger.info(f"✅ Saved referee metrics for {metrics.name} (ID: {referee.id})")
                return referee.id
                
        except Exception as e:
            logger.error(f"❌ Failed to save referee metrics: {e}")
            raise
    
    async def get_referee_metrics(self, referee_id: UUID) -> Optional[RefereeMetrics]:
        """Get referee metrics by ID"""
        try:
            # Check cache first
            if self.cache:
                cached = await self.cache.get(f"referee_metrics:{referee_id}")
                if cached:
                    return self._deserialize_metrics_from_cache(cached)
            
            # Query database
            async with get_session() as session:
                stmt = select(RefereeAnalyticsCacheModel).where(
                    and_(
                        RefereeAnalyticsCacheModel.referee_id == referee_id,
                        RefereeAnalyticsCacheModel.valid_until > datetime.now()
                    )
                )
                
                result = await session.execute(stmt)
                cached_metrics = result.scalar_one_or_none()
                
                if cached_metrics:
                    return self._deserialize_metrics_from_json(cached_metrics.metrics_json)
                
                # If no cached metrics, return None (would need to recalculate)
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get referee metrics for {referee_id}: {e}")
            return None
    
    async def get_referee_by_email(self, email: str) -> Optional[RefereeAnalyticsModel]:
        """Get referee by email address"""
        try:
            async with get_session() as session:
                stmt = select(RefereeAnalyticsModel).where(RefereeAnalyticsModel.email == email)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Failed to get referee by email {email}: {e}")
            return None
    
    async def get_referee_trends(self, referee_id: UUID, days: int = 90) -> Dict[str, Any]:
        """Get historical trends for a referee"""
        try:
            async with get_session() as session:
                start_date = (datetime.now() - timedelta(days=days)).date()
                
                stmt = select(RefereeMetricsHistoryModel).where(
                    and_(
                        RefereeMetricsHistoryModel.referee_id == referee_id,
                        RefereeMetricsHistoryModel.metric_date >= start_date
                    )
                ).order_by(RefereeMetricsHistoryModel.metric_date)
                
                result = await session.execute(stmt)
                history = result.scalars().all()
                
                if not history:
                    return {'error': 'No historical data available'}
                
                # Extract trend data
                dates = [h.metric_date.isoformat() for h in history]
                overall_scores = [h.overall_score for h in history if h.overall_score is not None]
                
                return {
                    'dates': dates,
                    'overall_scores': overall_scores,
                    'speed_scores': [h.speed_score for h in history if h.speed_score is not None],
                    'quality_scores': [h.quality_score for h in history if h.quality_score is not None],
                    'reliability_scores': [h.reliability_score for h in history if h.reliability_score is not None],
                    'workload': [h.current_reviews for h in history],
                    'trend_direction': self._calculate_trend_direction(overall_scores)
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get referee trends for {referee_id}: {e}")
            return {'error': str(e)}
    
    async def get_top_performers(
        self,
        tier: Optional[PerformanceTier] = None,
        journal_code: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get top performing referees"""
        try:
            async with get_session() as session:
                # Base query for recent performance tiers
                stmt = select(
                    PerformanceTierModel.referee_id,
                    PerformanceTierModel.tier,
                    PerformanceTierModel.tier_percentile,
                    PerformanceTierModel.tier_score,
                    RefereeAnalyticsModel.name,
                    RefereeAnalyticsModel.email,
                    RefereeAnalyticsModel.institution
                ).join(RefereeAnalyticsModel).where(
                    PerformanceTierModel.assessment_date >= (datetime.now() - timedelta(days=30)).date()
                )
                
                if tier:
                    stmt = stmt.where(PerformanceTierModel.tier == tier.value)
                
                if journal_code:
                    stmt = stmt.where(PerformanceTierModel.journal_context == journal_code)
                
                stmt = stmt.order_by(PerformanceTierModel.tier_percentile.desc()).limit(limit)
                
                result = await session.execute(stmt)
                performers = result.all()
                
                return [
                    {
                        'referee_id': str(p.referee_id),
                        'name': p.name,
                        'email': p.email,
                        'institution': p.institution,
                        'tier': p.tier,
                        'percentile': p.tier_percentile,
                        'score': p.tier_score
                    }
                    for p in performers
                ]
                
        except Exception as e:
            logger.error(f"❌ Failed to get top performers: {e}")
            return []
    
    async def get_journal_performance_stats(
        self,
        journal_code: str,
        days: int = 90
    ) -> Dict[str, Any]:
        """Get performance statistics for a specific journal"""
        try:
            async with get_session() as session:
                start_date = datetime.now() - timedelta(days=days)
                
                # Get recent review activity
                review_stmt = select(
                    func.count(ReviewHistoryModel.id).label('total_reviews'),
                    func.count(
                        func.nullif(ReviewHistoryModel.submitted_date, None)
                    ).label('completed_reviews'),
                    func.avg(ReviewHistoryModel.quality_score).label('avg_quality'),
                    func.avg(
                        func.extract('epoch', 
                            ReviewHistoryModel.submitted_date - ReviewHistoryModel.responded_date
                        ) / 86400
                    ).label('avg_review_time_days')
                ).join(ManuscriptAnalyticsModel).where(
                    and_(
                        ManuscriptAnalyticsModel.journal_code == journal_code,
                        ReviewHistoryModel.invited_date >= start_date
                    )
                )
                
                result = await session.execute(review_stmt)
                stats = result.one()
                
                # Get journal-specific metrics
                journal_metrics_stmt = select(
                    func.count(JournalSpecificMetricsModel.id).label('active_referees'),
                    func.avg(JournalSpecificMetricsModel.familiarity_score).label('avg_familiarity'),
                    func.avg(JournalSpecificMetricsModel.acceptance_rate).label('avg_acceptance_rate')
                ).where(JournalSpecificMetricsModel.journal_code == journal_code)
                
                journal_result = await session.execute(journal_metrics_stmt)
                journal_stats = journal_result.one()
                
                return {
                    'journal_code': journal_code,
                    'period_days': days,
                    'total_reviews': stats.total_reviews or 0,
                    'completed_reviews': stats.completed_reviews or 0,
                    'completion_rate': (stats.completed_reviews or 0) / max(stats.total_reviews or 1, 1),
                    'avg_quality_score': float(stats.avg_quality or 0),
                    'avg_review_time_days': float(stats.avg_review_time_days or 0),
                    'active_referees': journal_stats.active_referees or 0,
                    'avg_familiarity_score': float(journal_stats.avg_familiarity or 0),
                    'avg_acceptance_rate': float(journal_stats.avg_acceptance_rate or 0),
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get journal performance stats for {journal_code}: {e}")
            return {}
    
    async def record_review_activity(
        self,
        referee_id: UUID,
        manuscript_id: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record referee review activity"""
        try:
            async with get_session() as session:
                # Update review history based on action
                if action == "invited":
                    review = ReviewHistoryModel(
                        referee_id=referee_id,
                        manuscript_id=manuscript_id,
                        invited_date=datetime.now()
                    )
                    session.add(review)
                
                elif action in ["accepted", "declined"]:
                    stmt = update(ReviewHistoryModel).where(
                        and_(
                            ReviewHistoryModel.referee_id == referee_id,
                            ReviewHistoryModel.manuscript_id == manuscript_id
                        )
                    ).values(
                        decision=action,
                        responded_date=datetime.now()
                    )
                    await session.execute(stmt)
                
                elif action == "submitted":
                    quality_score = metadata.get('quality_score') if metadata else None
                    report_length = metadata.get('report_length') if metadata else None
                    
                    stmt = update(ReviewHistoryModel).where(
                        and_(
                            ReviewHistoryModel.referee_id == referee_id,
                            ReviewHistoryModel.manuscript_id == manuscript_id
                        )
                    ).values(
                        submitted_date=datetime.now(),
                        quality_score=quality_score,
                        report_length=report_length
                    )
                    await session.execute(stmt)
                
                await session.commit()
                
                # Invalidate cached metrics
                if self.cache:
                    await self.cache.delete(f"referee_metrics:{referee_id}")
                
                logger.info(f"✅ Recorded review activity: {action} for referee {referee_id}, manuscript {manuscript_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to record review activity: {e}")
    
    async def _get_or_create_referee(self, session: AsyncSession, metrics: RefereeMetrics) -> RefereeAnalyticsModel:
        """Get existing referee or create new one"""
        # Try to find by email first
        stmt = select(RefereeAnalyticsModel).where(RefereeAnalyticsModel.email == metrics.email)
        result = await session.execute(stmt)
        referee = result.scalar_one_or_none()
        
        if referee:
            # Update existing referee
            referee.name = metrics.name
            referee.institution = metrics.institution
            referee.updated_at = datetime.now()
        else:
            # Create new referee
            referee = RefereeAnalyticsModel(
                name=metrics.name,
                email=metrics.email,
                institution=metrics.institution,
                h_index=metrics.expertise_metrics.h_index,
                years_experience=metrics.expertise_metrics.years_experience
            )
            session.add(referee)
            await session.flush()  # Get the ID
        
        return referee
    
    async def _cache_referee_metrics(
        self,
        session: AsyncSession,
        referee_id: UUID,
        metrics: RefereeMetrics
    ) -> None:
        """Cache referee metrics in database"""
        valid_until = datetime.now() + timedelta(hours=24)
        
        # Try to update existing cache
        stmt = update(RefereeAnalyticsCacheModel).where(
            RefereeAnalyticsCacheModel.referee_id == referee_id
        ).values(
            metrics_json=metrics.to_dict(),
            calculated_at=datetime.now(),
            valid_until=valid_until,
            data_version=1
        )
        
        result = await session.execute(stmt)
        
        if result.rowcount == 0:
            # Insert new cache entry
            cache_entry = RefereeAnalyticsCacheModel(
                referee_id=referee_id,
                metrics_json=metrics.to_dict(),
                calculated_at=datetime.now(),
                valid_until=valid_until,
                data_version=1
            )
            session.add(cache_entry)
    
    async def _store_historical_metrics(
        self,
        session: AsyncSession,
        referee_id: UUID,
        metrics: RefereeMetrics
    ) -> None:
        """Store daily historical metrics"""
        today = date.today()
        
        # Try to update existing entry for today
        stmt = update(RefereeMetricsHistoryModel).where(
            and_(
                RefereeMetricsHistoryModel.referee_id == referee_id,
                RefereeMetricsHistoryModel.metric_date == today
            )
        ).values(
            overall_score=metrics.get_overall_score() / 10,  # Normalize to 0-1
            speed_score=1 - (metrics.time_metrics.avg_review_time / 30),
            quality_score=metrics.quality_metrics.get_overall_quality() / 10,
            reliability_score=metrics.reliability_metrics.get_reliability_score(),
            expertise_score=metrics.expertise_metrics.get_expertise_score(),
            current_reviews=metrics.workload_metrics.current_reviews,
            monthly_average=metrics.workload_metrics.monthly_average,
            burnout_risk=metrics.workload_metrics.burnout_risk_score,
            speed_percentile=metrics.percentile_ranks.speed_percentile if metrics.percentile_ranks else None,
            quality_percentile=metrics.percentile_ranks.quality_percentile if metrics.percentile_ranks else None,
            reliability_percentile=metrics.percentile_ranks.reliability_percentile if metrics.percentile_ranks else None,
            overall_percentile=metrics.percentile_ranks.overall_percentile if metrics.percentile_ranks else None
        )
        
        result = await session.execute(stmt)
        
        if result.rowcount == 0:
            # Insert new historical entry
            history_entry = RefereeMetricsHistoryModel(
                referee_id=referee_id,
                metric_date=today,
                overall_score=metrics.get_overall_score() / 10,
                speed_score=1 - (metrics.time_metrics.avg_review_time / 30),
                quality_score=metrics.quality_metrics.get_overall_quality() / 10,
                reliability_score=metrics.reliability_metrics.get_reliability_score(),
                expertise_score=metrics.expertise_metrics.get_expertise_score(),
                current_reviews=metrics.workload_metrics.current_reviews,
                monthly_average=metrics.workload_metrics.monthly_average,
                burnout_risk=metrics.workload_metrics.burnout_risk_score,
                speed_percentile=metrics.percentile_ranks.speed_percentile if metrics.percentile_ranks else None,
                quality_percentile=metrics.percentile_ranks.quality_percentile if metrics.percentile_ranks else None,
                reliability_percentile=metrics.percentile_ranks.reliability_percentile if metrics.percentile_ranks else None,
                overall_percentile=metrics.percentile_ranks.overall_percentile if metrics.percentile_ranks else None
            )
            session.add(history_entry)
    
    async def _update_journal_metrics(
        self,
        session: AsyncSession,
        referee_id: UUID,
        journal_metrics: Dict[str, JournalSpecificMetrics]
    ) -> None:
        """Update journal-specific metrics"""
        for journal_code, metrics in journal_metrics.items():
            stmt = update(JournalSpecificMetricsModel).where(
                and_(
                    JournalSpecificMetricsModel.referee_id == referee_id,
                    JournalSpecificMetricsModel.journal_code == journal_code
                )
            ).values(
                reviews_completed=metrics.reviews_completed,
                acceptance_rate=metrics.acceptance_rate,
                avg_quality_score=metrics.avg_quality_score,
                avg_review_time_days=metrics.avg_review_time,
                familiarity_score=metrics.familiarity_score,
                last_review_date=datetime.now(),
                updated_at=datetime.now()
            )
            
            result = await session.execute(stmt)
            
            if result.rowcount == 0:
                # Insert new journal metrics
                journal_metric = JournalSpecificMetricsModel(
                    referee_id=referee_id,
                    journal_code=journal_code,
                    reviews_completed=metrics.reviews_completed,
                    acceptance_rate=metrics.acceptance_rate,
                    avg_quality_score=metrics.avg_quality_score,
                    avg_review_time_days=metrics.avg_review_time,
                    familiarity_score=metrics.familiarity_score,
                    first_review_date=datetime.now(),
                    last_review_date=datetime.now()
                )
                session.add(journal_metric)
    
    def _calculate_trend_direction(self, scores: List[float]) -> str:
        """Calculate trend direction from scores"""
        if len(scores) < 2:
            return "insufficient_data"
        
        # Simple linear regression
        import numpy as np
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        
        if slope > 0.01:
            return "improving"
        elif slope < -0.01:
            return "declining"
        else:
            return "stable"
    
    def _serialize_metrics_for_cache(self, metrics: RefereeMetrics) -> Dict[str, Any]:
        """Serialize metrics for caching"""
        return metrics.to_dict()
    
    def _deserialize_metrics_from_cache(self, cached_data: Dict[str, Any]) -> RefereeMetrics:
        """Deserialize metrics from cache"""
        # This would need full implementation based on cached structure
        # For now, return a simplified version
        return self._deserialize_metrics_from_json(cached_data)
    
    def _deserialize_metrics_from_json(self, metrics_json: Dict[str, Any]) -> RefereeMetrics:
        """Convert JSON metrics to domain model"""
        # This is a simplified version - would need full deserialization logic
        # For now, return basic structure with placeholder data
        
        time_metrics = TimeMetrics(
            avg_response_time=metrics_json.get('time_metrics', {}).get('avg_response_time', 7.0),
            avg_review_time=metrics_json.get('time_metrics', {}).get('avg_review_time', 21.0),
            fastest_review=0,
            slowest_review=0,
            response_time_std=0,
            review_time_std=0,
            on_time_rate=metrics_json.get('time_metrics', {}).get('on_time_rate', 0.8)
        )
        
        quality_metrics = QualityMetrics(
            avg_quality_score=metrics_json.get('quality_metrics', {}).get('avg_quality_score', 7.0),
            quality_consistency=0,
            report_thoroughness=0.7,
            constructiveness_score=0.7,
            technical_accuracy=0.8,
            clarity_score=8.0,
            actionability_score=7.5
        )
        
        workload_metrics = WorkloadMetrics(
            current_reviews=metrics_json.get('workload_metrics', {}).get('current_reviews', 0),
            completed_reviews_30d=0,
            completed_reviews_90d=0,
            completed_reviews_365d=0,
            monthly_average=0,
            peak_capacity=3,
            availability_score=0.8,
            burnout_risk_score=0.2
        )
        
        reliability_metrics = ReliabilityMetrics(
            acceptance_rate=0.7,
            completion_rate=0.9,
            ghost_rate=0.1,
            decline_after_accept_rate=0.05,
            reminder_effectiveness=0.8,
            communication_score=0.8,
            excuse_frequency=0.1
        )
        
        expertise_metrics = ExpertiseMetrics(
            h_index=metrics_json.get('expertise_metrics', {}).get('h_index'),
            years_experience=metrics_json.get('expertise_metrics', {}).get('years_experience', 5)
        )
        
        return RefereeMetrics(
            referee_id=metrics_json['referee_id'],
            name=metrics_json['name'],
            email=metrics_json['email'],
            institution=metrics_json['institution'],
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics,
            last_updated=datetime.fromisoformat(metrics_json['last_updated'])
        )