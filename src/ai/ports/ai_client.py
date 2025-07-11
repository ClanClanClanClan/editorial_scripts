"""
AI Client Port (Interface)
Defines the contract for AI service integration (OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum

from ..models.manuscript_analysis import DeskRejectionAnalysis, RefereeRecommendation


class AIModel(Enum):
    """Supported AI models"""
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


class AIClient(ABC):
    """Abstract interface for AI service integration"""
    
    @abstractmethod
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
        
        Args:
            title: Manuscript title
            abstract: Manuscript abstract
            full_text_sample: Sample of full text (first few pages)
            journal_code: Target journal code
            model: AI model to use for analysis
            
        Returns:
            Desk rejection analysis with recommendation and reasoning
        """
        pass
    
    @abstractmethod
    async def extract_research_metadata(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, Any]:
        """
        Extract structured research metadata using AI
        
        Args:
            title: Manuscript title
            abstract: Manuscript abstract  
            full_text_sample: Sample of full text
            model: AI model to use
            
        Returns:
            Dictionary with research metadata:
            - 'research_area': Primary research area
            - 'methodology': Research methodology used
            - 'keywords': Extracted keywords
            - 'novelty_score': Assessed novelty (0-1)
            - 'complexity_score': Technical complexity (0-1)
            - 'quality_scores': Various quality metrics
        """
        pass
    
    @abstractmethod
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
        
        Args:
            title: Manuscript title
            abstract: Manuscript abstract
            research_area: Primary research area
            keywords: List of relevant keywords
            journal_code: Target journal
            exclude_authors: Authors to exclude from suggestions
            model: AI model to use
            
        Returns:
            List of referee recommendations with scoring
        """
        pass
    
    @abstractmethod
    async def assess_quality(
        self,
        title: str,
        abstract: str,
        full_text_sample: str,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> Dict[str, float]:
        """
        Assess various quality metrics using AI
        
        Args:
            title: Manuscript title
            abstract: Manuscript abstract
            full_text_sample: Sample of full text
            model: AI model to use
            
        Returns:
            Dictionary with quality scores (0-1):
            - 'technical_quality': Technical rigor and correctness
            - 'presentation_quality': Writing and presentation clarity
            - 'novelty_score': Novelty and originality
            - 'significance_score': Potential impact and significance
            - 'completeness_score': Completeness of analysis
        """
        pass
    
    @abstractmethod
    async def explain_decision(
        self,
        analysis_result: DeskRejectionAnalysis,
        model: AIModel = AIModel.GPT_4_TURBO
    ) -> str:
        """
        Generate human-readable explanation of AI decision
        
        Args:
            analysis_result: AI analysis result to explain
            model: AI model to use for explanation
            
        Returns:
            Human-readable explanation of the decision and reasoning
        """
        pass
    
    @abstractmethod
    async def check_model_availability(self, model: AIModel) -> bool:
        """
        Check if specified AI model is available
        
        Args:
            model: AI model to check
            
        Returns:
            True if model is available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get AI service usage statistics
        
        Returns:
            Dictionary with usage statistics:
            - 'requests_today': Number of requests today
            - 'tokens_used': Total tokens used
            - 'cost_estimate': Estimated cost in USD
            - 'rate_limit_remaining': Remaining rate limit
        """
        pass