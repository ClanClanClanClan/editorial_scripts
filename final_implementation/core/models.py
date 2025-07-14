"""
Core data models for editorial scripts
Optimized, clean implementation based on working July 11 system
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class Referee:
    """Referee information with all necessary fields"""
    name: str
    email: str
    status: str = "Unknown"
    institution: Optional[str] = None
    report_submitted: Optional[bool] = False
    report_date: Optional[str] = None
    reminder_count: int = 0
    days_since_invited: Optional[int] = None
    
    # Additional fields for compatibility with July 11 system
    full_name: Optional[str] = None
    sicon_invited_date: Optional[str] = None
    due_date: Optional[str] = None
    declined: Optional[bool] = False
    declined_date: Optional[str] = None
    contact_date: Optional[str] = None
    biblio_url: Optional[str] = None
    
    # Email verification data
    email_verification: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize computed fields"""
        if self.email_verification is None:
            self.email_verification = {}
        
        # Set full_name from name if not provided
        if not self.full_name:
            self.full_name = self.name


@dataclass
class Manuscript:
    """Manuscript information with all necessary fields"""
    id: str
    title: str
    authors: List[str]
    status: str
    submission_date: Optional[str] = None
    journal: Optional[str] = None
    corresponding_editor: Optional[str] = None
    associate_editor: Optional[str] = None
    referees: List[Referee] = None
    pdf_urls: Dict[str, str] = None
    pdf_paths: Dict[str, str] = None
    referee_reports: Dict[str, str] = None
    
    # Additional fields for compatibility with July 11 system
    submitted: Optional[str] = None
    days_in_system: Optional[str] = None
    manuscript_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.referees is None:
            self.referees = []
        if self.pdf_urls is None:
            self.pdf_urls = {}
        if self.pdf_paths is None:
            self.pdf_paths = {}
        if self.referee_reports is None:
            self.referee_reports = {}
        
        # Set manuscript_id from id for compatibility
        if not self.manuscript_id:
            self.manuscript_id = self.id
        
        # Set submitted from submission_date for compatibility
        if not self.submitted and self.submission_date:
            self.submitted = self.submission_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert manuscript to dictionary for JSON serialization"""
        result = asdict(self)
        
        # Convert referees to dictionaries
        result['referees'] = [asdict(ref) for ref in self.referees]
        
        return result
    
    def add_referee(self, referee: Referee):
        """Add a referee to the manuscript"""
        # Check for duplicates
        existing_emails = {ref.email for ref in self.referees if ref.email}
        existing_names = {ref.name for ref in self.referees}
        
        if referee.email and referee.email in existing_emails:
            return  # Duplicate email
        if referee.name in existing_names:
            return  # Duplicate name
        
        self.referees.append(referee)
    
    def get_referee_by_email(self, email: str) -> Optional[Referee]:
        """Get referee by email address"""
        for ref in self.referees:
            if ref.email == email:
                return ref
        return None
    
    def get_referee_by_name(self, name: str) -> Optional[Referee]:
        """Get referee by name"""
        for ref in self.referees:
            if ref.name == name:
                return ref
        return None


@dataclass
class ExtractionResult:
    """Complete extraction result with statistics"""
    journal: str
    session_id: str
    extraction_time: str
    total_manuscripts: int
    manuscripts: List[Manuscript]
    total_referees: int
    referees_with_emails: int
    pdfs_downloaded: int
    
    # Additional statistics
    referee_status_breakdown: Dict[str, int] = None
    email_verification_summary: Dict[str, Any] = None
    
    def __post_init__(self):
        """Compute statistics"""
        if self.referee_status_breakdown is None:
            self.referee_status_breakdown = {}
        if self.email_verification_summary is None:
            self.email_verification_summary = {}
        
        # Compute referee statistics
        self._compute_referee_stats()
    
    def _compute_referee_stats(self):
        """Compute referee statistics"""
        status_counts = {}
        referees_with_emails = 0
        
        for manuscript in self.manuscripts:
            for referee in manuscript.referees:
                # Count statuses
                status = referee.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count emails
                if referee.email:
                    referees_with_emails += 1
        
        self.referee_status_breakdown = status_counts
        self.referees_with_emails = referees_with_emails
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        result = asdict(self)
        
        # Convert manuscripts to dictionaries
        result['manuscripts'] = [ms.to_dict() for ms in self.manuscripts]
        
        return result
    
    def save_to_file(self, file_path: str):
        """Save extraction result to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def create_from_manuscripts(cls, journal: str, manuscripts: List[Manuscript]) -> 'ExtractionResult':
        """Create extraction result from list of manuscripts"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        extraction_time = datetime.now().isoformat()
        
        total_manuscripts = len(manuscripts)
        total_referees = sum(len(ms.referees) for ms in manuscripts)
        pdfs_downloaded = sum(len(ms.pdf_paths) for ms in manuscripts)
        
        return cls(
            journal=journal,
            session_id=session_id,
            extraction_time=extraction_time,
            total_manuscripts=total_manuscripts,
            manuscripts=manuscripts,
            total_referees=total_referees,
            referees_with_emails=0,  # Will be computed in __post_init__
            pdfs_downloaded=pdfs_downloaded
        )