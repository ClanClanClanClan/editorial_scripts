"""
Optimized data models for ultimate editorial scripts system
Production-ready with validation, error handling, and performance optimization
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
from email_validator import validate_email, EmailNotValidError
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error for model validation"""
    pass


@dataclass
class OptimizedReferee:
    """Production-ready referee model with validation and optimization"""
    
    # Core required fields
    name: str
    email: str
    status: str
    
    # Institutional data
    institution: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    
    # Timeline data
    contact_date: Optional[str] = None
    due_date: Optional[str] = None
    report_date: Optional[str] = None
    declined_date: Optional[str] = None
    
    # Status booleans (computed from status)
    declined: bool = field(default=False, init=False)
    report_submitted: bool = field(default=False, init=False)
    
    # Analytics
    reminder_count: int = 0
    days_since_invited: Optional[int] = None
    
    # Technical fields
    biblio_url: Optional[str] = None
    email_verification: Dict[str, Any] = field(default_factory=dict)
    
    # Performance tracking
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and optimize data on creation"""
        self._validate_required_fields()
        self._validate_email_format()
        self._compute_status_booleans()
        self._set_computed_fields()
        self._record_extraction_metadata()
    
    def _validate_required_fields(self):
        """Validate all required fields are present and valid"""
        if not self.name or len(self.name.strip()) < 2:
            raise ValidationError(f"Invalid referee name: '{self.name}'")
        
        if not self.email or len(self.email.strip()) < 5:
            raise ValidationError(f"Invalid referee email: '{self.email}'")
        
        if not self.status:
            raise ValidationError("Referee status is required")
    
    def _validate_email_format(self):
        """Validate email format"""
        try:
            if self.email and '@' in self.email:
                # Basic validation - full validation can be expensive
                validation = validate_email(self.email.strip())
                self.email = validation.email  # Normalized email
        except EmailNotValidError as e:
            logger.warning(f"Invalid email format for {self.name}: {self.email} - {e}")
            # Don't fail completely, just log warning
    
    def _compute_status_booleans(self):
        """Compute boolean flags from status string"""
        status_lower = self.status.lower()
        
        # Declined patterns
        declined_patterns = ['declined', 'unable', 'cannot', 'not available']
        self.declined = any(pattern in status_lower for pattern in declined_patterns)
        
        # Report submitted patterns
        submitted_patterns = ['submitted', 'completed', 'report received']
        self.report_submitted = any(pattern in status_lower for pattern in submitted_patterns)
    
    def _set_computed_fields(self):
        """Set computed fields"""
        if not self.full_name:
            self.full_name = self.name
        
        # Calculate days since invited if contact_date available
        if self.contact_date:
            try:
                contact_dt = datetime.strptime(self.contact_date, '%Y-%m-%d')
                self.days_since_invited = (datetime.now() - contact_dt).days
            except ValueError:
                logger.warning(f"Invalid contact_date format: {self.contact_date}")
    
    def _record_extraction_metadata(self):
        """Record extraction metadata for debugging"""
        self.extraction_metadata.update({
            'extracted_at': datetime.now().isoformat(),
            'validation_passed': True,
            'computed_declined': self.declined,
            'computed_report_submitted': self.report_submitted
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return asdict(self)
    
    def validate_completeness(self) -> Dict[str, Any]:
        """Validate data completeness for quality metrics"""
        required_fields = ['name', 'email', 'status']
        optional_fields = ['institution', 'contact_date', 'due_date']
        
        missing_required = [f for f in required_fields if not getattr(self, f)]
        missing_optional = [f for f in optional_fields if not getattr(self, f)]
        
        completeness_score = (
            len(required_fields) - len(missing_required) + 
            len(optional_fields) - len(missing_optional)
        ) / (len(required_fields) + len(optional_fields))
        
        return {
            'completeness_score': completeness_score,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'is_complete': len(missing_required) == 0
        }


@dataclass
class OptimizedManuscript:
    """Production-ready manuscript model with validation and optimization"""
    
    # Core identifiers  
    id: str
    journal: str
    
    # Basic metadata
    title: str
    authors: List[str]
    status: str
    
    # Dates
    submission_date: Optional[str] = None
    
    # Editorial assignments
    corresponding_editor: Optional[str] = None
    associate_editor: Optional[str] = None
    
    # Referee data
    referees: List[OptimizedReferee] = field(default_factory=list)
    
    # Document management
    pdf_urls: Dict[str, str] = field(default_factory=dict)
    pdf_paths: Dict[str, str] = field(default_factory=dict)
    
    # Advanced fields
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    subject_areas: List[str] = field(default_factory=list)
    
    # Analytics
    days_in_system: Optional[int] = None
    referee_reports: Dict[str, str] = field(default_factory=dict)
    
    # Compatibility fields (for backward compatibility)
    manuscript_id: Optional[str] = field(default=None, init=False)
    submitted: Optional[str] = field(default=None, init=False)
    
    # Performance tracking
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and optimize data on creation"""
        self._validate_required_fields()
        self._validate_dates()
        self._validate_referees()
        self._set_computed_fields()
        self._record_extraction_metadata()
    
    def _validate_required_fields(self):
        """Validate all required fields are present and valid"""
        required_fields = {
            'id': self.id,
            'journal': self.journal,
            'title': self.title,
            'authors': self.authors,
            'status': self.status
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value:
                raise ValidationError(f"Missing required field: {field_name}")
            
            if field_name in ['id', 'journal', 'title', 'status']:
                if isinstance(field_value, str) and len(field_value.strip()) < 2:
                    raise ValidationError(f"Invalid {field_name}: '{field_value}'")
            
            if field_name == 'authors':
                if not isinstance(field_value, list) or len(field_value) == 0:
                    raise ValidationError(f"Authors list cannot be empty")
    
    def _validate_dates(self):
        """Validate date formats"""
        if self.submission_date:
            try:
                parsed_date = datetime.strptime(self.submission_date, '%Y-%m-%d')
                if parsed_date.date() > date.today():
                    raise ValidationError(f"Submission date cannot be in the future: {self.submission_date}")
            except ValueError:
                logger.warning(f"Invalid submission_date format: {self.submission_date}")
    
    def _validate_referees(self):
        """Validate referee list"""
        if not isinstance(self.referees, list):
            self.referees = []
        
        # Validate each referee
        valid_referees = []
        for referee in self.referees:
            if isinstance(referee, OptimizedReferee):
                valid_referees.append(referee)
            elif isinstance(referee, dict):
                try:
                    valid_referees.append(OptimizedReferee(**referee))
                except ValidationError as e:
                    logger.warning(f"Invalid referee data: {e}")
            else:
                logger.warning(f"Invalid referee type: {type(referee)}")
        
        self.referees = valid_referees
    
    def _set_computed_fields(self):
        """Set computed and compatibility fields"""
        # Backward compatibility
        self.manuscript_id = self.id
        self.submitted = self.submission_date
        
        # Calculate days in system
        if self.submission_date:
            try:
                submission_dt = datetime.strptime(self.submission_date, '%Y-%m-%d')
                self.days_in_system = (datetime.now() - submission_dt).days
            except ValueError:
                logger.warning(f"Could not calculate days_in_system from {self.submission_date}")
    
    def _record_extraction_metadata(self):
        """Record extraction metadata for debugging and quality tracking"""
        self.extraction_metadata.update({
            'extracted_at': datetime.now().isoformat(),
            'total_referees': len(self.referees),
            'referees_with_emails': sum(1 for r in self.referees if r.email),
            'validation_passed': True,
            'completeness_score': self._calculate_completeness_score()
        })
    
    def _calculate_completeness_score(self) -> float:
        """Calculate data completeness score"""
        required_fields = 5  # id, journal, title, authors, status
        optional_fields = ['submission_date', 'corresponding_editor', 'associate_editor', 'abstract']
        
        optional_present = sum(1 for field in optional_fields if getattr(self, field))
        referee_completeness = sum(r.validate_completeness()['completeness_score'] for r in self.referees)
        avg_referee_completeness = referee_completeness / len(self.referees) if self.referees else 0
        
        return (required_fields + optional_present + avg_referee_completeness) / (required_fields + len(optional_fields) + 1)
    
    def add_referee(self, referee: Union[OptimizedReferee, Dict[str, Any]]) -> bool:
        """Add a referee with duplicate checking"""
        if isinstance(referee, dict):
            try:
                referee = OptimizedReferee(**referee)
            except ValidationError as e:
                logger.warning(f"Cannot add invalid referee: {e}")
                return False
        
        # Check for duplicates
        existing_emails = {r.email.lower() for r in self.referees if r.email}
        existing_names = {r.name.lower() for r in self.referees}
        
        if referee.email.lower() in existing_emails:
            logger.debug(f"Duplicate referee email: {referee.email}")
            return False
        
        if referee.name.lower() in existing_names:
            logger.debug(f"Duplicate referee name: {referee.name}")
            return False
        
        self.referees.append(referee)
        return True
    
    def get_referee_by_email(self, email: str) -> Optional[OptimizedReferee]:
        """Get referee by email address"""
        email_lower = email.lower()
        for referee in self.referees:
            if referee.email.lower() == email_lower:
                return referee
        return None
    
    def get_referee_by_name(self, name: str) -> Optional[OptimizedReferee]:
        """Get referee by name"""
        name_lower = name.lower()
        for referee in self.referees:
            if referee.name.lower() == name_lower:
                return referee
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        result = asdict(self)
        # Ensure referees are properly serialized
        result['referees'] = [referee.to_dict() for referee in self.referees]
        return result
    
    def validate_quality(self) -> Dict[str, Any]:
        """Comprehensive quality validation"""
        quality_report = {
            'overall_score': self._calculate_completeness_score(),
            'manuscript_completeness': self._validate_manuscript_completeness(),
            'referee_quality': self._validate_referee_quality(),
            'data_consistency': self._validate_data_consistency(),
            'issues': []
        }
        
        return quality_report
    
    def _validate_manuscript_completeness(self) -> Dict[str, Any]:
        """Validate manuscript data completeness"""
        required = ['id', 'title', 'authors', 'status']
        important = ['submission_date', 'corresponding_editor', 'associate_editor']
        
        missing_required = [f for f in required if not getattr(self, f)]
        missing_important = [f for f in important if not getattr(self, f)]
        
        return {
            'score': (len(required) - len(missing_required)) / len(required),
            'missing_required': missing_required,
            'missing_important': missing_important
        }
    
    def _validate_referee_quality(self) -> Dict[str, Any]:
        """Validate referee data quality"""
        if not self.referees:
            return {'score': 0, 'issues': ['No referees found']}
        
        referee_scores = [r.validate_completeness()['completeness_score'] for r in self.referees]
        avg_score = sum(referee_scores) / len(referee_scores)
        
        issues = []
        referees_without_email = [r.name for r in self.referees if not r.email]
        if referees_without_email:
            issues.append(f"Referees without email: {referees_without_email}")
        
        return {
            'score': avg_score,
            'total_referees': len(self.referees),
            'referees_with_emails': sum(1 for r in self.referees if r.email),
            'issues': issues
        }
    
    def _validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency"""
        issues = []
        
        # Check date consistency
        if self.submission_date:
            try:
                submission_dt = datetime.strptime(self.submission_date, '%Y-%m-%d')
                if submission_dt.date() > date.today():
                    issues.append("Submission date is in the future")
            except ValueError:
                issues.append("Invalid submission date format")
        
        # Check referee consistency
        for referee in self.referees:
            if referee.contact_date and self.submission_date:
                try:
                    contact_dt = datetime.strptime(referee.contact_date, '%Y-%m-%d')
                    submission_dt = datetime.strptime(self.submission_date, '%Y-%m-%d')
                    if contact_dt < submission_dt:
                        issues.append(f"Referee {referee.name} contacted before submission")
                except ValueError:
                    pass  # Already logged in individual validation
        
        return {
            'score': 1.0 if not issues else 0.8,
            'issues': issues
        }


@dataclass  
class OptimizedExtractionResult:
    """Production-ready extraction result with comprehensive metrics"""
    
    # Basic info
    journal: str
    session_id: str
    extraction_time: str
    
    # Results
    manuscripts: List[OptimizedManuscript]
    
    # Statistics (computed)
    total_manuscripts: int = field(default=0, init=False)
    total_referees: int = field(default=0, init=False)
    referees_with_emails: int = field(default=0, init=False)
    pdfs_downloaded: int = field(default=0, init=False)
    
    # Quality metrics
    overall_quality_score: float = field(default=0.0, init=False)
    referee_status_breakdown: Dict[str, int] = field(default_factory=dict, init=False)
    
    # Performance metrics
    extraction_duration_seconds: float = field(default=0.0, init=False)
    performance_metrics: Dict[str, Any] = field(default_factory=dict, init=False)
    
    # Quality analysis
    quality_report: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __post_init__(self):
        """Compute all statistics and metrics"""
        self._compute_basic_statistics()
        self._compute_quality_metrics()
        self._compute_performance_metrics()
        self._generate_quality_report()
    
    def _compute_basic_statistics(self):
        """Compute basic statistics"""
        self.total_manuscripts = len(self.manuscripts)
        
        all_referees = []
        pdfs_count = 0
        
        for manuscript in self.manuscripts:
            all_referees.extend(manuscript.referees)
            pdfs_count += len(manuscript.pdf_paths)
        
        self.total_referees = len(all_referees)
        self.referees_with_emails = sum(1 for r in all_referees if r.email)
        self.pdfs_downloaded = pdfs_count
        
        # Referee status breakdown
        status_counts = {}
        for referee in all_referees:
            status = referee.status
            status_counts[status] = status_counts.get(status, 0) + 1
        self.referee_status_breakdown = status_counts
    
    def _compute_quality_metrics(self):
        """Compute quality metrics"""
        if not self.manuscripts:
            self.overall_quality_score = 0.0
            return
        
        manuscript_scores = [m.validate_quality()['overall_score'] for m in self.manuscripts]
        self.overall_quality_score = sum(manuscript_scores) / len(manuscript_scores)
    
    def _compute_performance_metrics(self):
        """Compute performance metrics"""
        try:
            extraction_dt = datetime.fromisoformat(self.extraction_time)
            current_time = datetime.now()
            self.extraction_duration_seconds = (current_time - extraction_dt).total_seconds()
        except ValueError:
            self.extraction_duration_seconds = 0.0
        
        self.performance_metrics = {
            'manuscripts_per_minute': self.total_manuscripts / max(self.extraction_duration_seconds / 60, 1),
            'referees_per_minute': self.total_referees / max(self.extraction_duration_seconds / 60, 1),
            'pdfs_per_minute': self.pdfs_downloaded / max(self.extraction_duration_seconds / 60, 1),
            'average_referees_per_manuscript': self.total_referees / max(self.total_manuscripts, 1)
        }
    
    def _generate_quality_report(self):
        """Generate comprehensive quality report"""
        self.quality_report = {
            'extraction_success': True,
            'overall_score': self.overall_quality_score,
            'data_completeness': {
                'manuscripts_with_titles': sum(1 for m in self.manuscripts if m.title),
                'manuscripts_with_authors': sum(1 for m in self.manuscripts if m.authors),
                'manuscripts_with_dates': sum(1 for m in self.manuscripts if m.submission_date),
                'referees_with_emails': self.referees_with_emails,
                'total_referees': self.total_referees
            },
            'performance_summary': {
                'total_time_seconds': self.extraction_duration_seconds,
                'manuscripts_found': self.total_manuscripts,
                'pdfs_downloaded': self.pdfs_downloaded,
                'success_rate': self._calculate_success_rate()
            }
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        if not self.manuscripts:
            return 0.0
        
        # Success criteria: manuscripts with basic data + some referees + some PDFs
        successful_manuscripts = 0
        for manuscript in self.manuscripts:
            has_basic_data = manuscript.title and manuscript.authors and manuscript.status
            has_referees = len(manuscript.referees) > 0
            # PDFs not required for success but preferred
            
            if has_basic_data and has_referees:
                successful_manuscripts += 1
        
        return successful_manuscripts / self.total_manuscripts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        result = asdict(self)
        # Ensure manuscripts are properly serialized
        result['manuscripts'] = [manuscript.to_dict() for manuscript in self.manuscripts]
        return result
    
    def save_to_file(self, file_path: Union[str, Path]):
        """Save extraction result to JSON file with error handling"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Extraction result saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save extraction result: {e}")
            raise
    
    @classmethod
    def create_from_manuscripts(cls, journal: str, manuscripts: List[OptimizedManuscript]) -> 'OptimizedExtractionResult':
        """Create extraction result from list of manuscripts"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        extraction_time = datetime.now().isoformat()
        
        return cls(
            journal=journal,
            session_id=session_id,
            extraction_time=extraction_time,
            manuscripts=manuscripts
        )
    
    def meets_baseline_criteria(self, baseline: Dict[str, int]) -> Dict[str, Any]:
        """Check if extraction meets baseline criteria (e.g., July 11 baseline)"""
        results = {
            'meets_criteria': True,
            'criteria_analysis': {},
            'issues': []
        }
        
        for criterion, expected_value in baseline.items():
            actual_value = getattr(self, criterion, 0)
            meets_criterion = actual_value >= expected_value
            
            results['criteria_analysis'][criterion] = {
                'expected': expected_value,
                'actual': actual_value,
                'meets': meets_criterion,
                'percentage': (actual_value / expected_value * 100) if expected_value > 0 else 100
            }
            
            if not meets_criterion:
                results['meets_criteria'] = False
                results['issues'].append(f"{criterion}: expected {expected_value}, got {actual_value}")
        
        return results