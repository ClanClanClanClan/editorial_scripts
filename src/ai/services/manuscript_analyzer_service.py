"""
Async AI-powered manuscript analysis service - migrated to new architecture
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..ports.manuscript_analyzer import ManuscriptAnalyzerPort
from ..ports.ai_client import AIClient  
from ..ports.pdf_processor import PDFProcessor
from ..models.manuscript_analysis import (
    ManuscriptAnalysisRequest, 
    DeskRejectionAnalysis, 
    RefereeRecommendation
)
from ...infrastructure.database.engine import get_session
from ...infrastructure.repositories.ai_analysis_repository import AIAnalysisRepository

logger = logging.getLogger(__name__)


class AsyncManuscriptAnalyzerService:
    """
    Async AI-powered manuscript analyzer service
    Migrated from legacy core/ai_manuscript_analyzer.py to new architecture
    """
    
    def __init__(
        self,
        ai_client: AIClientPort,
        pdf_processor: PDFProcessorPort,
        cache_enabled: bool = True
    ):
        self.ai_client = ai_client
        self.pdf_processor = pdf_processor
        self.cache_enabled = cache_enabled
        self.ai_repository = AIAnalysisRepository()
        
        # Analysis thresholds
        self.desk_rejection_threshold = 0.3
        self.acceptance_threshold = 0.7
        
        logger.info("✅ AsyncManuscriptAnalyzerService initialized")
    
    async def analyze_manuscript_for_desk_rejection(
        self,
        request: ManuscriptAnalysisRequest
    ) -> DeskRejectionAnalysis:
        """
        Analyze manuscript for desk rejection decision with async operations
        """
        logger.info(f"🔍 Starting desk rejection analysis for: {request.title[:50]}...")
        
        try:
            # Check cache first
            if self.cache_enabled:
                cached_result = await self._get_cached_analysis(request, "desk_rejection")
                if cached_result:
                    logger.info("📋 Using cached desk rejection analysis")
                    return cached_result
            
            # Extract PDF content if available
            pdf_content = None
            if request.pdf_path and Path(request.pdf_path).exists():
                logger.info(f"📄 Extracting PDF content: {request.pdf_path}")
                pdf_content = await self.pdf_processor.extract_content(request.pdf_path)
            
            # Perform AI analysis
            if await self.ai_client.is_available():
                analysis = await self._openai_desk_rejection_analysis(request, pdf_content)
            else:
                analysis = await self._fallback_desk_rejection_analysis(request, pdf_content)
            
            # Cache the results
            if self.cache_enabled:
                await self._cache_analysis(request, "desk_rejection", analysis)
            
            # Store in database
            await self._store_analysis_result(request, analysis)
            
            logger.info(f"✅ Desk rejection analysis completed: {analysis.recommendation} (confidence: {analysis.confidence:.2f})")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Desk rejection analysis failed: {e}")
            # Return fallback analysis on error
            return await self._fallback_desk_rejection_analysis(request, None)
    
    async def recommend_referees(
        self,
        request: ManuscriptAnalysisRequest,
        num_recommendations: int = 5
    ) -> List[RefereeRecommendation]:
        """
        Generate AI-powered referee recommendations
        """
        logger.info(f"👥 Generating {num_recommendations} referee recommendations for: {request.title[:50]}...")
        
        try:
            # Check cache first
            if self.cache_enabled:
                cached_result = await self._get_cached_analysis(request, "referee_recommendations")
                if cached_result:
                    logger.info("📋 Using cached referee recommendations")
                    return cached_result
            
            # Extract PDF content if available
            pdf_content = None
            if request.pdf_path and Path(request.pdf_path).exists():
                pdf_content = await self.pdf_processor.extract_content(request.pdf_path)
            
            # Perform AI analysis
            if await self.ai_client.is_available():
                recommendations = await self._openai_referee_recommendations(
                    request, pdf_content, num_recommendations
                )
            else:
                recommendations = await self._fallback_referee_recommendations(
                    request, pdf_content, num_recommendations
                )
            
            # Cache the results
            if self.cache_enabled:
                await self._cache_analysis(request, "referee_recommendations", recommendations)
            
            logger.info(f"✅ Generated {len(recommendations)} referee recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Referee recommendation failed: {e}")
            # Return fallback recommendations on error
            return await self._fallback_referee_recommendations(request, None, num_recommendations)
    
    async def analyze_manuscript_comprehensively(
        self,
        request: ManuscriptAnalysisRequest
    ) -> Dict[str, Any]:
        """
        Perform comprehensive manuscript analysis combining all AI features
        """
        logger.info(f"🔬 Starting comprehensive analysis for: {request.title[:50]}...")
        
        analysis_result = {
            'manuscript_id': request.manuscript_id,
            'title': request.title,
            'analysis_timestamp': datetime.now().isoformat(),
            'pdf_analysis': None,
            'desk_rejection_analysis': None,
            'referee_recommendations': [],
            'ai_enabled': await self.ai_client.is_available(),
            'analysis_confidence': 0.0,
            'processing_time_ms': 0
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Extract PDF content if available
            if request.pdf_path and Path(request.pdf_path).exists():
                logger.info(f"📄 Extracting PDF content: {request.pdf_path}")
                pdf_content = await self.pdf_processor.extract_content(request.pdf_path)
                analysis_result['pdf_analysis'] = pdf_content.dict() if pdf_content else None
            
            # Perform desk rejection analysis
            logger.info("🔍 Performing desk rejection analysis...")
            desk_analysis = await self.analyze_manuscript_for_desk_rejection(request)
            analysis_result['desk_rejection_analysis'] = desk_analysis.dict()
            
            # Generate referee recommendations if not likely to be rejected
            if desk_analysis.recommendation in ['accept', 'uncertain']:
                logger.info("👥 Generating referee recommendations...")
                referee_recs = await self.recommend_referees(request)
                analysis_result['referee_recommendations'] = [rec.dict() for rec in referee_recs]
            
            # Calculate overall confidence
            confidence_factors = [desk_analysis.confidence]
            if analysis_result['referee_recommendations']:
                avg_referee_confidence = sum(
                    rec['overall_score'] for rec in analysis_result['referee_recommendations']
                ) / len(analysis_result['referee_recommendations'])
                confidence_factors.append(avg_referee_confidence)
            
            analysis_result['analysis_confidence'] = sum(confidence_factors) / len(confidence_factors)
            
            # Calculate processing time
            end_time = asyncio.get_event_loop().time()
            analysis_result['processing_time_ms'] = int((end_time - start_time) * 1000)
            
            logger.info(f"✅ Comprehensive analysis completed in {analysis_result['processing_time_ms']}ms (confidence: {analysis_result['analysis_confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis failed: {e}")
            analysis_result['error'] = str(e)
            
            # Calculate processing time even on error
            end_time = asyncio.get_event_loop().time()
            analysis_result['processing_time_ms'] = int((end_time - start_time) * 1000)
        
        return analysis_result
    
    async def _openai_desk_rejection_analysis(
        self,
        request: ManuscriptAnalysisRequest,
        pdf_content: Optional[Any]
    ) -> DeskRejectionAnalysis:
        """
        OpenAI-powered desk rejection analysis
        """
        # Prepare content for analysis
        abstract = pdf_content.abstract if pdf_content else request.abstract
        text_sample = pdf_content.full_text[:3000] if pdf_content else ""
        
        prompt = self._build_desk_rejection_prompt(
            request.title,
            abstract,
            text_sample,
            request.journal_id
        )
        
        # Call AI service
        response = await self.ai_client.analyze_text(
            prompt=prompt,
            max_tokens=1500,
            temperature=0.3
        )
        
        # Parse response into structured result
        return self._parse_desk_rejection_response(response)
    
    async def _openai_referee_recommendations(
        self,
        request: ManuscriptAnalysisRequest,
        pdf_content: Optional[Any],
        num_recommendations: int
    ) -> List[RefereeRecommendation]:
        """
        OpenAI-powered referee recommendations
        """
        abstract = pdf_content.abstract if pdf_content else request.abstract
        
        prompt = self._build_referee_recommendation_prompt(
            request.title,
            abstract,
            num_recommendations
        )
        
        # Call AI service
        response = await self.ai_client.analyze_text(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.4
        )
        
        # Parse response into structured recommendations
        return self._parse_referee_recommendations_response(response)
    
    async def _fallback_desk_rejection_analysis(
        self,
        request: ManuscriptAnalysisRequest,
        pdf_content: Optional[Any]
    ) -> DeskRejectionAnalysis:
        """
        Fallback heuristic-based desk rejection analysis
        """
        # Simple heuristic analysis when AI is not available
        issues = []
        quality_issues = []
        scope_issues = []
        technical_issues = []
        
        # Basic quality checks
        if len(request.title) < 10:
            quality_issues.append("Title appears too short")
        
        abstract = pdf_content.abstract if pdf_content else request.abstract
        if not abstract or len(abstract) < 100:
            quality_issues.append("Abstract appears too short or missing")
        
        # Simple keyword-based scope checking
        math_keywords = ['algorithm', 'optimization', 'theorem', 'proof', 'analysis', 'method', 'model']
        title_lower = request.title.lower()
        abstract_lower = (abstract or "").lower()
        
        math_score = sum(1 for keyword in math_keywords if keyword in title_lower or keyword in abstract_lower)
        
        if math_score == 0:
            scope_issues.append("Limited mathematical content detected")
        
        # Determine recommendation
        issue_count = len(quality_issues) + len(scope_issues) + len(technical_issues)
        
        if issue_count == 0:
            recommendation = "accept"
            confidence = 0.7
        elif issue_count <= 2:
            recommendation = "uncertain"
            confidence = 0.5
        else:
            recommendation = "reject"
            confidence = 0.8
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=confidence,
            rejection_reasons=quality_issues + scope_issues + technical_issues,
            quality_issues=quality_issues,
            scope_issues=scope_issues,
            technical_issues=technical_issues,
            recommendation_summary=f"Heuristic analysis found {issue_count} potential issues"
        )
    
    async def _fallback_referee_recommendations(
        self,
        request: ManuscriptAnalysisRequest,
        pdf_content: Optional[Any],
        num_recommendations: int
    ) -> List[RefereeRecommendation]:
        """
        Fallback heuristic-based referee recommendations
        """
        # Simple keyword-based recommendations
        math_areas = {
            'optimization': 'Optimization Theory',
            'algorithm': 'Computational Mathematics', 
            'numerical': 'Numerical Analysis',
            'stochastic': 'Stochastic Processes',
            'differential': 'Differential Equations',
            'topology': 'Topology',
            'algebra': 'Algebra',
            'analysis': 'Mathematical Analysis'
        }
        
        detected_areas = []
        title_lower = request.title.lower()
        
        for keyword, area in math_areas.items():
            if keyword in title_lower:
                detected_areas.append(area)
        
        if not detected_areas:
            detected_areas = ['General Mathematics']
        
        recommendations = []
        for i in range(num_recommendations):
            area = detected_areas[i % len(detected_areas)]
            
            recommendations.append(RefereeRecommendation(
                name=f"Expert in {area} {i+1}",
                expertise_match=0.7 - i * 0.05,  # Decreasing match score
                availability_score=0.6,
                quality_score=0.8,
                workload_score=0.5,
                overall_score=0.6 - i * 0.05,
                rationale=f"Specializes in {area}, relevant to manuscript topic",
                contact_info={'email': f'expert{i+1}@university.edu'}
            ))
        
        return recommendations
    
    def _build_desk_rejection_prompt(
        self,
        title: str,
        abstract: str,
        text_sample: str,
        journal_id: str
    ) -> str:
        """Build prompt for desk rejection analysis"""
        return f"""
        As an expert academic editor for {journal_id}, analyze this manuscript for potential desk rejection.
        
        Title: {title}
        
        Abstract: {abstract}
        
        Text Sample: {text_sample}
        
        Evaluate the manuscript on these criteria:
        1. Scope fit for a mathematics/applied mathematics journal
        2. Technical quality and rigor
        3. Novelty and significance
        4. Writing clarity and presentation
        5. Completeness and methodology
        
        Provide your analysis in JSON format with:
        - recommendation: "accept", "reject", or "uncertain"
        - confidence: float between 0 and 1
        - rejection_reasons: list of specific reasons if recommending rejection
        - quality_issues: list of quality concerns
        - scope_issues: list of scope/fit concerns  
        - technical_issues: list of technical problems
        - recommendation_summary: brief summary of recommendation
        
        Be thorough but concise. Focus on actionable feedback.
        """
    
    def _build_referee_recommendation_prompt(
        self,
        title: str,
        abstract: str,
        num_recommendations: int
    ) -> str:
        """Build prompt for referee recommendations"""
        return f"""
        As an expert academic editor, recommend {num_recommendations} suitable referees for this manuscript.
        
        Title: {title}
        Abstract: {abstract}
        
        For each recommended referee, provide:
        - name: A realistic academic name (can be generic like "Expert in [Area]")
        - expertise_match: How well their expertise matches (0.0-1.0)
        - availability_score: Estimated availability (0.0-1.0, based on typical academic workload)
        - quality_score: Expected review quality (0.0-1.0)
        - workload_score: Current workload consideration (0.0-1.0, higher = less overloaded)
        - overall_score: Combined score (0.0-1.0)
        - rationale: Brief explanation for the recommendation
        
        Return as JSON array of referee objects.
        Focus on diversity of expertise while maintaining relevance.
        """
    
    def _parse_desk_rejection_response(self, response: str) -> DeskRejectionAnalysis:
        """Parse AI response into DeskRejectionAnalysis"""
        import json
        
        try:
            result = json.loads(response)
            return DeskRejectionAnalysis(
                recommendation=result.get('recommendation', 'uncertain'),
                confidence=float(result.get('confidence', 0.5)),
                rejection_reasons=result.get('rejection_reasons', []),
                quality_issues=result.get('quality_issues', []),
                scope_issues=result.get('scope_issues', []),
                technical_issues=result.get('technical_issues', []),
                recommendation_summary=result.get('recommendation_summary', 'Analysis completed')
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return DeskRejectionAnalysis(
                recommendation="uncertain",
                confidence=0.5,
                rejection_reasons=["Failed to parse AI analysis"],
                quality_issues=[],
                scope_issues=[],
                technical_issues=[],
                recommendation_summary="AI analysis parsing failed"
            )
    
    def _parse_referee_recommendations_response(self, response: str) -> List[RefereeRecommendation]:
        """Parse AI response into referee recommendations"""
        import json
        
        try:
            result = json.loads(response)
            
            recommendations = []
            for rec_data in result:
                recommendations.append(RefereeRecommendation(
                    name=rec_data.get('name', 'Expert Reviewer'),
                    expertise_match=float(rec_data.get('expertise_match', 0.7)),
                    availability_score=float(rec_data.get('availability_score', 0.6)),
                    quality_score=float(rec_data.get('quality_score', 0.8)),
                    workload_score=float(rec_data.get('workload_score', 0.5)),
                    overall_score=float(rec_data.get('overall_score', 0.6)),
                    rationale=rec_data.get('rationale', 'Suitable expertise for this research area')
                ))
            
            return recommendations
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse referee recommendations: {e}")
            return []
    
    async def _get_cached_analysis(self, request: ManuscriptAnalysisRequest, analysis_type: str) -> Optional[Any]:
        """Get cached analysis results"""
        try:
            async with get_session() as session:
                return await self.ai_repository.get_cached_analysis(
                    session, request.manuscript_id, analysis_type
                )
        except Exception as e:
            logger.debug(f"Cache retrieval error: {e}")
            return None
    
    async def _cache_analysis(self, request: ManuscriptAnalysisRequest, analysis_type: str, result: Any):
        """Cache analysis results"""
        try:
            async with get_session() as session:
                await self.ai_repository.cache_analysis(
                    session, request.manuscript_id, analysis_type, result
                )
        except Exception as e:
            logger.debug(f"Cache storage error: {e}")
    
    async def _store_analysis_result(self, request: ManuscriptAnalysisRequest, analysis: DeskRejectionAnalysis):
        """Store analysis result in database"""
        try:
            async with get_session() as session:
                await self.ai_repository.store_analysis_result(
                    session, request.manuscript_id, analysis
                )
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")