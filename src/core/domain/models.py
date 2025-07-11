"""
Domain models for Editorial Scripts system
Pure Python classes with no external dependencies
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum


class ManuscriptStatus(Enum):
    """Manuscript status enumeration"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    AWAITING_REFEREE = "awaiting_referee"
    AWAITING_REVISION = "awaiting_revision"
    REVISED = "revised"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RefereeStatus(Enum):
    """Referee invitation/review status"""
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    NO_RESPONSE = "no_response"


class ReviewQuality(Enum):
    """Review quality rating"""
    EXCELLENT = "excellent"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


@dataclass
class Author:
    """Author information"""
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    is_corresponding: bool = False


@dataclass
class Referee:
    """Referee (reviewer) information"""
    name: str
    email: str
    id: UUID = field(default_factory=uuid4)
    institution: Optional[str] = None
    expertise_areas: List[str] = field(default_factory=list)
    h_index: Optional[int] = None
    total_reviews: int = 0
    active_reviews: int = 0
    average_review_days: Optional[float] = None
    reliability_score: Optional[float] = None


@dataclass
class Review:
    """Review/referee report"""
    referee_id: UUID
    manuscript_id: UUID
    status: RefereeStatus
    invited_date: datetime
    id: UUID = field(default_factory=uuid4)
    responded_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    submitted_date: Optional[datetime] = None
    quality_score: Optional[ReviewQuality] = None
    report_text: Optional[str] = None
    recommendation: Optional[str] = None
    confidence_level: Optional[str] = None
    pdf_path: Optional[str] = None


@dataclass
class Manuscript:
    """Core manuscript entity"""
    journal_code: str
    external_id: str  # Journal's manuscript ID (e.g., "SICON-2024-0123")
    title: str
    id: UUID = field(default_factory=uuid4)
    abstract: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    submission_date: datetime = field(default_factory=datetime.now)
    status: ManuscriptStatus = ManuscriptStatus.SUBMITTED
    current_round: int = 1
    editor_name: Optional[str] = None
    associate_editor_name: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    page_count: Optional[int] = None
    pdf_path: Optional[str] = None
    
    # Relationships
    reviews: List[Review] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_review(self, review: Review) -> None:
        """Add a review to this manuscript"""
        if review.manuscript_id != self.id:
            raise ValueError("Review manuscript_id does not match")
        self.reviews.append(review)
        self.updated_at = datetime.now()
    
    def get_active_reviews(self) -> List[Review]:
        """Get all active (pending) reviews"""
        return [r for r in self.reviews if r.status in [
            RefereeStatus.INVITED, 
            RefereeStatus.ACCEPTED
        ]]
    
    def get_completed_reviews(self) -> List[Review]:
        """Get all completed reviews"""
        return [r for r in self.reviews if r.status == RefereeStatus.COMPLETED]
    
    def is_review_complete(self) -> bool:
        """Check if all reviews for current round are complete"""
        active_reviews = self.get_active_reviews()
        completed_reviews = self.get_completed_reviews()
        
        # Typically need at least 2 reviews
        return len(active_reviews) == 0 and len(completed_reviews) >= 2


@dataclass
class JournalConfiguration:
    """Journal-specific configuration"""
    code: str
    name: str
    url: str
    platform: str  # "scholarone", "editorial_manager", "siam"
    requires_2fa: bool = False
    min_reviews_required: int = 2
    review_deadline_days: int = 30
    reminder_schedule_days: List[int] = field(default_factory=lambda: [7, 14, 21])
    
    # Feature flags
    supports_bulk_download: bool = False
    supports_email_extraction: bool = False
    supports_api_access: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExtractionResult:
    """Result of a journal data extraction"""
    journal_code: str
    started_at: datetime
    id: UUID = field(default_factory=uuid4)
    completed_at: Optional[datetime] = None
    success: bool = False
    manuscripts_count: int = 0
    referees_count: int = 0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate extraction duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class RefereeStatistics:
    """Aggregated referee statistics"""
    referee_id: UUID
    total_invitations: int = 0
    accepted_invitations: int = 0
    declined_invitations: int = 0
    completed_reviews: int = 0
    average_response_days: Optional[float] = None
    average_review_days: Optional[float] = None
    on_time_percentage: Optional[float] = None
    journals_reviewed_for: List[str] = field(default_factory=list)
    last_review_date: Optional[datetime] = None
    quality_scores: List[ReviewQuality] = field(default_factory=list)
    
    @property
    def acceptance_rate(self) -> Optional[float]:
        """Calculate invitation acceptance rate"""
        if self.total_invitations > 0:
            return self.accepted_invitations / self.total_invitations
        return None
    
    @property
    def completion_rate(self) -> Optional[float]:
        """Calculate review completion rate"""
        if self.accepted_invitations > 0:
            return self.completed_reviews / self.accepted_invitations
        return None