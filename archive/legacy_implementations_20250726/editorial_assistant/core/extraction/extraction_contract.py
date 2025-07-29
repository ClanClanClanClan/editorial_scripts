"""
Extraction Contract Definition

Defines the standard contract that all journal extractors must fulfill,
ensuring consistent data extraction across all platforms.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import (
    ExtractionResult, 
    ExtractionStatus, 
    ExtractionMetadata,
    QualityScore,
    DataQualityMetrics
)
from .validation import ValidationResult, QualityValidator
from ..data_models import Manuscript, Referee


class ExtractionContract:
    """
    Standard extraction contract that defines what data must be extracted
    from each journal and validates extraction quality.
    
    This contract ensures consistent behavior across all journal extractors
    and provides quality metrics for system reliability.
    """
    
    def __init__(self, journal_code: str, journal_name: str, 
                 minimum_quality_threshold: float = 0.7):
        """
        Initialize extraction contract.
        
        Args:
            journal_code: Journal code (e.g., 'SICON', 'MF')
            journal_name: Full journal name
            minimum_quality_threshold: Minimum acceptable quality score
        """
        self.journal_code = journal_code
        self.journal_name = journal_name
        self.minimum_quality_threshold = minimum_quality_threshold
        
        # Initialize components
        self.validator = QualityValidator()
        self.metadata = self._create_metadata()
        
        # Track extraction progress
        self._extraction_started = False
        self._extraction_completed = False
    
    def _create_metadata(self) -> ExtractionMetadata:
        """Create extraction metadata."""
        return ExtractionMetadata(
            journal_code=self.journal_code,
            journal_name=self.journal_name,
            extraction_id=str(uuid.uuid4()),
            started_at=datetime.now()
        )
    
    def begin_extraction(self, config: Dict[str, Any] = None) -> None:
        """
        Begin extraction process.
        
        Args:
            config: Extraction configuration parameters
        """
        if self._extraction_started:
            raise RuntimeError("Extraction already started")
        
        self._extraction_started = True
        self.metadata.started_at = datetime.now()
        self.metadata.extraction_config = config or {}
        self.metadata.add_action("Extraction process started")
    
    def complete_extraction(self) -> None:
        """Complete extraction process."""
        if not self._extraction_started:
            raise RuntimeError("Extraction not started")
        
        self._extraction_completed = True
        self.metadata.completed_at = datetime.now()
        
        # Calculate duration
        if self.metadata.started_at and self.metadata.completed_at:
            duration = self.metadata.completed_at - self.metadata.started_at
            self.metadata.duration_seconds = duration.total_seconds()
        
        self.metadata.add_action("Extraction process completed")
    
    def create_result(self, manuscripts: List[Manuscript], 
                     referees: List[Referee] = None,
                     pdfs: List[Path] = None,
                     errors: List[str] = None) -> ExtractionResult:
        """
        Create extraction result with validation.
        
        Args:
            manuscripts: List of extracted manuscripts
            referees: List of extracted referees (if separate from manuscripts)
            pdfs: List of downloaded PDF files
            errors: List of errors encountered
            
        Returns:
            ExtractionResult with quality validation
        """
        # Ensure extraction is properly tracked
        if not self._extraction_started:
            self.begin_extraction()
        
        if not self._extraction_completed:
            self.complete_extraction()
        
        # Create result object
        result = ExtractionResult(
            manuscripts=manuscripts or [],
            referees=referees or [],
            pdfs=pdfs or [],
            errors=errors or [],
            metadata=self.metadata
        )
        
        # Calculate metrics
        result.metrics = self._calculate_metrics(result)
        
        # Calculate quality score
        result.quality_score = self._calculate_quality_score(result)
        
        # Determine extraction status
        result.status = self._determine_status(result)
        
        # Validate result
        validation_result = self.validate(result)
        if not validation_result.is_valid:
            result.add_warning(f"Validation issues: {validation_result.message}")
        
        return result
    
    def _calculate_metrics(self, result: ExtractionResult) -> DataQualityMetrics:
        """
        Calculate detailed metrics for extraction result.
        
        Args:
            result: Extraction result to analyze
            
        Returns:
            DataQualityMetrics with detailed statistics
        """
        metrics = DataQualityMetrics()
        
        # Basic counts
        metrics.total_manuscripts_found = len(result.manuscripts)
        metrics.total_manuscripts_processed = len(result.manuscripts)
        metrics.total_pdfs_downloaded = len(result.pdfs)
        
        # Analyze manuscripts for referee data
        total_referees = 0
        referees_with_emails = 0
        manuscripts_with_complete_data = 0
        manuscripts_with_pdfs = 0
        
        for manuscript in result.manuscripts:
            # Count referees
            if hasattr(manuscript, 'referees') and manuscript.referees:
                manuscript_referees = len(manuscript.referees)
                total_referees += manuscript_referees
                
                # Count referees with emails
                for referee in manuscript.referees:
                    if hasattr(referee, 'email') and referee.email:
                        referees_with_emails += 1
            
            # Check if manuscript has complete data
            if self._has_complete_manuscript_data(manuscript):
                manuscripts_with_complete_data += 1
            
            # Check if manuscript has PDF
            if hasattr(manuscript, 'pdf_path') and manuscript.pdf_path:
                manuscripts_with_pdfs += 1
        
        metrics.total_referees_found = total_referees
        metrics.total_referees_with_emails = referees_with_emails
        metrics.manuscripts_with_complete_data = manuscripts_with_complete_data
        metrics.manuscripts_with_pdfs = manuscripts_with_pdfs
        
        # Error counts
        metrics.authentication_errors = sum(1 for e in result.errors if 'auth' in e.lower())
        metrics.navigation_errors = sum(1 for e in result.errors if 'nav' in e.lower())
        metrics.parsing_errors = sum(1 for e in result.errors if 'pars' in e.lower())
        metrics.download_errors = sum(1 for e in result.errors if 'download' in e.lower())
        
        # Timing
        if result.metadata:
            metrics.total_extraction_time = result.metadata.duration_seconds
            if metrics.total_manuscripts_processed > 0:
                metrics.average_manuscript_time = (
                    metrics.total_extraction_time / metrics.total_manuscripts_processed
                )
        
        return metrics
    
    def _has_complete_manuscript_data(self, manuscript: Manuscript) -> bool:
        """
        Check if manuscript has complete data.
        
        Args:
            manuscript: Manuscript object to check
            
        Returns:
            True if manuscript has complete essential data
        """
        # Required fields
        if not manuscript.manuscript_id:
            return False
        
        # Check for title (optional but preferred)
        has_title = hasattr(manuscript, 'title') and manuscript.title
        
        # Check for referee data
        has_referees = (
            hasattr(manuscript, 'referees') and 
            manuscript.referees and 
            len(manuscript.referees) > 0
        )
        
        # Consider complete if has ID and either title or referees
        return has_title or has_referees
    
    def _calculate_quality_score(self, result: ExtractionResult) -> QualityScore:
        """
        Calculate quality score for extraction result.
        
        Args:
            result: Extraction result to score
            
        Returns:
            QualityScore with detailed quality metrics
        """
        score = QualityScore()
        metrics = result.metrics
        
        # Manuscript completeness
        if metrics.total_manuscripts_found > 0:
            score.manuscript_completeness = (
                metrics.manuscripts_with_complete_data / metrics.total_manuscripts_found
            )
        
        # Referee completeness  
        if metrics.total_referees_found > 0:
            score.referee_completeness = (
                metrics.total_referees_with_emails / metrics.total_referees_found
            )
        
        # PDF success rate
        if metrics.total_manuscripts_found > 0:
            score.pdf_success_rate = (
                metrics.manuscripts_with_pdfs / metrics.total_manuscripts_found
            )
        
        # Data integrity (based on error rates)
        total_operations = metrics.total_manuscripts_processed + metrics.total_pdfs_downloaded
        total_errors = (
            metrics.authentication_errors + 
            metrics.navigation_errors + 
            metrics.parsing_errors + 
            metrics.download_errors
        )
        
        if total_operations > 0:
            error_rate = total_errors / total_operations
            score.data_integrity = max(0.0, 1.0 - error_rate)
        else:
            score.data_integrity = 1.0
        
        # Quality indicators
        score.has_referee_emails = metrics.total_referees_with_emails > 0
        score.has_manuscript_pdfs = metrics.manuscripts_with_pdfs > 0
        score.has_referee_reports = any(
            hasattr(m, 'referees') and m.referees and
            any(hasattr(r, 'report') and r.report for r in m.referees)
            for m in result.manuscripts
        )
        score.has_complete_dates = any(
            hasattr(m, 'referees') and m.referees and
            any(hasattr(r, 'dates') and r.dates for r in m.referees)
            for m in result.manuscripts
        )
        
        # Error indicators
        score.authentication_issues = metrics.authentication_errors > 0
        score.navigation_issues = metrics.navigation_errors > 0
        score.parsing_issues = metrics.parsing_errors > 0
        score.download_issues = metrics.download_errors > 0
        
        # Calculate overall score
        score.calculate_overall_score()
        
        return score
    
    def _determine_status(self, result: ExtractionResult) -> ExtractionStatus:
        """
        Determine extraction status based on results.
        
        Args:
            result: Extraction result to analyze
            
        Returns:
            ExtractionStatus enum value
        """
        # Check for critical failures
        if result.metrics.authentication_errors > 0:
            return ExtractionStatus.AUTH_FAILED
        
        # Check if we got any usable data
        if not result.has_usable_data():
            return ExtractionStatus.FAILED
        
        # Check quality score
        if result.quality_score.overall_score >= self.minimum_quality_threshold:
            return ExtractionStatus.SUCCESS
        elif result.quality_score.overall_score >= 0.3:
            return ExtractionStatus.PARTIAL_SUCCESS
        else:
            return ExtractionStatus.FAILED
    
    def validate(self, result: ExtractionResult) -> ValidationResult:
        """
        Validate extraction result against contract requirements.
        
        Args:
            result: Extraction result to validate
            
        Returns:
            ValidationResult with validation details
        """
        return self.validator.validate_extraction_result(
            result, 
            self.minimum_quality_threshold
        )
    
    def get_requirements(self) -> Dict[str, Any]:
        """
        Get extraction requirements for this contract.
        
        Returns:
            Dictionary defining extraction requirements
        """
        return {
            'journal_code': self.journal_code,
            'journal_name': self.journal_name,
            'minimum_quality_threshold': self.minimum_quality_threshold,
            'required_data': {
                'manuscripts': {
                    'required': True,
                    'minimum_count': 1,
                    'required_fields': ['manuscript_id']
                },
                'referees': {
                    'required': True,
                    'minimum_count': 1,
                    'required_fields': ['name'],
                    'preferred_fields': ['email', 'institution']
                },
                'pdfs': {
                    'required': False,
                    'minimum_count': 0,
                    'preferred': True
                }
            },
            'quality_requirements': {
                'minimum_manuscript_completeness': 0.8,
                'minimum_referee_completeness': 0.6,
                'minimum_data_integrity': 0.9,
                'preferred_pdf_success_rate': 0.7
            }
        }