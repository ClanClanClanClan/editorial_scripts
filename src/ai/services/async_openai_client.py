"""
Async OpenAI client implementation for AI-powered analysis
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import asdict

from ..ports.ai_client import AIClient, AIModel
from ..models.manuscript_analysis import (
    DeskRejectionAnalysis, RefereeRecommendation, AnalysisRecommendation,
    QualityIssue, QualityIssueType, ManuscriptMetadata
)

logger = logging.getLogger(__name__)


class AsyncOpenAIClient(AIClient):
    """
    Async OpenAI client implementing the AIClientPort interface
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self.available = False
        
        # Initialize OpenAI client
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI async client"""
        try:
            if not self.api_key:
                import os
                self.api_key = os.getenv('OPENAI_API_KEY')
            
            if self.api_key:
                import openai
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
                self.available = True
                logger.info("✅ AsyncOpenAI client initialized successfully")
            else:
                logger.warning("⚠️ OpenAI API key not found")
                
        except ImportError:
            logger.warning("⚠️ OpenAI package not installed")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI client initialization failed: {e}")
    
    async def check_model_availability(self, model: AIModel) -> bool:
        """Check if specified AI model is available"""
        return self.available and self.client is not None
    
    async def _analyze_text(
        self,
        prompt: str,
        model: AIModel = AIModel.GPT_4_TURBO,
        max_tokens: int = 1500,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """
        Internal method to analyze text using OpenAI API
        """
        if not await self.check_model_availability(model):
            raise ValueError("OpenAI client not available")
        
        try:
            response = await self.client.chat.completions.create(
                model=model.value,
                messages=[
                    {"role": "system", "content": "You are an expert academic editor with 20+ years of experience in mathematics and applied mathematics journals."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            content = response.choices[0].message.content
            logger.debug(f"OpenAI API call successful, response length: {len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    async def analyze_for_desk_rejection(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        journal_code: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> DeskRejectionAnalysis:
        """
        Use AI to analyze manuscript for desk rejection
        """
        prompt = self._build_desk_rejection_prompt(title, abstract, full_text_sample, journal_code)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self._analyze_text(
                prompt=prompt,
                model=model,
                max_tokens=1500,
                temperature=0.3
            )
            
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            # Parse the JSON response
            result = json.loads(response)
            
            # Convert to domain model
            return self._parse_desk_rejection_response(result, processing_time)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI")
        except Exception as e:
            logger.error(f"Desk rejection analysis failed: {e}")
            raise
    
    async def extract_research_metadata(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, Any]:
        """
        Extract structured research metadata using AI
        """
        prompt = self._build_metadata_extraction_prompt(title, abstract, full_text_sample)
        
        try:
            response = await self._analyze_text(
                prompt=prompt,
                model=model,
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse the JSON response
            result = json.loads(response)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata response as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI")
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise
    
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
        """
        Generate referee suggestions using AI
        """
        prompt = self._build_referee_recommendation_prompt(
            title, abstract, research_area, keywords, journal_code, exclude_authors
        )
        
        try:
            response = await self._analyze_text(
                prompt=prompt,
                model=model,
                max_tokens=2000,
                temperature=0.4
            )
            
            # Parse the JSON response
            result = json.loads(response)
            
            # Convert to domain models
            return self._parse_referee_recommendations_response(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse referee recommendations as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI")
        except Exception as e:
            logger.error(f"Referee recommendation failed: {e}")
            raise
    
    async def assess_quality(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, float]:
        """
        Assess various quality metrics using AI
        """
        prompt = self._build_quality_assessment_prompt(title, abstract, full_text_sample)
        
        try:
            response = await self._analyze_text(
                prompt=prompt,
                model=model,
                max_tokens=800,
                temperature=0.3
            )
            
            # Parse the JSON response
            result = json.loads(response)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quality assessment as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI")
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            raise
    
    async def explain_decision(
        self,
        analysis_result: DeskRejectionAnalysis,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> str:
        """
        Generate human-readable explanation of AI decision
        """
        prompt = self._build_explanation_prompt(analysis_result)
        
        try:
            response = await self._analyze_text(
                prompt=prompt,
                model=model,
                max_tokens=1000,
                temperature=0.5
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Decision explanation failed: {e}")
            raise
    
    def _build_desk_rejection_prompt(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        journal_id: str
    ) -> str:
        """Build comprehensive prompt for desk rejection analysis"""
        journal_context = self._get_journal_context(journal_id)
        
        return f"""
Analyze this manuscript for potential desk rejection as an expert editor for {journal_id}.

{journal_context}

MANUSCRIPT DETAILS:
Title: {title}

Abstract: {abstract}

Text Sample: {full_text_sample[:2000]}...

EVALUATION CRITERIA:
1. Journal Scope Fit (0.0-1.0): How well does this align with the journal's focus?
2. Technical Quality (0.0-1.0): Is the methodology sound and rigorous?
3. Novelty & Significance (0.0-1.0): Does this present meaningful new insights?
4. Presentation Quality (0.0-1.0): Is it well-written, clear, and organized?
5. Completeness (0.0-1.0): Are the results and analysis sufficient?

REQUIRED OUTPUT FORMAT (JSON):
{{
    "recommendation": "accept_for_review|desk_reject|requires_revision|uncertain",
    "confidence": 0.85,
    "overall_score": 0.72,
    "scores": {{
        "scope_fit": 0.8,
        "technical_quality": 0.75,
        "novelty": 0.7,
        "presentation": 0.8,
        "completeness": 0.65
    }},
    "rejection_reasons": ["List specific reasons if recommending rejection"],
    "quality_issues": [
        {{
            "type": "technical_error|unclear_methodology|insufficient_novelty|poor_presentation|scope_mismatch|incomplete_analysis|reference_issues",
            "severity": 0.7,
            "description": "Specific description of the issue",
            "location": "Section or page reference (optional)",
            "suggestion": "Specific improvement suggestion (optional)"
        }}
    ],
    "scope_issues": ["List scope/fit concerns"],
    "technical_issues": ["List technical problems"],
    "recommendation_summary": "Brief summary of recommendation",
    "detailed_explanation": "Comprehensive explanation of the analysis and decision"
}}

Be thorough, objective, and provide actionable feedback. Focus on helping improve the manuscript quality.
"""
    
    def _build_referee_recommendation_prompt(
        self,
        title: str,
        abstract: str,
        research_area: str,
        keywords: List[str],
        journal_code: str,
        exclude_authors: List[str] = None
    ) -> str:
        """Build prompt for referee recommendations"""
        journal_context = self._get_journal_context(journal_code)
        exclude_text = ""
        if exclude_authors:
            exclude_text = f"\nEXCLUDE these authors from recommendations: {', '.join(exclude_authors)}"
        
        return f"""
Recommend 5 suitable referees for this manuscript as an expert editor for {journal_code}.

{journal_context}

MANUSCRIPT DETAILS:
Title: {title}
Abstract: {abstract}
Research Area: {research_area}
Keywords: {', '.join(keywords)}
{exclude_text}

REFEREE SELECTION CRITERIA:
- Expertise match with manuscript content and keywords
- Availability and typical response patterns
- Review quality and thoroughness
- Current workload considerations
- Geographic and institutional diversity

REQUIRED OUTPUT FORMAT (JSON Array):
[
    {{
        "referee_name": "Dr. Expert Name or 'Expert in [Specific Area]'",
        "expertise_match": 0.85,
        "availability_score": 0.7,
        "quality_score": 0.9,
        "workload_score": 0.6,
        "overall_score": 0.8,
        "expertise_areas": ["optimization", "machine learning", "control theory"],
        "matching_keywords": ["algorithm", "convergence", "numerical"],
        "rationale": "Detailed explanation for this recommendation",
        "confidence": 0.8,
        "institution": "University Name (if known)",
        "recent_publications": ["Relevant paper titles if known"],
        "estimated_response_time": 7,
        "estimated_review_time": 21
    }}
]

Provide realistic recommendations with diverse expertise while maintaining high relevance. Consider both established experts and emerging researchers.
"""
    
    def _build_metadata_extraction_prompt(
        self,
        title: str,
        abstract: str,
        full_text_sample: str
    ) -> str:
        """Build prompt for metadata extraction"""
        return f"""
Extract structured research metadata from this manuscript.

MANUSCRIPT DETAILS:
Title: {title}
Abstract: {abstract}
Text Sample: {full_text_sample[:2000]}...

REQUIRED OUTPUT FORMAT (JSON):
{{
    "research_area": "Primary research domain (e.g., 'optimization', 'control theory')",
    "methodology": "Research methodology used (e.g., 'theoretical analysis', 'numerical simulation')",
    "keywords": ["extracted", "relevant", "keywords", "from", "content"],
    "novelty_score": 0.8,
    "complexity_score": 0.7,
    "quality_scores": {{
        "technical_quality": 0.8,
        "presentation_quality": 0.7,
        "completeness": 0.9,
        "significance": 0.75
    }}
}}

Provide objective assessments based on the manuscript content.
"""
    
    def _build_quality_assessment_prompt(
        self,
        title: str,
        abstract: str,
        full_text_sample: str
    ) -> str:
        """Build prompt for quality assessment"""
        return f"""
Assess the quality metrics of this manuscript across multiple dimensions.

MANUSCRIPT DETAILS:
Title: {title}
Abstract: {abstract}
Text Sample: {full_text_sample[:2000]}...

REQUIRED OUTPUT FORMAT (JSON):
{{
    "technical_quality": 0.85,
    "presentation_quality": 0.80,
    "novelty_score": 0.75,
    "significance_score": 0.70,
    "completeness_score": 0.90
}}

Each score should be between 0.0 and 1.0 where:
- technical_quality: Technical rigor, correctness, and soundness
- presentation_quality: Writing clarity, organization, and readability
- novelty_score: Originality and new contributions
- significance_score: Potential impact and importance
- completeness_score: Thoroughness of analysis and results

Provide objective, evidence-based assessments.
"""
    
    def _build_explanation_prompt(
        self,
        analysis_result: DeskRejectionAnalysis
    ) -> str:
        """Build prompt for decision explanation"""
        return f"""
Generate a clear, human-readable explanation of this AI analysis decision.

ANALYSIS RESULT:
Recommendation: {analysis_result.recommendation.value}
Confidence: {analysis_result.confidence:.2f}
Overall Score: {analysis_result.overall_score:.2f}
Quality Issues: {len(analysis_result.quality_issues)}
Scope Issues: {analysis_result.scope_issues}
Technical Issues: {analysis_result.technical_issues}

Create a comprehensive but accessible explanation that:
1. Summarizes the overall recommendation and confidence level
2. Explains the key factors that influenced the decision
3. Highlights the main strengths and concerns identified
4. Provides actionable guidance for the editorial team
5. Uses clear, professional language suitable for editors

The explanation should be 2-3 paragraphs long and help editors understand and trust the AI recommendation.
"""
    
    def _get_journal_context(self, journal_id: str) -> str:
        """Get journal-specific context for prompts"""
        journal_contexts = {
            "SICON": "SIAM Journal on Control and Optimization focuses on mathematical control theory, optimization, and related computational methods.",
            "SIFIN": "SIAM Journal on Financial Mathematics covers mathematical finance, risk management, and quantitative finance methods.",
            "MOR": "Mathematics of Operations Research publishes research on mathematical aspects of operations research, optimization, and decision sciences.",
            "JOTA": "Journal of Optimization Theory and Applications covers theoretical and applied aspects of optimization.",
            "MF": "Mathematical Finance focuses on mathematical models and methods in finance and economics.",
            "MAFE": "Mathematical Analysis and Financial Engineering covers mathematical analysis with applications to finance."
        }
        
        return journal_contexts.get(journal_id, f"This is a mathematics journal ({journal_id}) focusing on rigorous mathematical research.")
    
    def _parse_desk_rejection_response(self, result: Dict[str, Any], processing_time: float) -> DeskRejectionAnalysis:
        """Parse OpenAI response into DeskRejectionAnalysis domain model"""
        try:
            # Parse recommendation
            recommendation_str = result.get('recommendation', 'uncertain')
            recommendation = AnalysisRecommendation(recommendation_str)
            
            # Parse quality issues
            quality_issues = []
            for issue_data in result.get('quality_issues', []):
                issue_type = QualityIssueType(issue_data.get('type', 'technical_error'))
                quality_issues.append(QualityIssue(
                    issue_type=issue_type,
                    severity=float(issue_data.get('severity', 0.5)),
                    description=issue_data.get('description', ''),
                    location=issue_data.get('location'),
                    suggestion=issue_data.get('suggestion')
                ))
            
            return DeskRejectionAnalysis(
                recommendation=recommendation,
                confidence=float(result.get('confidence', 0.5)),
                overall_score=float(result.get('overall_score', 0.5)),
                rejection_reasons=result.get('rejection_reasons', []),
                quality_issues=quality_issues,
                scope_issues=result.get('scope_issues', []),
                technical_issues=result.get('technical_issues', []),
                recommendation_summary=result.get('recommendation_summary', ''),
                detailed_explanation=result.get('detailed_explanation', ''),
                model_version=self.model,
                processing_time_seconds=processing_time
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse desk rejection response: {e}")
            # Return fallback analysis
            return DeskRejectionAnalysis(
                recommendation=AnalysisRecommendation.UNCERTAIN,
                confidence=0.3,
                overall_score=0.5,
                rejection_reasons=["Failed to parse AI analysis"],
                recommendation_summary="AI analysis parsing failed",
                model_version=self.model,
                processing_time_seconds=processing_time
            )
    
    def _parse_referee_recommendations_response(self, result: List[Dict[str, Any]]) -> List[RefereeRecommendation]:
        """Parse OpenAI response into RefereeRecommendation domain models"""
        recommendations = []
        
        try:
            for rec_data in result:
                recommendation = RefereeRecommendation(
                    referee_name=rec_data.get('referee_name', 'Expert Reviewer'),
                    expertise_match=float(rec_data.get('expertise_match', 0.7)),
                    availability_score=float(rec_data.get('availability_score', 0.6)),
                    quality_score=float(rec_data.get('quality_score', 0.8)),
                    workload_score=float(rec_data.get('workload_score', 0.5)),
                    overall_score=float(rec_data.get('overall_score', 0.6)),
                    expertise_areas=rec_data.get('expertise_areas', []),
                    matching_keywords=rec_data.get('matching_keywords', []),
                    rationale=rec_data.get('rationale', 'Suitable expertise for this research area'),
                    confidence=float(rec_data.get('confidence', 0.7)),
                    institution=rec_data.get('institution'),
                    recent_publications=rec_data.get('recent_publications', []),
                    average_review_time_days=rec_data.get('estimated_review_time', 21)
                )
                
                # Calculate overall score if not provided
                if recommendation.overall_score == 0.6:  # Default value
                    recommendation.calculate_overall_score()
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse referee recommendations: {e}")
            return []
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        # This would require storing usage data
        return {
            "api_calls_today": 0,
            "tokens_used_today": 0,
            "average_response_time": 0.0,
            "success_rate": 1.0
        }