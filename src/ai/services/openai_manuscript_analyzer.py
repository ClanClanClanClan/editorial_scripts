"""
OpenAI-powered Manuscript Analyzer Implementation
Orchestrates PDF processing and AI analysis in clean architecture
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..ports.manuscript_analyzer import ManuscriptAnalyzer
from ..ports.pdf_processor import PDFProcessor
from ..ports.ai_client import AIClient
from ..models.manuscript_analysis import (
    AnalysisResult,
    ManuscriptMetadata,
    DeskRejectionAnalysis,
    RefereeRecommendation
)
from ...infrastructure.config import get_settings
from ...infrastructure.cache.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class OpenAIManuscriptAnalyzer(ManuscriptAnalyzer):
    """
    Main manuscript analyzer using OpenAI for AI analysis
    Orchestrates PDF processing, AI analysis, and caching
    """
    
    def __init__(
        self,
        pdf_processor: PDFProcessor,
        ai_client: AIClient,
        cache: Optional[RedisCache] = None
    ):
        self.pdf_processor = pdf_processor
        self.ai_client = ai_client
        self.cache = cache
        self.settings = get_settings()
        
        # Analysis configuration
        self.cache_ttl_hours = 24
        self.max_text_length = 10000  # Limit for AI processing
        
        logger.info("✅ OpenAI Manuscript Analyzer initialized")
    
    async def analyze_manuscript(
        self,
        manuscript_id: str,
        journal_code: str,
        pdf_path: Path,
        manuscript_data: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Perform comprehensive AI analysis of a manuscript
        """
        start_time = datetime.now()
        logger.info(f"Starting analysis for manuscript {manuscript_id}")
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(manuscript_id, pdf_path)
            if self.cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.info(f"📋 Using cached analysis for {manuscript_id}")
                    return AnalysisResult(**cached_result)
            
            # Validate PDF
            pdf_validation = await self.pdf_processor.validate_pdf(pdf_path)
            if not pdf_validation['is_valid']:
                raise ValueError(f"Invalid PDF: {', '.join(pdf_validation['issues'])}")
            
            # Extract content from PDF
            logger.info(f"🔍 Extracting content from PDF: {pdf_path}")
            text_content = await self.pdf_processor.extract_text_content(pdf_path)
            pdf_metadata = await self.pdf_processor.extract_metadata(pdf_path)
            content_hash = await self.pdf_processor.get_content_hash(pdf_path)
            
            if 'error' in text_content:
                raise ValueError(f"PDF extraction failed: {text_content['error']}")
            
            # Extract structured metadata using AI
            logger.info(f"🤖 Extracting metadata with AI")
            ai_metadata = await self.ai_client.extract_research_metadata(
                title=text_content.get('title', ''),
                abstract=text_content.get('abstract', ''),
                full_text_sample=text_content.get('full_text', '')[:self.max_text_length]
            )
            
            # Create manuscript metadata
            metadata = ManuscriptMetadata(
                title=text_content.get('title', manuscript_data.get('Title', 'Unknown') if manuscript_data else 'Unknown'),
                abstract=text_content.get('abstract', ''),
                keywords=ai_metadata.get('keywords', []),
                research_area=ai_metadata.get('research_area', ''),
                methodology=ai_metadata.get('methodology', ''),
                complexity_score=ai_metadata.get('complexity_score', 0.5),
                novelty_score=ai_metadata.get('novelty_score', 0.5),
                technical_quality_score=ai_metadata.get('technical_quality_score', 0.5),
                presentation_quality_score=ai_metadata.get('presentation_quality_score', 0.5),
                scope_fit_score=ai_metadata.get('scope_fit_score', 0.5),
                quality_indicators=pdf_validation
            )
            
            # Perform desk rejection analysis
            logger.info(f"📝 Performing desk rejection analysis")
            desk_analysis = await self.ai_client.analyze_for_desk_rejection(
                title=metadata.title,
                abstract=metadata.abstract,
                full_text_sample=text_content.get('full_text', '')[:self.max_text_length],
                journal_code=journal_code
            )
            
            # Generate referee recommendations (if accepted for review)
            referee_recommendations = []
            if desk_analysis.recommendation.value in ['accept_for_review', 'uncertain']:
                logger.info(f"👥 Generating referee recommendations")
                referee_recommendations = await self.ai_client.suggest_referees(
                    title=metadata.title,
                    abstract=metadata.abstract,
                    research_area=metadata.research_area,
                    keywords=metadata.keywords,
                    journal_code=journal_code
                )
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create analysis result
            analysis_result = AnalysisResult(
                manuscript_id=manuscript_id,
                journal_code=journal_code,
                metadata=metadata,
                desk_rejection_analysis=desk_analysis,
                referee_recommendations=referee_recommendations,
                processing_time_seconds=processing_time,
                content_hash=content_hash,
                pdf_path=str(pdf_path),
                text_extracted=True,
                analysis_quality=self._calculate_analysis_quality(text_content, ai_metadata),
                ai_model_versions={
                    'openai_model': desk_analysis.model_version,
                    'pdf_processor': 'PyPDF2',
                    'analyzer_version': '1.0.0'
                }
            )
            
            # Cache the result
            if self.cache:
                await self.cache.set(
                    cache_key, 
                    analysis_result.__dict__, 
                    ttl_seconds=self.cache_ttl_hours * 3600
                )
            
            logger.info(f"✅ Analysis completed for {manuscript_id} in {processing_time:.2f}s")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Analysis failed for {manuscript_id}: {e}")
            # Return minimal analysis result with error information
            return self._create_error_analysis(manuscript_id, journal_code, str(e), start_time)
    
    async def extract_metadata(self, pdf_path: Path) -> ManuscriptMetadata:
        """Extract structured metadata from manuscript PDF"""
        try:
            # Extract text content
            text_content = await self.pdf_processor.extract_text_content(pdf_path)
            
            # Use AI to extract structured metadata
            ai_metadata = await self.ai_client.extract_research_metadata(
                title=text_content.get('title', ''),
                abstract=text_content.get('abstract', ''),
                full_text_sample=text_content.get('full_text', '')[:self.max_text_length]
            )
            
            return ManuscriptMetadata(
                title=text_content.get('title', ''),
                abstract=text_content.get('abstract', ''),
                keywords=ai_metadata.get('keywords', []),
                research_area=ai_metadata.get('research_area', ''),
                methodology=ai_metadata.get('methodology', ''),
                complexity_score=ai_metadata.get('complexity_score', 0.5),
                novelty_score=ai_metadata.get('novelty_score', 0.5),
                technical_quality_score=ai_metadata.get('technical_quality_score', 0.5),
                presentation_quality_score=ai_metadata.get('presentation_quality_score', 0.5),
                scope_fit_score=ai_metadata.get('scope_fit_score', 0.5)
            )
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return ManuscriptMetadata(title="", abstract="")
    
    async def analyze_for_desk_rejection(
        self,
        manuscript_id: str,
        pdf_path: Path,
        journal_code: str
    ) -> DeskRejectionAnalysis:
        """Analyze manuscript specifically for desk rejection decision"""
        try:
            # Extract content
            text_content = await self.pdf_processor.extract_text_content(pdf_path)
            
            # Perform AI analysis
            return await self.ai_client.analyze_for_desk_rejection(
                title=text_content.get('title', ''),
                abstract=text_content.get('abstract', ''),
                full_text_sample=text_content.get('full_text', '')[:self.max_text_length],
                journal_code=journal_code
            )
            
        except Exception as e:
            logger.error(f"Desk rejection analysis failed: {e}")
            # Return fallback analysis
            from ..models.manuscript_analysis import AnalysisRecommendation
            return DeskRejectionAnalysis(
                recommendation=AnalysisRecommendation.UNCERTAIN,
                confidence=0.1,
                overall_score=0.0,
                recommendation_summary=f"Analysis failed: {str(e)}",
                detailed_explanation=f"Could not perform AI analysis due to error: {str(e)}"
            )
    
    async def recommend_referees(
        self,
        analysis_result: AnalysisResult,
        max_recommendations: int = 10
    ) -> List[RefereeRecommendation]:
        """Generate AI-powered referee recommendations"""
        try:
            return await self.ai_client.suggest_referees(
                title=analysis_result.metadata.title,
                abstract=analysis_result.metadata.abstract,
                research_area=analysis_result.metadata.research_area,
                keywords=analysis_result.metadata.keywords,
                journal_code=analysis_result.journal_code
            )
            
        except Exception as e:
            logger.error(f"Referee recommendation failed: {e}")
            return []
    
    async def validate_analysis(
        self,
        analysis_id: str,
        human_feedback: Dict[str, Any]
    ) -> bool:
        """Record human validation of AI analysis"""
        try:
            # This would typically update the analysis in database
            # and potentially retrain models based on feedback
            logger.info(f"Recorded validation for analysis {analysis_id}")
            
            # Store validation in cache/database
            if self.cache:
                validation_key = f"validation:{analysis_id}"
                await self.cache.set(validation_key, {
                    'feedback': human_feedback,
                    'timestamp': datetime.now().isoformat(),
                    'validated_by': human_feedback.get('reviewer_id', 'unknown')
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Validation recording failed: {e}")
            return False
    
    def _generate_cache_key(self, manuscript_id: str, pdf_path: Path) -> str:
        """Generate cache key for analysis result"""
        # Include file modification time to invalidate cache if PDF changes
        try:
            mtime = pdf_path.stat().st_mtime
            key_data = f"{manuscript_id}:{pdf_path}:{mtime}"
            return f"analysis:{hashlib.md5(key_data.encode()).hexdigest()}"
        except Exception:
            return f"analysis:{manuscript_id}"
    
    def _calculate_analysis_quality(
        self, 
        text_content: Dict[str, str], 
        ai_metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence in the analysis quality"""
        quality_score = 0.0
        
        # Text extraction quality
        if text_content.get('title'):
            quality_score += 0.2
        if text_content.get('abstract'):
            quality_score += 0.3
        if len(text_content.get('full_text', '')) > 1000:
            quality_score += 0.3
        
        # AI metadata quality
        if ai_metadata.get('research_area'):
            quality_score += 0.1
        if ai_metadata.get('keywords'):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _create_error_analysis(
        self,
        manuscript_id: str,
        journal_code: str,
        error_msg: str,
        start_time: datetime
    ) -> AnalysisResult:
        """Create minimal analysis result for error cases"""
        from ..models.manuscript_analysis import AnalysisRecommendation
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            manuscript_id=manuscript_id,
            journal_code=journal_code,
            metadata=ManuscriptMetadata(title="Error", abstract=""),
            desk_rejection_analysis=DeskRejectionAnalysis(
                recommendation=AnalysisRecommendation.UNCERTAIN,
                confidence=0.0,
                overall_score=0.0,
                recommendation_summary=f"Analysis failed: {error_msg}",
                detailed_explanation=f"Could not complete analysis due to: {error_msg}"
            ),
            processing_time_seconds=processing_time,
            analysis_quality=0.0,
            text_extracted=False
        )