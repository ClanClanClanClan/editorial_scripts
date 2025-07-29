"""Common data models for the editorial extraction system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class ManuscriptStatus(Enum):
    """Manuscript status enumeration."""
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    AWAITING_REFEREE_SCORES = "Awaiting Referee Scores"
    AWAITING_DECISION = "Awaiting Decision"
    REVISION_REQUESTED = "Revision Requested"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    UNKNOWN = "Unknown"


class RefereeStatus(Enum):
    """Referee status enumeration."""
    INVITED = "Invited"
    AGREED = "Agreed"
    DECLINED = "Declined"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    UNAVAILABLE = "Unavailable"
    UNKNOWN = "Unknown"


class DocumentType(Enum):
    """Document type enumeration."""
    MANUSCRIPT = "Manuscript"
    PDF = "PDF"
    HTML = "HTML"
    COVER_LETTER = "Cover Letter"
    ABSTRACT = "Abstract"
    SOURCE_FILES = "Source Files"
    REFEREE_REPORT = "Referee Report"
    SUPPLEMENTARY = "Supplementary Material"
    REVISION = "Revision"
    RESPONSE_LETTER = "Response Letter"
    OTHER = "Other"


@dataclass
class Author:
    """Author information."""
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    country: Optional[str] = None
    orcid: Optional[str] = None
    is_corresponding: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'email': self.email,
            'affiliation': self.affiliation,
            'country': self.country,
            'orcid': self.orcid,
            'is_corresponding': self.is_corresponding
        }


@dataclass
class Referee:
    """Referee information."""
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    country: Optional[str] = None
    orcid: Optional[str] = None
    status: RefereeStatus = RefereeStatus.UNKNOWN
    invitation_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    report_submitted: Optional[datetime] = None
    recommendation: Optional[str] = None
    comments: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'email': self.email,
            'affiliation': self.affiliation,
            'country': self.country,
            'orcid': self.orcid,
            'status': self.status.value,
            'invitation_date': self.invitation_date.isoformat() if self.invitation_date else None,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'report_submitted': self.report_submitted.isoformat() if self.report_submitted else None,
            'recommendation': self.recommendation,
            'comments': self.comments
        }


@dataclass
class Document:
    """Document information."""
    type: DocumentType
    title: Optional[str] = None
    filename: Optional[str] = None
    url: Optional[str] = None
    downloaded: bool = False
    download_path: Optional[str] = None
    size_bytes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.type.value,
            'title': self.title,
            'filename': self.filename,
            'url': self.url,
            'downloaded': self.downloaded,
            'download_path': self.download_path,
            'size_bytes': self.size_bytes
        }


@dataclass
class Manuscript:
    """Manuscript information."""
    id: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    status: ManuscriptStatus = ManuscriptStatus.UNKNOWN
    submission_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    decision_date: Optional[datetime] = None
    authors: List[Author] = field(default_factory=list)
    referees: List[Referee] = field(default_factory=list)
    documents: List[Document] = field(default_factory=list)
    journal_code: Optional[str] = None
    category: Optional[str] = None
    editor: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_corresponding_author(self) -> Optional[Author]:
        """Get the corresponding author."""
        for author in self.authors:
            if author.is_corresponding:
                return author
        return self.authors[0] if self.authors else None
    
    def get_referee_by_email(self, email: str) -> Optional[Referee]:
        """Get referee by email address."""
        for referee in self.referees:
            if referee.email == email:
                return referee
        return None
    
    def get_document(self, doc_type: DocumentType) -> Optional[Document]:
        """Get first document of specified type."""
        for doc in self.documents:
            if doc.type == doc_type:
                return doc
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'status': self.status.value,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'decision_date': self.decision_date.isoformat() if self.decision_date else None,
            'authors': [author.to_dict() for author in self.authors],
            'referees': [referee.to_dict() for referee in self.referees],
            'documents': [doc.to_dict() for doc in self.documents],
            'journal_code': self.journal_code,
            'category': self.category,
            'editor': self.editor,
            'audit_trail': self.audit_trail,
            'metadata': self.metadata
        }


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    success: bool
    manuscripts: List[Manuscript] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extraction_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'manuscripts': [ms.to_dict() for ms in self.manuscripts],
            'errors': self.errors,
            'warnings': self.warnings,
            'extraction_time': self.extraction_time.isoformat() if self.extraction_time else None,
            'duration_seconds': self.duration_seconds,
            'summary': {
                'total_manuscripts': len(self.manuscripts),
                'total_referees': sum(len(ms.referees) for ms in self.manuscripts),
                'total_documents': sum(len(ms.documents) for ms in self.manuscripts)
            }
        }