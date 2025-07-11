"""
Manuscript Analyzer Port (Interface)
Defines the contract for AI-powered manuscript analysis
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from ..models.manuscript_analysis import AnalysisResult, ManuscriptMetadata


class ManuscriptAnalyzer(ABC):
    """Abstract interface for AI-powered manuscript analysis"""
    
    @abstractmethod
    async def analyze_manuscript(
        self, 
        manuscript_id: str,
        journal_code: str,
        pdf_path: Path,
        manuscript_data: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Perform comprehensive AI analysis of a manuscript
        
        Args:
            manuscript_id: Unique identifier for the manuscript
            journal_code: Journal code (e.g., "SICON", "SIFIN")
            pdf_path: Path to the manuscript PDF file
            manuscript_data: Optional additional manuscript metadata
            
        Returns:
            Complete analysis result with desk rejection analysis and referee recommendations
        """
        pass
    
    @abstractmethod
    async def extract_metadata(
        self,
        pdf_path: Path
    ) -> ManuscriptMetadata:
        """
        Extract structured metadata from manuscript PDF
        
        Args:
            pdf_path: Path to the manuscript PDF file
            
        Returns:
            Structured metadata extracted from the document
        """
        pass
    
    @abstractmethod
    async def analyze_for_desk_rejection(
        self,
        manuscript_id: str,
        pdf_path: Path,
        journal_code: str
    ) -> "DeskRejectionAnalysis":
        """
        Analyze manuscript specifically for desk rejection decision
        
        Args:
            manuscript_id: Unique identifier for the manuscript
            pdf_path: Path to the manuscript PDF file
            journal_code: Target journal code
            
        Returns:
            Desk rejection analysis with recommendation and reasoning
        """
        pass
    
    @abstractmethod
    async def recommend_referees(
        self,
        analysis_result: AnalysisResult,
        max_recommendations: int = 10
    ) -> list["RefereeRecommendation"]:
        """
        Generate AI-powered referee recommendations
        
        Args:
            analysis_result: Complete manuscript analysis
            max_recommendations: Maximum number of referee recommendations
            
        Returns:
            List of referee recommendations sorted by score
        """
        pass
    
    @abstractmethod
    async def validate_analysis(
        self,
        analysis_id: str,
        human_feedback: Dict[str, Any]
    ) -> bool:
        """
        Record human validation of AI analysis for model improvement
        
        Args:
            analysis_id: ID of the analysis to validate
            human_feedback: Human reviewer feedback and corrections
            
        Returns:
            Success status of validation recording
        """
        pass