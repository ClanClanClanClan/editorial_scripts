"""Common data models for the editorial extraction system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
    email: str | None = None
    affiliation: str | None = None
    country: str | None = None
    orcid: str | None = None
    is_corresponding: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "affiliation": self.affiliation,
            "country": self.country,
            "orcid": self.orcid,
            "is_corresponding": self.is_corresponding,
        }


@dataclass
class Referee:
    """Referee information."""

    name: str
    email: str | None = None
    affiliation: str | None = None
    country: str | None = None
    orcid: str | None = None
    status: RefereeStatus = RefereeStatus.UNKNOWN
    invitation_date: datetime | None = None
    response_date: datetime | None = None
    due_date: datetime | None = None
    report_submitted: datetime | None = None
    recommendation: str | None = None
    comments: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "affiliation": self.affiliation,
            "country": self.country,
            "orcid": self.orcid,
            "status": self.status.value,
            "invitation_date": self.invitation_date.isoformat() if self.invitation_date else None,
            "response_date": self.response_date.isoformat() if self.response_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "report_submitted": (
                self.report_submitted.isoformat() if self.report_submitted else None
            ),
            "recommendation": self.recommendation,
            "comments": self.comments,
        }


@dataclass
class Document:
    """Document information."""

    type: DocumentType
    title: str | None = None
    filename: str | None = None
    url: str | None = None
    downloaded: bool = False
    download_path: str | None = None
    size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "title": self.title,
            "filename": self.filename,
            "url": self.url,
            "downloaded": self.downloaded,
            "download_path": self.download_path,
            "size_bytes": self.size_bytes,
        }


@dataclass
class Manuscript:
    """Manuscript information."""

    id: str
    title: str | None = None
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    status: ManuscriptStatus = ManuscriptStatus.UNKNOWN
    submission_date: datetime | None = None
    last_updated: datetime | None = None
    decision_date: datetime | None = None
    authors: list[Author] = field(default_factory=list)
    referees: list[Referee] = field(default_factory=list)
    documents: list[Document] = field(default_factory=list)
    journal_code: str | None = None
    category: str | None = None
    editor: str | None = None
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_corresponding_author(self) -> Author | None:
        """Get the corresponding author."""
        for author in self.authors:
            if author.is_corresponding:
                return author
        return self.authors[0] if self.authors else None

    def get_referee_by_email(self, email: str) -> Referee | None:
        """Get referee by email address."""
        for referee in self.referees:
            if referee.email == email:
                return referee
        return None

    def get_document(self, doc_type: DocumentType) -> Document | None:
        """Get first document of specified type."""
        for doc in self.documents:
            if doc.type == doc_type:
                return doc
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "status": self.status.value,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "authors": [author.to_dict() for author in self.authors],
            "referees": [referee.to_dict() for referee in self.referees],
            "documents": [doc.to_dict() for doc in self.documents],
            "journal_code": self.journal_code,
            "category": self.category,
            "editor": self.editor,
            "audit_trail": self.audit_trail,
            "metadata": self.metadata,
        }


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    success: bool
    manuscripts: list[Manuscript] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extraction_time: datetime | None = None
    duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "manuscripts": [ms.to_dict() for ms in self.manuscripts],
            "errors": self.errors,
            "warnings": self.warnings,
            "extraction_time": self.extraction_time.isoformat() if self.extraction_time else None,
            "duration_seconds": self.duration_seconds,
            "summary": {
                "total_manuscripts": len(self.manuscripts),
                "total_referees": sum(len(ms.referees) for ms in self.manuscripts),
                "total_documents": sum(len(ms.documents) for ms in self.manuscripts),
            },
        }
