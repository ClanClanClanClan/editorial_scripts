"""Domain models for Editorial Command Center - based on ECC specs v2.0."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ManuscriptStatus(Enum):
    """Manuscript workflow status."""
    
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    AWAITING_REFEREE_REPORTS = "awaiting_referee_reports"
    AWAITING_DECISION = "awaiting_decision"
    REVISION_REQUESTED = "revision_requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RefereeStatus(Enum):
    """Referee assignment status."""
    
    INVITED = "invited"
    AGREED = "agreed"
    DECLINED = "declined"
    REPORT_SUBMITTED = "report_submitted"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class AnalysisType(Enum):
    """AI analysis types."""
    
    DESK_REJECTION = "desk_rejection"
    REFEREE_RECOMMENDATION = "referee_recommendation"
    REPORT_SYNTHESIS = "report_synthesis"
    PLAGIARISM_CHECK = "plagiarism_check"
    CONFLICT_DETECTION = "conflict_detection"


class DocumentType(Enum):
    """Document types in the system."""
    
    MANUSCRIPT = "manuscript"
    COVER_LETTER = "cover_letter"
    REFEREE_REPORT = "referee_report"
    DECISION_LETTER = "decision_letter"
    REVISION = "revision"
    SUPPLEMENTARY = "supplementary"


@dataclass
class Author:
    """Author information."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    email: str = ""
    orcid: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    is_corresponding: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Referee:
    """Referee information."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    email: str = ""
    institution: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    status: RefereeStatus = RefereeStatus.INVITED
    invited_date: Optional[datetime] = None
    agreed_date: Optional[datetime] = None
    report_due_date: Optional[datetime] = None
    report_submitted_date: Optional[datetime] = None
    expertise_score: Optional[float] = None
    conflict_of_interest: bool = False
    historical_performance: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Report:
    """Referee report information."""
    
    id: UUID = field(default_factory=uuid4)
    referee_id: UUID = field(default_factory=uuid4)
    manuscript_id: UUID = field(default_factory=uuid4)
    recommendation: str = ""
    confidence_score: Optional[float] = None
    summary: str = ""
    major_comments: str = ""
    minor_comments: str = ""
    confidential_comments: str = ""
    file_path: Optional[str] = None
    submitted_date: datetime = field(default_factory=datetime.utcnow)
    version: int = 1


@dataclass
class File:
    """File attachment information."""
    
    id: UUID = field(default_factory=uuid4)
    manuscript_id: UUID = field(default_factory=uuid4)
    document_type: DocumentType = DocumentType.MANUSCRIPT
    filename: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    storage_path: str = ""
    checksum: str = ""
    uploaded_date: datetime = field(default_factory=datetime.utcnow)
    version: int = 1


@dataclass
class Evidence:
    """Evidence for AI analysis."""
    
    text: str = ""
    source: str = ""
    confidence: float = 0.0
    location: Optional[str] = None


@dataclass
class HumanReview:
    """Human review of AI analysis."""
    
    id: UUID = field(default_factory=uuid4)
    reviewer_id: str = ""
    decision: str = ""
    reasoning: str = ""
    overrides: Dict[str, Any] = field(default_factory=dict)
    reviewed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIAnalysis:
    """AI analysis result with governance."""
    
    id: UUID = field(default_factory=uuid4)
    manuscript_id: UUID = field(default_factory=uuid4)
    analysis_type: AnalysisType = AnalysisType.DESK_REJECTION
    model_version: str = ""
    confidence_score: float = 0.0
    reasoning: str = ""
    recommendation: str = ""
    evidence: List[Evidence] = field(default_factory=list)
    human_review: Optional[HumanReview] = None
    audit_trail: List['AuditEvent'] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class StatusChange:
    """Manuscript status change record."""
    
    from_status: ManuscriptStatus
    to_status: ManuscriptStatus
    changed_by: str = ""
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuditEvent:
    """Comprehensive audit trail event."""
    
    id: UUID = field(default_factory=uuid4)
    entity_type: str = ""
    entity_id: UUID = field(default_factory=uuid4)
    action: str = ""
    actor: str = ""
    ip_address: str = ""
    user_agent: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: str = ""


@dataclass
class Manuscript:
    """Core manuscript entity with full audit trail."""
    
    id: UUID = field(default_factory=uuid4)
    journal_id: str = ""
    external_id: str = ""  # Journal's manuscript ID
    title: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    authors: List[Author] = field(default_factory=list)
    submission_date: datetime = field(default_factory=datetime.utcnow)
    current_status: ManuscriptStatus = ManuscriptStatus.SUBMITTED
    status_history: List[StatusChange] = field(default_factory=list)
    referees: List[Referee] = field(default_factory=list)
    reports: List[Report] = field(default_factory=list)
    files: List[File] = field(default_factory=list)
    ai_analyses: List[AIAnalysis] = field(default_factory=list)
    audit_trail: List[AuditEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1  # For optimistic locking
    
    # Additional fields from production extractors
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    figure_count: Optional[int] = None
    table_count: Optional[int] = None
    funding_information: Optional[str] = None
    conflict_of_interest: Optional[str] = None
    data_availability: Optional[str] = None
    msc_codes: List[str] = field(default_factory=list)
    topic_area: Optional[str] = None
    editor_assigned: Optional[str] = None
    
    def add_status_change(self, new_status: ManuscriptStatus, changed_by: str, reason: str = ""):
        """Record a status change."""
        if self.current_status != new_status:
            change = StatusChange(
                from_status=self.current_status,
                to_status=new_status,
                changed_by=changed_by,
                reason=reason
            )
            self.status_history.append(change)
            self.current_status = new_status
            self.updated_at = datetime.utcnow()
            self.version += 1
    
    def add_audit_event(self, action: str, actor: str, **kwargs):
        """Add an audit trail event."""
        event = AuditEvent(
            entity_type="Manuscript",
            entity_id=self.id,
            action=action,
            actor=actor,
            **kwargs
        )
        self.audit_trail.append(event)
        self.updated_at = datetime.utcnow()
    
    def get_corresponding_author(self) -> Optional[Author]:
        """Get the corresponding author."""
        for author in self.authors:
            if author.is_corresponding:
                return author
        return self.authors[0] if self.authors else None
    
    def get_active_referees(self) -> List[Referee]:
        """Get referees who are actively reviewing."""
        return [
            r for r in self.referees 
            if r.status in [RefereeStatus.AGREED, RefereeStatus.INVITED]
        ]
    
    def get_submitted_reports(self) -> List[Report]:
        """Get all submitted reports."""
        return [
            report for report in self.reports
            if report.submitted_date is not None
        ]
    
    def needs_ai_analysis(self, analysis_type: AnalysisType) -> bool:
        """Check if manuscript needs a specific AI analysis."""
        for analysis in self.ai_analyses:
            if analysis.analysis_type == analysis_type:
                if analysis.expires_at and analysis.expires_at > datetime.utcnow():
                    return False
        return True