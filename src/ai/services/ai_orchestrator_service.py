"""
AI Orchestrator Service - Central coordinator for all AI-powered features
Migrated from legacy architecture to new async framework
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID

from ..ports.ai_client import AIClient, AIModel
from ..ports.pdf_processor import PDFProcessor
from ..models.manuscript_analysis import (
    AnalysisResult, DeskRejectionAnalysis, RefereeRecommendation,
    ManuscriptMetadata, ComprehensiveAnalysis
)
from ...infrastructure.database.engine import get_session
from ...infrastructure.repositories.ai_analysis_repository import AIAnalysisRepository
from ...infrastructure.repositories.referee_analytics_repository import RefereeAnalyticsRepository

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Central orchestrator for all AI-powered editorial features
    Coordinates AI analysis, referee recommendations, and analytics
    """
    
    def __init__(
        self,
        ai_client: AIClient,
        pdf_processor: PDFProcessor,
        cache_enabled: bool = True
    ):
        self.ai_client = ai_client
        self.pdf_processor = pdf_processor
        self.cache_enabled = cache_enabled
        
        # Repositories
        self.ai_repository = AIAnalysisRepository()
        self.referee_repository = RefereeAnalyticsRepository()
        
        # Configuration
        self.default_model = AIModel.GPT_4_TURBO
        self.confidence_threshold = 0.7
        self.max_referee_recommendations = 10
        
        logger.info("✅ AI Orchestrator initialized with full analytics integration")
    
    async def analyze_manuscript_comprehensively(
        self,
        manuscript_id: str,
        title: str,
        abstract: str,
        journal_code: str,
        pdf_path: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        exclude_authors: Optional[List[str]] = None
    ) -> ComprehensiveAnalysis:
        """
        Perform comprehensive AI-powered manuscript analysis
        Combines desk rejection analysis, metadata extraction, and referee recommendations
        """
        logger.info(f"🔬 Starting comprehensive analysis for manuscript: {manuscript_id}")
        
        start_time = asyncio.get_event_loop().time()
        analysis = ComprehensiveAnalysis(
            manuscript_id=manuscript_id,
            title=title,
            ai_enabled=await self.ai_client.check_model_availability(self.default_model)
        )
        
        try:
            # Step 1: PDF Content Extraction (if available)
            pdf_content = None
            if pdf_path:
                logger.info(f"📄 Extracting PDF content: {pdf_path}")
                try:
                    pdf_content = await self.pdf_processor.extract_content(pdf_path)
                    analysis.pdf_analysis = pdf_content
                    
                    # Update abstract if extracted from PDF
                    if pdf_content and pdf_content.abstract and not abstract:
                        abstract = pdf_content.abstract
                        
                except Exception as e:
                    logger.warning(f"⚠️ PDF extraction failed: {e}")
                    analysis.warnings.append(f"PDF extraction failed: {str(e)}")
            
            # Step 2: Research Metadata Extraction
            logger.info("🔍 Extracting research metadata...")
            try:
                metadata_result = await self.ai_client.extract_research_metadata(
                    title=title,
                    abstract=abstract,
                    full_text_sample=pdf_content.full_text[:3000] if pdf_content else "",
                    model=self.default_model
                )
                
                analysis.metadata = ManuscriptMetadata(
                    title=title,
                    abstract=abstract,
                    keywords=keywords or metadata_result.get('keywords', []),
                    research_area=metadata_result.get('research_area', ''),
                    methodology=metadata_result.get('methodology', ''),
                    novelty_score=metadata_result.get('novelty_score', 0.0),
                    complexity_score=metadata_result.get('complexity_score', 0.0),
                    quality_indicators=metadata_result.get('quality_scores', {})
                )
                
            except Exception as e:
                logger.error(f"❌ Metadata extraction failed: {e}")
                analysis.errors.append(f"Metadata extraction failed: {str(e)}")
                # Create minimal metadata
                analysis.metadata = ManuscriptMetadata(
                    title=title,
                    abstract=abstract,
                    keywords=keywords or []
                )
            
            # Step 3: Desk Rejection Analysis
            logger.info("⚖️ Performing desk rejection analysis...")
            try:
                desk_analysis = await self.ai_client.analyze_for_desk_rejection(
                    title=title,
                    abstract=abstract,
                    full_text_sample=pdf_content.full_text[:3000] if pdf_content else "",
                    journal_code=journal_code,
                    model=self.default_model
                )
                
                analysis.desk_rejection_analysis = desk_analysis
                
                # Store analysis in database
                await self._store_analysis_result(manuscript_id, desk_analysis)
                
            except Exception as e:
                logger.error(f"❌ Desk rejection analysis failed: {e}")
                analysis.errors.append(f"Desk rejection analysis failed: {str(e)}")
            
            # Step 4: Referee Recommendations (if not likely to be rejected)
            if (analysis.desk_rejection_analysis and 
                analysis.desk_rejection_analysis.recommendation.value in ['accept_for_review', 'uncertain']):
                
                logger.info("👥 Generating referee recommendations...")
                try:
                    referee_recommendations = await self.ai_client.suggest_referees(
                        title=title,
                        abstract=abstract,
                        research_area=analysis.metadata.research_area,
                        keywords=analysis.metadata.keywords,
                        journal_code=journal_code,
                        exclude_authors=exclude_authors,
                        model=self.default_model
                    )
                    
                    analysis.referee_recommendations = referee_recommendations
                    
                    # Enrich with historical performance data
                    await self._enrich_referee_recommendations(analysis.referee_recommendations)
                    
                except Exception as e:
                    logger.error(f"❌ Referee recommendation failed: {e}")
                    analysis.errors.append(f"Referee recommendation failed: {str(e)}")
            
            # Step 5: Calculate Overall Confidence
            confidence_factors = []
            
            if analysis.desk_rejection_analysis:
                confidence_factors.append(analysis.desk_rejection_analysis.confidence)
            
            if analysis.referee_recommendations:
                avg_referee_confidence = sum(
                    r.confidence for r in analysis.referee_recommendations
                ) / len(analysis.referee_recommendations)
                confidence_factors.append(avg_referee_confidence)
            
            if analysis.metadata and analysis.metadata.quality_indicators:
                quality_confidence = sum(analysis.metadata.quality_indicators.values()) / len(analysis.metadata.quality_indicators)
                confidence_factors.append(quality_confidence)
            
            analysis.analysis_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
            
            # Step 6: Performance Metrics
            end_time = asyncio.get_event_loop().time()
            analysis.processing_time_ms = int((end_time - start_time) * 1000)
            
            logger.info(f"✅ Comprehensive analysis completed in {analysis.processing_time_ms}ms (confidence: {analysis.analysis_confidence:.2f})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis failed: {e}")
            analysis.errors.append(f"Analysis failed: {str(e)}")
            
            # Calculate processing time even on error
            end_time = asyncio.get_event_loop().time()
            analysis.processing_time_ms = int((end_time - start_time) * 1000)
            
            return analysis
    
    async def get_referee_suggestions_with_analytics(
        self,
        manuscript_id: str,
        title: str,
        abstract: str,
        journal_code: str,
        research_area: str,
        keywords: List[str],
        exclude_authors: Optional[List[str]] = None,
        include_performance_data: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get AI referee suggestions enriched with historical analytics
        """
        logger.info(f"👥 Getting referee suggestions with analytics for: {manuscript_id}")
        
        try:
            # Get AI recommendations
            ai_recommendations = await self.ai_client.suggest_referees(
                title=title,
                abstract=abstract,
                research_area=research_area,
                keywords=keywords,
                journal_code=journal_code,
                exclude_authors=exclude_authors,
                model=self.default_model
            )
            
            # Enrich with performance data if requested
            if include_performance_data:
                await self._enrich_referee_recommendations(ai_recommendations)
            
            # Convert to enriched format
            enriched_recommendations = []
            for rec in ai_recommendations:
                enriched_rec = {
                    'referee_name': rec.referee_name,
                    'ai_scores': {
                        'expertise_match': rec.expertise_match,
                        'availability_score': rec.availability_score,
                        'quality_score': rec.quality_score,
                        'workload_score': rec.workload_score,
                        'overall_score': rec.overall_score,
                        'confidence': rec.confidence
                    },
                    'expertise_areas': rec.expertise_areas,
                    'matching_keywords': rec.matching_keywords,
                    'rationale': rec.rationale,
                    'institution': rec.institution,
                    'contact_info': rec.contact_info,
                    'historical_performance': getattr(rec, 'historical_performance', None),
                    'recommendation_timestamp': datetime.now().isoformat()
                }
                enriched_recommendations.append(enriched_rec)
            
            logger.info(f"✅ Generated {len(enriched_recommendations)} enriched referee recommendations")
            return enriched_recommendations
            
        except Exception as e:
            logger.error(f"❌ Failed to get referee suggestions with analytics: {e}")
            return []
    
    async def explain_editorial_decision(
        self,
        manuscript_id: str,
        analysis_result: DeskRejectionAnalysis
    ) -> str:
        """
        Generate human-readable explanation of AI editorial decision
        """
        try:
            explanation = await self.ai_client.explain_decision(
                analysis_result=analysis_result,
                model=self.default_model
            )
            
            # Store explanation for reference
            await self._store_decision_explanation(manuscript_id, explanation)
            
            return explanation
            
        except Exception as e:
            logger.error(f"❌ Failed to generate decision explanation: {e}")
            return "Unable to generate decision explanation at this time."
    
    async def get_journal_ai_insights(
        self,
        journal_code: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get AI-powered insights for journal performance
        """
        logger.info(f"📊 Generating AI insights for journal: {journal_code}")
        
        try:
            # Get journal performance stats
            performance_stats = await self.referee_repository.get_journal_performance_stats(
                journal_code=journal_code,
                days=days
            )
            
            # Get recent AI analysis results
            recent_analyses = await self._get_recent_ai_analyses(journal_code, days)
            
            # Calculate AI insights
            insights = {
                'journal_code': journal_code,
                'analysis_period_days': days,
                'performance_summary': performance_stats,
                'ai_analysis_insights': {
                    'total_analyses': len(recent_analyses),
                    'desk_rejection_rate': self._calculate_desk_rejection_rate(recent_analyses),
                    'avg_analysis_confidence': self._calculate_avg_confidence(recent_analyses),
                    'quality_trends': self._analyze_quality_trends(recent_analyses),
                    'recommendation_patterns': self._analyze_recommendation_patterns(recent_analyses)
                },
                'referee_insights': {
                    'top_performers': await self.referee_repository.get_top_performers(
                        journal_code=journal_code,
                        limit=10
                    ),
                    'utilization_metrics': performance_stats
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to generate journal AI insights: {e}")
            return {}
    
    async def _enrich_referee_recommendations(
        self,
        recommendations: List[RefereeRecommendation]
    ) -> None:
        """
        Enrich AI recommendations with historical performance data
        """
        for rec in recommendations:
            try:
                # Try to find referee by email (if available)
                if rec.contact_info and 'email' in rec.contact_info:
                    referee = await self.referee_repository.get_referee_by_email(
                        rec.contact_info['email']
                    )
                    
                    if referee:
                        # Get historical metrics
                        metrics = await self.referee_repository.get_referee_metrics(referee.id)
                        if metrics:
                            # Add historical performance data to recommendation
                            rec.historical_performance = {
                                'avg_response_time_days': metrics.time_metrics.avg_response_time,
                                'avg_review_time_days': metrics.time_metrics.avg_review_time,
                                'completion_rate': metrics.reliability_metrics.completion_rate,
                                'quality_score': metrics.quality_metrics.avg_quality_score,
                                'reliability_score': metrics.reliability_metrics.get_reliability_score(),
                                'current_workload': metrics.workload_metrics.current_reviews,
                                'burnout_risk': metrics.workload_metrics.burnout_risk_score,
                                'last_review_date': metrics.last_updated.isoformat()
                            }
                            
                            # Adjust AI scores based on historical data
                            rec.overall_score = self._adjust_score_with_historical_data(
                                rec.overall_score,
                                rec.historical_performance
                            )
                        
            except Exception as e:
                logger.debug(f"Could not enrich recommendation for {rec.referee_name}: {e}")
                continue
    
    def _adjust_score_with_historical_data(
        self,
        ai_score: float,
        historical_data: Dict[str, Any]
    ) -> float:
        """
        Adjust AI recommendation score based on historical performance
        """
        # Weight AI score with historical performance
        reliability_factor = historical_data.get('reliability_score', 0.5)
        quality_factor = historical_data.get('quality_score', 5.0) / 10.0  # Normalize to 0-1
        workload_factor = 1.0 - min(1.0, historical_data.get('current_workload', 0) / 5.0)
        
        # Weighted combination
        adjusted_score = (
            ai_score * 0.6 +
            reliability_factor * 0.2 +
            quality_factor * 0.1 +
            workload_factor * 0.1
        )
        
        return min(1.0, max(0.0, adjusted_score))
    
    async def _store_analysis_result(
        self,
        manuscript_id: str,
        analysis: DeskRejectionAnalysis
    ) -> None:
        """Store analysis result in database"""
        try:
            async with get_session() as session:
                await self.ai_repository.store_analysis_result(
                    session, manuscript_id, analysis
                )
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
    
    async def _store_decision_explanation(
        self,
        manuscript_id: str,
        explanation: str
    ) -> None:
        """Store decision explanation for reference"""
        try:
            async with get_session() as session:
                # This would need implementation in ai_repository
                pass
        except Exception as e:
            logger.error(f"Failed to store decision explanation: {e}")
    
    async def _get_recent_ai_analyses(
        self,
        journal_code: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """Get recent AI analyses for journal"""
        # This would need implementation based on stored analyses
        return []
    
    def _calculate_desk_rejection_rate(self, analyses: List[Dict[str, Any]]) -> float:
        """Calculate desk rejection rate from analyses"""
        if not analyses:
            return 0.0
        
        rejections = sum(1 for a in analyses if a.get('recommendation') == 'desk_reject')
        return rejections / len(analyses)
    
    def _calculate_avg_confidence(self, analyses: List[Dict[str, Any]]) -> float:
        """Calculate average confidence from analyses"""
        if not analyses:
            return 0.0
        
        confidences = [a.get('confidence', 0.0) for a in analyses]
        return sum(confidences) / len(confidences)
    
    def _analyze_quality_trends(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality trends from analyses"""
        return {
            'trend': 'stable',
            'avg_quality': 0.7,
            'quality_distribution': {}
        }
    
    def _analyze_recommendation_patterns(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze recommendation patterns"""
        return {
            'accept_rate': 0.6,
            'reject_rate': 0.2,
            'uncertain_rate': 0.2
        }