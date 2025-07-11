"""
OpenAI Client Implementation
Async implementation of AI service using OpenAI API
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..ports.ai_client import AIClient, AIModel
from ..models.manuscript_analysis import (
    DeskRejectionAnalysis, 
    RefereeRecommendation,
    AnalysisRecommendation,
    QualityIssue,
    QualityIssueType
)
from ...infrastructure.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIClient(AIClient):
    """OpenAI API client for manuscript analysis"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.openai_api_key
        self.client = None
        self._initialize_client()
        
        # Journal-specific prompts
        self.journal_contexts = {
            'SICON': 'SIAM Journal on Control and Optimization - focuses on mathematical control theory, optimization, and related applications',
            'SIFIN': 'SIAM Journal on Financial Mathematics - focuses on mathematical and computational methods in finance',
            'MF': 'Mathematical Finance - focuses on mathematical theory and methods in finance',
            'MOR': 'Mathematics of Operations Research - focuses on mathematical aspects of operations research',
            'MAFE': 'Mathematical and Financial Economics - focuses on mathematical methods in economics and finance',
            'NACO': 'Numerical Algorithms and Computational Optimization - focuses on numerical methods and algorithms'
        }
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        if not self.api_key:
            logger.warning("⚠️ OpenAI API key not configured")
            return
            
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            logger.info("✅ OpenAI client initialized successfully")
        except ImportError:
            logger.error("❌ OpenAI package not installed")
        except Exception as e:
            logger.error(f"❌ OpenAI client initialization failed: {e}")
    
    async def analyze_for_desk_rejection(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        journal_code: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> DeskRejectionAnalysis:
        """Analyze manuscript for desk rejection using OpenAI"""
        
        if not self.client:
            return self._fallback_desk_rejection_analysis(title, "OpenAI client not available")
        
        start_time = datetime.now()
        
        try:
            journal_context = self.journal_contexts.get(journal_code, 'mathematical research journal')
            
            prompt = f"""
As an expert academic editor for {journal_context}, analyze this manuscript for potential desk rejection.

Title: {title}

Abstract: {abstract}

Text Sample: {full_text_sample[:3000]}

Evaluate the manuscript on these criteria:
1. Scope fit for the journal
2. Technical quality and mathematical rigor
3. Novelty and significance of contributions
4. Writing clarity and presentation quality
5. Completeness of methodology and results

Provide your analysis in valid JSON format with exactly these fields:
{{
    "recommendation": "accept_for_review" | "desk_reject" | "requires_revision" | "uncertain",
    "confidence": 0.0-1.0,
    "overall_score": 0.0-1.0,
    "rejection_reasons": ["reason1", "reason2"],
    "quality_issues": [
        {{
            "type": "technical_error" | "unclear_methodology" | "insufficient_novelty" | "poor_presentation" | "scope_mismatch" | "incomplete_analysis" | "reference_issues",
            "severity": 0.0-1.0,
            "description": "detailed description"
        }}
    ],
    "scope_issues": ["issue1", "issue2"],
    "technical_issues": ["issue1", "issue2"],
    "recommendation_summary": "brief summary",
    "detailed_explanation": "comprehensive explanation"
}}

Focus on mathematical rigor, novelty, and fit for the specific journal scope.
"""

            response = await self.client.chat.completions.create(
                model=model.value,
                messages=[
                    {"role": "system", "content": "You are an expert academic editor specializing in mathematical research. Provide detailed, fair, and constructive analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                analysis_data = json.loads(content)
                return self._create_desk_rejection_analysis(analysis_data, model, start_time)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                return self._fallback_desk_rejection_analysis(title, "Invalid JSON response from AI")
                
        except Exception as e:
            logger.error(f"OpenAI desk rejection analysis failed: {e}")
            return self._fallback_desk_rejection_analysis(title, str(e))
    
    def _create_desk_rejection_analysis(
        self, 
        data: Dict[str, Any], 
        model: AIModel, 
        start_time: datetime
    ) -> DeskRejectionAnalysis:
        """Create DeskRejectionAnalysis from OpenAI response"""
        
        # Parse recommendation
        rec_mapping = {
            "accept_for_review": AnalysisRecommendation.ACCEPT_FOR_REVIEW,
            "desk_reject": AnalysisRecommendation.DESK_REJECT,
            "requires_revision": AnalysisRecommendation.REQUIRES_REVISION,
            "uncertain": AnalysisRecommendation.UNCERTAIN
        }
        recommendation = rec_mapping.get(data.get("recommendation", "uncertain"), AnalysisRecommendation.UNCERTAIN)
        
        # Parse quality issues
        quality_issues = []
        for issue_data in data.get("quality_issues", []):
            issue_type_mapping = {
                "technical_error": QualityIssueType.TECHNICAL_ERROR,
                "unclear_methodology": QualityIssueType.UNCLEAR_METHODOLOGY,
                "insufficient_novelty": QualityIssueType.INSUFFICIENT_NOVELTY,
                "poor_presentation": QualityIssueType.POOR_PRESENTATION,
                "scope_mismatch": QualityIssueType.SCOPE_MISMATCH,
                "incomplete_analysis": QualityIssueType.INCOMPLETE_ANALYSIS,
                "reference_issues": QualityIssueType.REFERENCE_ISSUES
            }
            
            issue_type = issue_type_mapping.get(issue_data.get("type"), QualityIssueType.TECHNICAL_ERROR)
            quality_issue = QualityIssue(
                issue_type=issue_type,
                severity=float(issue_data.get("severity", 0.5)),
                description=issue_data.get("description", ""),
                suggestion=issue_data.get("suggestion")
            )
            quality_issues.append(quality_issue)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=float(data.get("confidence", 0.5)),
            overall_score=float(data.get("overall_score", 0.5)),
            rejection_reasons=data.get("rejection_reasons", []),
            quality_issues=quality_issues,
            scope_issues=data.get("scope_issues", []),
            technical_issues=data.get("technical_issues", []),
            model_version=model.value,
            processing_time_seconds=processing_time,
            recommendation_summary=data.get("recommendation_summary", ""),
            detailed_explanation=data.get("detailed_explanation", "")
        )
    
    def _fallback_desk_rejection_analysis(self, title: str, error_msg: str) -> DeskRejectionAnalysis:
        """Create fallback analysis when OpenAI is unavailable"""
        logger.warning(f"Using fallback desk rejection analysis: {error_msg}")
        
        # Simple heuristic analysis
        confidence = 0.3  # Low confidence for fallback
        
        # Basic heuristics
        has_math_keywords = any(keyword in title.lower() for keyword in 
                               ['theorem', 'proof', 'algorithm', 'optimization', 'analysis', 'method'])
        
        if has_math_keywords:
            recommendation = AnalysisRecommendation.ACCEPT_FOR_REVIEW
            summary = "Fallback analysis: Title suggests mathematical content suitable for review"
        else:
            recommendation = AnalysisRecommendation.UNCERTAIN
            summary = "Fallback analysis: Unable to determine suitability without AI analysis"
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=confidence,
            overall_score=0.5,
            rejection_reasons=[],
            quality_issues=[],
            scope_issues=[],
            technical_issues=[],
            model_version="fallback-heuristic",
            recommendation_summary=summary,
            detailed_explanation=f"Fallback analysis used due to: {error_msg}"
        )
    
    async def extract_research_metadata(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, Any]:
        """Extract research metadata using OpenAI"""
        
        if not self.client:
            return self._fallback_metadata(title, abstract)
        
        try:
            prompt = f"""
Extract structured research metadata from this manuscript:

Title: {title}
Abstract: {abstract}
Text Sample: {full_text_sample[:2000]}

Provide a JSON response with:
{{
    "research_area": "primary research area",
    "methodology": "research methodology used",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "novelty_score": 0.0-1.0,
    "complexity_score": 0.0-1.0,
    "technical_quality_score": 0.0-1.0,
    "presentation_quality_score": 0.0-1.0,
    "scope_fit_score": 0.0-1.0
}}
"""

            response = await self.client.chat.completions.create(
                model=model.value,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing mathematical research papers. Extract structured metadata accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return self._fallback_metadata(title, abstract)
    
    def _fallback_metadata(self, title: str, abstract: str) -> Dict[str, Any]:
        """Fallback metadata extraction using simple heuristics"""
        return {
            "research_area": "Mathematical Sciences",
            "methodology": "Theoretical/Computational",
            "keywords": title.lower().split()[:5],
            "novelty_score": 0.5,
            "complexity_score": 0.5,
            "technical_quality_score": 0.5,
            "presentation_quality_score": 0.5,
            "scope_fit_score": 0.5
        }
    
    async def suggest_referees(
        self,
        title: str,
        abstract: str,
        research_area: str,
        keywords: List[str],
        journal_code: str,
        exclude_authors: List[str] = None,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> List[RefereeRecommendation]:
        """Generate referee suggestions (placeholder - needs referee database integration)"""
        
        # This would need integration with a referee database
        # For now, return empty list with note for future implementation
        logger.info("Referee suggestion requires referee database integration")
        return []
    
    async def assess_quality(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, float]:
        """Assess quality metrics using OpenAI"""
        
        if not self.client:
            return {
                'technical_quality': 0.5,
                'presentation_quality': 0.5,
                'novelty_score': 0.5,
                'significance_score': 0.5,
                'completeness_score': 0.5
            }
        
        try:
            prompt = f"""
Assess the quality of this manuscript on multiple dimensions:

Title: {title}
Abstract: {abstract}
Text Sample: {full_text_sample[:2000]}

Provide scores (0.0-1.0) in JSON format:
{{
    "technical_quality": 0.0-1.0,
    "presentation_quality": 0.0-1.0,
    "novelty_score": 0.0-1.0,
    "significance_score": 0.0-1.0,
    "completeness_score": 0.0-1.0
}}
"""

            response = await self.client.chat.completions.create(
                model=model.value,
                messages=[
                    {"role": "system", "content": "You are an expert reviewer assessing academic papers. Provide fair and accurate quality assessments."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {
                'technical_quality': 0.5,
                'presentation_quality': 0.5,
                'novelty_score': 0.5,
                'significance_score': 0.5,
                'completeness_score': 0.5
            }
    
    async def explain_decision(
        self,
        analysis_result: DeskRejectionAnalysis,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> str:
        """Generate human-readable explanation of AI decision"""
        
        if not self.client:
            return f"AI Analysis: {analysis_result.recommendation_summary}"
        
        try:
            prompt = f"""
Generate a clear, professional explanation for this editorial decision:

Recommendation: {analysis_result.recommendation.value}
Confidence: {analysis_result.confidence}
Summary: {analysis_result.recommendation_summary}
Issues: {[issue.description for issue in analysis_result.quality_issues]}

Write a 2-3 paragraph explanation that an editor could use when communicating with authors.
Be constructive and specific about areas for improvement.
"""

            response = await self.client.chat.completions.create(
                model=model.value,
                messages=[
                    {"role": "system", "content": "You are an expert editor writing professional feedback to authors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Decision explanation failed: {e}")
            return analysis_result.detailed_explanation or analysis_result.recommendation_summary
    
    async def check_model_availability(self, model: AIModel) -> bool:
        """Check if specified model is available"""
        if not self.client:
            return False
        
        try:
            # Test with a minimal request
            await self.client.chat.completions.create(
                model=model.value,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception:
            return False
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics (placeholder)"""
        return {
            'requests_today': 0,
            'tokens_used': 0,
            'cost_estimate': 0.0,
            'rate_limit_remaining': 'unknown'
        }