"""Data models for manuscript extraction based on actual legacy output."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RefereeStatusType(Enum):
    """Referee status types from actual data."""

    AGREED = "Agreed"
    DECLINED = "Declined"
    INVITED = "Invited"
    NO_RESPONSE = "No Response"
    UNAVAILABLE = "Unavailable"
    AUTO_DECLINED = "Auto-declined"

    @classmethod
    def parse(cls, status_text: str) -> "RefereeStatusType":
        """Parse status from messy text."""
        status_upper = status_text.upper()
        if "AGREED" in status_upper:
            return cls.AGREED
        elif "DECLINED" in status_upper:
            return cls.DECLINED
        elif "NO RESPONSE" in status_upper:
            return cls.NO_RESPONSE
        elif "UNAVAILABLE" in status_upper:
            return cls.UNAVAILABLE
        elif "AUTO-DECLINED" in status_upper:
            return cls.AUTO_DECLINED
        elif "INVITED" in status_upper:
            return cls.INVITED
        return cls.INVITED  # Default


@dataclass
class RefereeTimeline:
    """Timeline information for referee interactions."""

    invitation_sent: str | None = None
    invitation_viewed: str | None = None
    agreed_to_review: str | None = None
    declined_date: str | None = None
    review_submitted: str | None = None
    review_modified: str | None = None
    reminder_sent: list[str] = field(default_factory=list)
    total_days_to_review: int | None = None
    days_to_respond: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RefereeTimeline":
        """Create from dictionary."""
        return cls(
            invitation_sent=data.get("invitation_sent"),
            invitation_viewed=data.get("invitation_viewed"),
            agreed_to_review=data.get("agreed_to_review"),
            declined_date=data.get("declined_date"),
            review_submitted=data.get("review_submitted"),
            review_modified=data.get("review_modified"),
            reminder_sent=data.get("reminder_sent", []),
            total_days_to_review=data.get("total_days_to_review"),
            days_to_respond=data.get("days_to_respond"),
        )


@dataclass
class RefereeStatusDetails:
    """Detailed status information for referee."""

    status: str
    review_received: bool = False
    review_complete: bool = False
    review_pending: bool = False
    agreed_to_review: bool = False
    declined: bool = False
    no_response: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RefereeStatusDetails":
        """Create from dictionary."""
        return cls(
            status=data.get("status", ""),
            review_received=data.get("review_received", False),
            review_complete=data.get("review_complete", False),
            review_pending=data.get("review_pending", False),
            agreed_to_review=data.get("agreed_to_review", False),
            declined=data.get("declined", False),
            no_response=data.get("no_response", False),
        )


@dataclass
class RefereeReport:
    """Referee report information."""

    available: bool = False
    url: str | None = None
    pdf_downloaded: bool = False
    pdf_path: str | None = None
    content: str | None = None
    recommendation: str | None = None
    scores: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RefereeReport":
        """Create from dictionary."""
        if not data:
            return cls()
        return cls(
            available=data.get("available", False),
            url=data.get("url"),
            pdf_downloaded=data.get("pdf_downloaded", False),
            pdf_path=data.get("pdf_path"),
            content=data.get("content"),
            recommendation=data.get("recommendation"),
            scores=data.get("scores", {}),
        )


@dataclass
class Referee:
    """Complete referee information as extracted."""

    name: str
    email: str = ""
    affiliation: str = ""
    orcid: str = ""
    status: str = ""
    dates: dict[str, str] = field(default_factory=dict)
    report: RefereeReport | None = None
    affiliation_status: str = ""
    status_details: RefereeStatusDetails | None = None
    timeline: RefereeTimeline | None = None
    institution_parsed: str = ""
    country_hints: list[str] = field(default_factory=list)
    department: str = ""
    mathscinet_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Referee":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            affiliation=data.get("affiliation", ""),
            orcid=data.get("orcid", ""),
            status=data.get("status", ""),
            dates=data.get("dates", {}),
            report=RefereeReport.from_dict(data["report"]) if "report" in data else None,
            affiliation_status=data.get("affiliation_status", ""),
            status_details=(
                RefereeStatusDetails.from_dict(data["status_details"])
                if "status_details" in data
                else None
            ),
            timeline=RefereeTimeline.from_dict(data["timeline"]) if "timeline" in data else None,
            institution_parsed=data.get("institution_parsed", ""),
            country_hints=data.get("country_hints", []),
            department=data.get("department", ""),
            mathscinet_id=data.get("mathscinet_id", ""),
        )


@dataclass
class Author:
    """Author information as extracted."""

    name: str
    email: str = ""
    affiliation: str = ""
    orcid: str = ""
    is_corresponding: bool = False
    department: str = ""
    institution: str = ""
    country: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Author":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            affiliation=data.get("affiliation", ""),
            orcid=data.get("orcid", ""),
            is_corresponding=data.get("is_corresponding", False),
            department=data.get("department", ""),
            institution=data.get("institution", ""),
            country=data.get("country", ""),
        )


@dataclass
class Documents:
    """Document information for manuscript."""

    pdf: bool = False
    pdf_size: str = ""
    pdf_path: str = ""
    html: bool = False
    abstract: bool = False
    cover_letter: bool = False
    cover_letter_path: str = ""
    supplementary_files: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Documents":
        """Create from dictionary."""
        if not data:
            return cls()
        return cls(
            pdf=data.get("pdf", False),
            pdf_size=data.get("pdf_size", ""),
            pdf_path=data.get("pdf_path", ""),
            html=data.get("html", False),
            abstract=data.get("abstract", False),
            cover_letter=data.get("cover_letter", False),
            cover_letter_path=data.get("cover_letter_path", ""),
            supplementary_files=data.get("supplementary_files", []),
        )


@dataclass
class AuditEvent:
    """Single audit trail event."""

    date: str
    event_type: str
    description: str
    actor: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEvent":
        """Create from dictionary."""
        return cls(
            date=data.get("date", ""),
            event_type=data.get("event_type", ""),
            description=data.get("description", ""),
            actor=data.get("actor", ""),
            details=data.get("details", {}),
        )


@dataclass
class ExtractedManuscript:
    """Complete manuscript as extracted by legacy system."""

    # Core identifiers
    id: str
    category: str = ""

    # Basic information
    title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    status: str = ""

    # People
    authors: list[Author] = field(default_factory=list)
    referees: list[Referee] = field(default_factory=list)
    editor_assigned: str = ""
    editor_chain: list[str] = field(default_factory=list)

    # Documents
    documents: Documents | None = None

    # Dates
    submission_date: str | None = None
    last_status_update: str | None = None
    decision_date: str | None = None

    # Counts
    word_count: int | None = None
    page_count: int | None = None
    figure_count: int | None = None
    table_count: int | None = None

    # MOR parity fields
    funding_information: str = ""
    conflict_of_interest: str = ""
    data_availability: str = ""
    msc_codes: list[str] = field(default_factory=list)
    topic_area: str = ""

    # Audit trail
    audit_trail: list[AuditEvent] = field(default_factory=list)

    # Version tracking
    version: str = ""
    revision_number: int = 0
    version_history: list[dict[str, Any]] = field(default_factory=list)

    # Extraction metadata
    extraction_timestamp: str | None = None
    extraction_errors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtractedManuscript":
        """Create from dictionary (legacy JSON format)."""
        manuscript = cls(
            id=data.get("id", ""),
            category=data.get("category", ""),
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),
            keywords=data.get("keywords", []),
            status=data.get("status", ""),
            editor_assigned=data.get("editor_assigned", ""),
            editor_chain=data.get("editor_chain", []),
            submission_date=data.get("submission_date"),
            last_status_update=data.get("last_status_update"),
            decision_date=data.get("decision_date"),
            word_count=data.get("word_count"),
            page_count=data.get("page_count"),
            figure_count=data.get("figure_count"),
            table_count=data.get("table_count"),
            funding_information=data.get("funding_information", ""),
            conflict_of_interest=data.get("conflict_of_interest", ""),
            data_availability=data.get("data_availability", ""),
            msc_codes=data.get("msc_codes", []),
            topic_area=data.get("topic_area", ""),
            version=data.get("version", ""),
            revision_number=data.get("revision_number", 0),
            version_history=data.get("version_history", []),
            extraction_timestamp=data.get("extraction_timestamp"),
            extraction_errors=data.get("extraction_errors", []),
        )

        # Parse authors
        if "authors" in data:
            manuscript.authors = [Author.from_dict(a) for a in data["authors"]]

        # Parse referees
        if "referees" in data:
            manuscript.referees = [Referee.from_dict(r) for r in data["referees"]]

        # Parse documents
        if "documents" in data:
            manuscript.documents = Documents.from_dict(data["documents"])

        # Parse audit trail
        if "audit_trail" in data:
            manuscript.audit_trail = [AuditEvent.from_dict(e) for e in data["audit_trail"]]

        return manuscript

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dictionary format."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "status": self.status,
            "authors": [vars(a) for a in self.authors],
            "referees": [self._referee_to_dict(r) for r in self.referees],
            "documents": vars(self.documents) if self.documents else None,
            "editor_assigned": self.editor_assigned,
            "editor_chain": self.editor_chain,
            "submission_date": self.submission_date,
            "last_status_update": self.last_status_update,
            "decision_date": self.decision_date,
            "word_count": self.word_count,
            "page_count": self.page_count,
            "figure_count": self.figure_count,
            "table_count": self.table_count,
            "funding_information": self.funding_information,
            "conflict_of_interest": self.conflict_of_interest,
            "data_availability": self.data_availability,
            "msc_codes": self.msc_codes,
            "topic_area": self.topic_area,
            "audit_trail": [vars(e) for e in self.audit_trail],
            "version": self.version,
            "revision_number": self.revision_number,
            "version_history": self.version_history,
            "extraction_timestamp": self.extraction_timestamp,
            "extraction_errors": self.extraction_errors,
        }

    def _referee_to_dict(self, referee: Referee) -> dict[str, Any]:
        """Convert referee to dictionary with nested objects."""
        result = {
            "name": referee.name,
            "email": referee.email,
            "affiliation": referee.affiliation,
            "orcid": referee.orcid,
            "status": referee.status,
            "dates": referee.dates,
            "affiliation_status": referee.affiliation_status,
            "institution_parsed": referee.institution_parsed,
            "country_hints": referee.country_hints,
            "department": referee.department,
            "mathscinet_id": referee.mathscinet_id,
        }
        if referee.report:
            result["report"] = vars(referee.report)
        if referee.status_details:
            result["status_details"] = vars(referee.status_details)
        if referee.timeline:
            result["timeline"] = vars(referee.timeline)
        return result
