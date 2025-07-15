"""
Extraction Result Models

Defines standardized data models for extraction results,
quality metrics, and status tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path


class ExtractionStatus(Enum):
    """Extraction status enumeration."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    AUTH_FAILED = "auth_failed"


@dataclass
class QualityScore:
    """
    Quality scoring for extraction results.
    
    Provides objective metrics for assessing extraction completeness
    and accuracy across all journal platforms.
    """
    
    # Overall quality score (0.0 - 1.0)
    overall_score: float = 0.0
    
    # Component scores
    manuscript_completeness: float = 0.0  # Did we get all expected manuscripts?
    referee_completeness: float = 0.0     # Did we get all referee data?
    pdf_success_rate: float = 0.0         # Percentage of PDFs successfully downloaded
    data_integrity: float = 0.0           # Are the extracted data consistent?
    
    # Quality indicators
    has_referee_emails: bool = False      # Do we have referee email addresses?
    has_manuscript_pdfs: bool = False     # Do we have manuscript PDFs?
    has_referee_reports: bool = False     # Do we have referee review reports?
    has_complete_dates: bool = False      # Do we have complete date information?
    
    # Error indicators
    authentication_issues: bool = False
    navigation_issues: bool = False
    parsing_issues: bool = False
    download_issues: bool = False
    
    def calculate_overall_score(self) -> float:
        """
        Calculate overall quality score based on component scores.
        
        Returns:
            Overall quality score between 0.0 and 1.0
        """
        # Base score from component averages
        component_scores = [
            self.manuscript_completeness,
            self.referee_completeness,
            self.pdf_success_rate,
            self.data_integrity
        ]
        
        base_score = sum(component_scores) / len(component_scores)
        
        # Bonus points for quality indicators
        bonus = 0.0
        if self.has_referee_emails:
            bonus += 0.1
        if self.has_manuscript_pdfs:
            bonus += 0.1
        if self.has_referee_reports:
            bonus += 0.05
        if self.has_complete_dates:
            bonus += 0.05
        
        # Penalties for issues
        penalty = 0.0
        if self.authentication_issues:
            penalty += 0.2
        if self.navigation_issues:
            penalty += 0.1
        if self.parsing_issues:
            penalty += 0.1
        if self.download_issues:
            penalty += 0.05
        
        # Calculate final score
        final_score = min(1.0, max(0.0, base_score + bonus - penalty))
        self.overall_score = final_score
        
        return final_score


@dataclass
class DataQualityMetrics:
    """
    Detailed data quality metrics for analysis.
    """
    
    # Count metrics
    total_manuscripts_found: int = 0
    total_manuscripts_processed: int = 0
    total_referees_found: int = 0
    total_referees_with_emails: int = 0
    total_pdfs_attempted: int = 0
    total_pdfs_downloaded: int = 0
    
    # Quality metrics
    manuscripts_with_complete_data: int = 0
    referees_with_complete_data: int = 0
    manuscripts_with_pdfs: int = 0
    referees_with_reports: int = 0
    
    # Error tracking
    authentication_errors: int = 0
    navigation_errors: int = 0
    parsing_errors: int = 0
    download_errors: int = 0
    validation_errors: int = 0
    
    # Timing metrics
    total_extraction_time: float = 0.0
    average_manuscript_time: float = 0.0
    authentication_time: float = 0.0
    navigation_time: float = 0.0
    
    def calculate_success_rates(self) -> Dict[str, float]:
        """
        Calculate various success rates from metrics.
        
        Returns:
            Dictionary of success rate percentages
        """
        rates = {}
        
        # Manuscript processing rate
        if self.total_manuscripts_found > 0:
            rates['manuscript_processing_rate'] = (
                self.total_manuscripts_processed / self.total_manuscripts_found
            )
        
        # PDF download rate
        if self.total_pdfs_attempted > 0:
            rates['pdf_download_rate'] = (
                self.total_pdfs_downloaded / self.total_pdfs_attempted
            )
        
        # Email extraction rate
        if self.total_referees_found > 0:
            rates['email_extraction_rate'] = (
                self.total_referees_with_emails / self.total_referees_found
            )
        
        # Data completeness rate
        if self.total_manuscripts_processed > 0:
            rates['manuscript_completeness_rate'] = (
                self.manuscripts_with_complete_data / self.total_manuscripts_processed
            )
        
        if self.total_referees_found > 0:
            rates['referee_completeness_rate'] = (
                self.referees_with_complete_data / self.total_referees_found
            )
        
        return rates


@dataclass
class ExtractionMetadata:
    """
    Metadata about the extraction process.
    """
    
    # Basic info
    journal_code: str
    journal_name: str
    extraction_id: str
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # System info
    extractor_version: str = "2.0.0"
    browser_type: str = "undetected_chrome"
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration
    extraction_config: Dict[str, Any] = field(default_factory=dict)
    journal_config: Dict[str, Any] = field(default_factory=dict)
    
    # Processing details
    pages_visited: List[str] = field(default_factory=list)
    actions_performed: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    
    def add_action(self, action: str) -> None:
        """Add an action to the processing log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.actions_performed.append(f"[{timestamp}] {action}")
    
    def add_error(self, error: str) -> None:
        """Add an error to the error log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.errors_encountered.append(f"[{timestamp}] {error}")
    
    def add_page_visit(self, url: str) -> None:
        """Add a page visit to the navigation log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.pages_visited.append(f"[{timestamp}] {url}")


@dataclass
class ExtractionResult:
    """
    Complete extraction result with all data and metadata.
    
    This is the standard container for all extraction outputs,
    ensuring consistent data structure across all journal platforms.
    """
    
    # Core data (from existing data_models.py)
    manuscripts: List[Any] = field(default_factory=list)  # List[Manuscript]
    referees: List[Any] = field(default_factory=list)     # List[Referee] 
    pdfs: List[Path] = field(default_factory=list)        # List[PDFDocument]
    
    # Status and quality
    status: ExtractionStatus = ExtractionStatus.FAILED
    quality_score: QualityScore = field(default_factory=QualityScore)
    metrics: DataQualityMetrics = field(default_factory=DataQualityMetrics)
    metadata: Optional[ExtractionMetadata] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Output files
    output_directory: Optional[Path] = None
    raw_data_file: Optional[Path] = None
    report_file: Optional[Path] = None
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        if self.metadata:
            self.metadata.add_error(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def is_success(self) -> bool:
        """Check if extraction was successful."""
        return self.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL_SUCCESS]
    
    def has_usable_data(self) -> bool:
        """Check if result contains usable data."""
        return (
            len(self.manuscripts) > 0 or 
            len(self.referees) > 0 or
            len(self.pdfs) > 0
        )
    
    def calculate_summary_stats(self) -> Dict[str, Any]:
        """
        Calculate summary statistics for the extraction.
        
        Returns:
            Dictionary containing key statistics
        """
        total_referees = sum(len(m.referees) if hasattr(m, 'referees') else 0 for m in self.manuscripts)
        referees_with_emails = sum(
            1 for m in self.manuscripts 
            if hasattr(m, 'referees')
            for r in m.referees 
            if hasattr(r, 'email') and r.email
        )
        
        return {
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': referees_with_emails,
            'total_pdfs': len(self.pdfs),
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'quality_score': self.quality_score.overall_score,
            'status': self.status.value,
            'duration_seconds': self.metadata.duration_seconds if self.metadata else 0.0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert extraction result to dictionary for serialization.
        
        Returns:
            Dictionary representation of extraction result
        """
        return {
            'metadata': {
                'journal_code': self.metadata.journal_code if self.metadata else '',
                'extraction_id': self.metadata.extraction_id if self.metadata else '',
                'started_at': self.metadata.started_at.isoformat() if self.metadata else '',
                'completed_at': self.metadata.completed_at.isoformat() if self.metadata and self.metadata.completed_at else '',
                'duration_seconds': self.metadata.duration_seconds if self.metadata else 0.0
            },
            'status': self.status.value,
            'summary': self.calculate_summary_stats(),
            'quality_score': {
                'overall_score': self.quality_score.overall_score,
                'manuscript_completeness': self.quality_score.manuscript_completeness,
                'referee_completeness': self.quality_score.referee_completeness,
                'pdf_success_rate': self.quality_score.pdf_success_rate,
                'data_integrity': self.quality_score.data_integrity
            },
            'metrics': {
                'total_manuscripts_found': self.metrics.total_manuscripts_found,
                'total_manuscripts_processed': self.metrics.total_manuscripts_processed,
                'total_referees_found': self.metrics.total_referees_found,
                'total_referees_with_emails': self.metrics.total_referees_with_emails,
                'total_pdfs_downloaded': self.metrics.total_pdfs_downloaded,
                'success_rates': self.metrics.calculate_success_rates()
            },
            'errors': self.errors,
            'warnings': self.warnings
        }