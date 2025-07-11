"""
AI Analysis Repository Implementation
Stores and retrieves AI analysis results in PostgreSQL
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.domain.ports import CacheService
from ...ai.models.manuscript_analysis import (
    AnalysisResult, DeskRejectionAnalysis, RefereeRecommendation,
    QualityIssue, ManuscriptMetadata, AnalysisRecommendation, QualityIssueType
)
from ..database.engine import get_session
from ..database.ai_models import (
    AIAnalysisModel, AIRefereeRecommendationModel, 
    AIQualityIssueModel, AIUsageStatsModel, AIModelPerformanceModel
)

logger = logging.getLogger(__name__)


class AIAnalysisRepository:
    """Repository for AI analysis results with caching and performance tracking"""
    
    def __init__(self, cache: Optional[CacheService] = None):
        self.cache = cache
        self.cache_ttl_seconds = 3600 * 24  # 24 hours
    
    async def save_analysis(self, analysis: AnalysisResult) -> UUID:
        """Save complete AI analysis to database"""
        try:
            async with get_session() as session:
                # Create main analysis record
                ai_analysis = AIAnalysisModel(
                    id=analysis.id,
                    manuscript_id=analysis.manuscript_id,
                    journal_code=analysis.journal_code,
                    analysis_timestamp=analysis.analysis_timestamp,
                    processing_time_seconds=analysis.processing_time_seconds,
                    ai_model_versions=analysis.ai_model_versions,
                    content_hash=analysis.content_hash,
                    pdf_path=analysis.pdf_path,
                    text_extracted=analysis.text_extracted,
                    analysis_quality=analysis.analysis_quality,
                    
                    # Serialize complex objects to JSON
                    desk_rejection_analysis=self._serialize_desk_rejection(analysis.desk_rejection_analysis),
                    manuscript_metadata=self._serialize_metadata(analysis.metadata),
                    
                    human_validated=analysis.human_validated,
                    validation_notes=analysis.validation_notes,
                    validation_timestamp=analysis.validation_timestamp
                )
                
                session.add(ai_analysis)
                await session.flush()  # Get the ID
                
                # Save referee recommendations
                for rec in analysis.referee_recommendations:
                    rec_model = AIRefereeRecommendationModel(
                        analysis_id=analysis.id,
                        referee_name=rec.referee_name,
                        expertise_match=rec.expertise_match,
                        availability_score=rec.availability_score,
                        quality_score=rec.quality_score,
                        workload_score=rec.workload_score,
                        overall_score=rec.overall_score,
                        confidence=rec.confidence,
                        expertise_areas=rec.expertise_areas,
                        matching_keywords=rec.matching_keywords,
                        contact_info=rec.contact_info,
                        rationale=rec.rationale,
                        institution=rec.institution,
                        recent_publications=rec.recent_publications,
                        historical_response_rate=rec.historical_response_rate,
                        average_review_time_days=rec.average_review_time_days,
                        review_quality_rating=rec.review_quality_rating
                    )
                    session.add(rec_model)
                
                # Save quality issues
                for issue in analysis.desk_rejection_analysis.quality_issues:
                    issue_model = AIQualityIssueModel(
                        analysis_id=analysis.id,
                        issue_type=issue.issue_type,
                        severity=issue.severity,
                        description=issue.description,
                        location=issue.location,
                        suggestion=issue.suggestion
                    )
                    session.add(issue_model)
                
                await session.commit()
                
                # Update cache
                if self.cache:
                    await self.cache.set(
                        f"ai_analysis:{analysis.id}",
                        self._serialize_analysis_for_cache(analysis),
                        ttl=self.cache_ttl_seconds
                    )
                
                logger.info(f"✅ Saved AI analysis {analysis.id} for manuscript {analysis.manuscript_id}")
                return analysis.id
                
        except Exception as e:
            logger.error(f"❌ Failed to save AI analysis: {e}")
            raise
    
    async def get_analysis_by_id(self, analysis_id: UUID) -> Optional[AnalysisResult]:
        """Get AI analysis by ID"""
        try:
            # Check cache first
            if self.cache:
                cached = await self.cache.get(f"ai_analysis:{analysis_id}")
                if cached:
                    return self._deserialize_analysis_from_cache(cached)
            
            # Query database
            async with get_session() as session:
                stmt = select(AIAnalysisModel).options(
                    selectinload(AIAnalysisModel.referee_recommendations),
                    selectinload(AIAnalysisModel.quality_issues)
                ).where(AIAnalysisModel.id == analysis_id)
                
                result = await session.execute(stmt)
                ai_analysis = result.scalar_one_or_none()
                
                if not ai_analysis:
                    return None
                
                return self._deserialize_analysis(ai_analysis)
                
        except Exception as e:
            logger.error(f"❌ Failed to get AI analysis {analysis_id}: {e}")
            return None
    
    async def get_analyses_by_manuscript(self, manuscript_id: str) -> List[AnalysisResult]:
        """Get all AI analyses for a manuscript"""
        try:
            async with get_session() as session:
                stmt = select(AIAnalysisModel).options(
                    selectinload(AIAnalysisModel.referee_recommendations),
                    selectinload(AIAnalysisModel.quality_issues)
                ).where(
                    AIAnalysisModel.manuscript_id == manuscript_id
                ).order_by(AIAnalysisModel.analysis_timestamp.desc())
                
                result = await session.execute(stmt)
                ai_analyses = result.scalars().all()
                
                return [self._deserialize_analysis(analysis) for analysis in ai_analyses]
                
        except Exception as e:
            logger.error(f"❌ Failed to get analyses for manuscript {manuscript_id}: {e}")
            return []
    
    async def get_recent_analyses(
        self, 
        journal_code: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AnalysisResult]:
        """Get recent AI analyses"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            async with get_session() as session:
                stmt = select(AIAnalysisModel).options(
                    selectinload(AIAnalysisModel.referee_recommendations),
                    selectinload(AIAnalysisModel.quality_issues)
                ).where(AIAnalysisModel.analysis_timestamp >= since)
                
                if journal_code:
                    stmt = stmt.where(AIAnalysisModel.journal_code == journal_code)
                
                stmt = stmt.order_by(AIAnalysisModel.analysis_timestamp.desc()).limit(limit)
                
                result = await session.execute(stmt)
                ai_analyses = result.scalars().all()
                
                return [self._deserialize_analysis(analysis) for analysis in ai_analyses]
                
        except Exception as e:
            logger.error(f"❌ Failed to get recent analyses: {e}")
            return []
    
    async def update_validation(
        self,
        analysis_id: UUID,
        validated: bool,
        notes: str,
        validator_id: str
    ) -> bool:
        """Update human validation status"""
        try:
            async with get_session() as session:
                stmt = update(AIAnalysisModel).where(
                    AIAnalysisModel.id == analysis_id
                ).values(
                    human_validated=validated,
                    validation_notes=notes,
                    validation_timestamp=datetime.now(),
                    validation_user_id=validator_id,
                    updated_at=datetime.now()
                )
                
                await session.execute(stmt)
                await session.commit()
                
                # Invalidate cache
                if self.cache:
                    await self.cache.delete(f"ai_analysis:{analysis_id}")
                
                logger.info(f"✅ Updated validation for analysis {analysis_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update validation: {e}")
            return False
    
    async def get_performance_stats(
        self,
        journal_code: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get AI performance statistics"""
        try:
            since = datetime.now() - timedelta(days=days)
            
            async with get_session() as session:
                # Base query
                base_query = select(AIAnalysisModel).where(
                    AIAnalysisModel.analysis_timestamp >= since
                )
                
                if journal_code:
                    base_query = base_query.where(AIAnalysisModel.journal_code == journal_code)
                
                # Total analyses
                total_result = await session.execute(
                    select(func.count()).select_from(base_query.subquery())
                )
                total_analyses = total_result.scalar()
                
                # Validated analyses
                validated_result = await session.execute(
                    select(func.count()).select_from(
                        base_query.where(AIAnalysisModel.human_validated == True).subquery()
                    )
                )
                validated_count = validated_result.scalar()
                
                # Average processing time
                avg_time_result = await session.execute(
                    select(func.avg(AIAnalysisModel.processing_time_seconds)).select_from(
                        base_query.subquery()
                    )
                )
                avg_processing_time = avg_time_result.scalar() or 0
                
                # Quality distribution
                quality_result = await session.execute(
                    select(func.avg(AIAnalysisModel.analysis_quality)).select_from(
                        base_query.subquery()
                    )
                )
                avg_quality = quality_result.scalar() or 0
                
                return {
                    'period_days': days,
                    'journal_code': journal_code,
                    'total_analyses': total_analyses,
                    'validated_analyses': validated_count,
                    'validation_rate': validated_count / total_analyses if total_analyses > 0 else 0,
                    'avg_processing_time_seconds': float(avg_processing_time),
                    'avg_analysis_quality': float(avg_quality),
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get performance stats: {e}")
            return {}
    
    async def record_usage(
        self,
        service_type: str,
        operation: str,
        model_name: str,
        processing_time_ms: float,
        success: bool,
        journal_code: Optional[str] = None,
        tokens_used: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Record AI service usage for analytics"""
        try:
            async with get_session() as session:
                usage_stat = AIUsageStatsModel(
                    date=datetime.now(),
                    service_type=service_type,
                    operation=operation,
                    model_name=model_name,
                    processing_time_ms=processing_time_ms,
                    success=success,
                    journal_code=journal_code,
                    tokens_used=tokens_used,
                    estimated_cost_usd=estimated_cost_usd,
                    error_message=error_message
                )
                
                session.add(usage_stat)
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to record usage: {e}")
    
    def _serialize_desk_rejection(self, analysis: DeskRejectionAnalysis) -> Dict[str, Any]:
        """Serialize desk rejection analysis to JSON"""
        return {
            'id': str(analysis.id),
            'recommendation': analysis.recommendation.value,
            'confidence': analysis.confidence,
            'overall_score': analysis.overall_score,
            'rejection_reasons': analysis.rejection_reasons,
            'scope_issues': analysis.scope_issues,
            'technical_issues': analysis.technical_issues,
            'model_version': analysis.model_version,
            'analysis_timestamp': analysis.analysis_timestamp.isoformat(),
            'processing_time_seconds': analysis.processing_time_seconds,
            'recommendation_summary': analysis.recommendation_summary,
            'detailed_explanation': analysis.detailed_explanation
        }
    
    def _serialize_metadata(self, metadata: ManuscriptMetadata) -> Dict[str, Any]:
        """Serialize manuscript metadata to JSON"""
        return {
            'title': metadata.title,
            'abstract': metadata.abstract,
            'keywords': metadata.keywords,
            'research_area': metadata.research_area,
            'methodology': metadata.methodology,
            'complexity_score': metadata.complexity_score,
            'novelty_score': metadata.novelty_score,
            'technical_quality_score': metadata.technical_quality_score,
            'presentation_quality_score': metadata.presentation_quality_score,
            'scope_fit_score': metadata.scope_fit_score,
            'quality_indicators': metadata.quality_indicators
        }
    
    def _serialize_analysis_for_cache(self, analysis: AnalysisResult) -> Dict[str, Any]:
        """Serialize complete analysis for caching"""
        return {
            'id': str(analysis.id),
            'manuscript_id': analysis.manuscript_id,
            'journal_code': analysis.journal_code,
            'desk_rejection_analysis': self._serialize_desk_rejection(analysis.desk_rejection_analysis),
            'manuscript_metadata': self._serialize_metadata(analysis.metadata),
            # Add other fields as needed for cache
        }
    
    def _deserialize_analysis(self, ai_analysis: AIAnalysisModel) -> AnalysisResult:
        """Convert database model to domain model"""
        # This is a simplified version - would need full deserialization logic
        # For now, return a basic structure
        
        # Deserialize desk rejection analysis
        desk_data = ai_analysis.desk_rejection_analysis
        desk_analysis = DeskRejectionAnalysis(
            recommendation=AnalysisRecommendation(desk_data['recommendation']),
            confidence=desk_data['confidence'],
            overall_score=desk_data['overall_score'],
            rejection_reasons=desk_data.get('rejection_reasons', []),
            scope_issues=desk_data.get('scope_issues', []),
            technical_issues=desk_data.get('technical_issues', []),
            model_version=desk_data.get('model_version', ''),
            recommendation_summary=desk_data.get('recommendation_summary', ''),
            detailed_explanation=desk_data.get('detailed_explanation', '')
        )
        
        # Deserialize metadata
        meta_data = ai_analysis.manuscript_metadata
        metadata = ManuscriptMetadata(
            title=meta_data['title'],
            abstract=meta_data['abstract'],
            keywords=meta_data.get('keywords', []),
            research_area=meta_data.get('research_area', ''),
            methodology=meta_data.get('methodology', ''),
            complexity_score=meta_data.get('complexity_score', 0.0),
            novelty_score=meta_data.get('novelty_score', 0.0),
            technical_quality_score=meta_data.get('technical_quality_score', 0.0),
            presentation_quality_score=meta_data.get('presentation_quality_score', 0.0),
            scope_fit_score=meta_data.get('scope_fit_score', 0.0),
            quality_indicators=meta_data.get('quality_indicators', {})
        )
        
        # Convert referee recommendations
        referee_recommendations = []
        for rec_model in ai_analysis.referee_recommendations:
            rec = RefereeRecommendation(
                referee_name=rec_model.referee_name,
                expertise_match=rec_model.expertise_match,
                availability_score=rec_model.availability_score,
                quality_score=rec_model.quality_score,
                workload_score=rec_model.workload_score,
                overall_score=rec_model.overall_score,
                expertise_areas=rec_model.expertise_areas,
                matching_keywords=rec_model.matching_keywords,
                rationale=rec_model.rationale,
                confidence=rec_model.confidence,
                contact_info=rec_model.contact_info,
                institution=rec_model.institution,
                recent_publications=rec_model.recent_publications,
                historical_response_rate=rec_model.historical_response_rate,
                average_review_time_days=rec_model.average_review_time_days,
                review_quality_rating=rec_model.review_quality_rating
            )
            referee_recommendations.append(rec)
        
        return AnalysisResult(
            manuscript_id=ai_analysis.manuscript_id,
            journal_code=ai_analysis.journal_code,
            metadata=metadata,
            desk_rejection_analysis=desk_analysis,
            id=ai_analysis.id,
            referee_recommendations=referee_recommendations,
            analysis_timestamp=ai_analysis.analysis_timestamp,
            processing_time_seconds=ai_analysis.processing_time_seconds,
            ai_model_versions=ai_analysis.ai_model_versions,
            content_hash=ai_analysis.content_hash or "",
            pdf_path=ai_analysis.pdf_path,
            text_extracted=ai_analysis.text_extracted,
            analysis_quality=ai_analysis.analysis_quality,
            human_validated=ai_analysis.human_validated,
            validation_notes=ai_analysis.validation_notes,
            validation_timestamp=ai_analysis.validation_timestamp
        )
    
    def _deserialize_analysis_from_cache(self, cached_data: Dict[str, Any]) -> AnalysisResult:
        """Deserialize analysis from cache (simplified version)"""
        # This would need full implementation based on cached structure
        pass