"""
Data models for the Editorial Assistant system.

This module defines Pydantic models for all data structures used throughout
the system, ensuring type safety and data validation.
"""

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator


class RefereeStatus(str, Enum):
    """Possible referee statuses in the review process."""

    INVITED = "invited"
    AGREED = "agreed"
    DECLINED = "declined"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    UNKNOWN = "unknown"


class Platform(str, Enum):
    """Supported journal submission platforms."""

    SCHOLARONE = "scholarone"
    EDITORIAL_MANAGER = "editorial_manager"
    EJPRESS = "ejpress"


class RefereeDates(BaseModel):
    """Important dates in the referee process."""

    invited: date | None = None
    agreed: date | None = None
    declined: date | None = None
    due: date | None = None
    completed: date | None = None

    @validator("due")
    def validate_due_date(cls, v, values):
        """Ensure due date is after agreed date if both exist."""
        if v and values.get("agreed") and v < values["agreed"]:
            raise ValueError("Due date cannot be before agreed date")
        return v


class RefereeReport(BaseModel):
    """Referee report information."""

    pdf_path: Path | None = None
    text_content: str | None = None
    submitted_date: datetime | None = None
    recommendation: str | None = None
    confidence_score: str | None = None

    @property
    def has_content(self) -> bool:
        """Check if the report has any content."""
        return bool(self.pdf_path or self.text_content)


class Referee(BaseModel):
    """Complete referee information."""

    name: str = Field(..., min_length=1, description="Referee's full name")
    email: str | None = None
    institution: str | None = None
    department: str | None = None
    status: RefereeStatus = RefereeStatus.UNKNOWN
    dates: RefereeDates = Field(default_factory=RefereeDates)
    time_in_review: int | None = Field(None, ge=0, description="Days in review")
    report: RefereeReport | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Original extracted data")

    @validator("name")
    def clean_name(cls, v):
        """Clean and validate referee name."""
        # Remove extra whitespace
        v = " ".join(v.split())
        # Ensure proper format (Last, First)
        if "," not in v:
            raise ValueError('Name must be in "Last, First" format')
        return v

    @property
    def is_active(self) -> bool:
        """Check if referee is currently active in review."""
        return self.status in [RefereeStatus.INVITED, RefereeStatus.AGREED]

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class Author(BaseModel):
    """Manuscript author information."""

    name: str
    email: str | None = None
    institution: str | None = None
    is_corresponding: bool = False


class ManuscriptStatus(str, Enum):
    """Possible manuscript statuses."""

    AWAITING_REVIEWER_ASSIGNMENT = "awaiting_reviewer_assignment"
    AWAITING_REVIEWER_SCORES = "awaiting_reviewer_scores"
    AWAITING_REVIEWER_REPORTS = "awaiting_reviewer_reports"
    AWAITING_AE_RECOMMENDATION = "awaiting_ae_recommendation"
    AWAITING_FINAL_DECISION = "awaiting_final_decision"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    IN_REVISION = "in_revision"


class Manuscript(BaseModel):
    """Complete manuscript information."""

    manuscript_id: str = Field(..., description="Unique manuscript identifier")
    title: str
    authors: list[Author] = Field(default_factory=list)
    status: ManuscriptStatus
    submission_date: date | None = None
    decision_date: date | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    pdf_path: Path | None = None
    referees: list[Referee] = Field(default_factory=list)
    ae_name: str | None = None
    ae_email: str | None = None
    journal_code: str
    url: str | None = None

    @property
    def days_in_review(self) -> int | None:
        """Calculate total days in review."""
        if self.submission_date:
            end_date = self.decision_date or date.today()
            return (end_date - self.submission_date).days
        return None

    @property
    def active_referees(self) -> list[Referee]:
        """Get list of active referees."""
        return [r for r in self.referees if r.is_active]

    @property
    def completed_referees(self) -> list[Referee]:
        """Get list of referees who completed their review."""
        return [r for r in self.referees if r.status == RefereeStatus.COMPLETED]

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }


class Journal(BaseModel):
    """Journal configuration and metadata."""

    code: str = Field(..., description="Journal code (e.g., MF, MOR)")
    name: str = Field(..., description="Full journal name")
    platform: Platform
    url: str = Field(..., description="Journal submission system URL")
    categories: list[str] = Field(default_factory=list, description="AE categories to check")
    patterns: dict[str, str] = Field(default_factory=dict, description="Regex patterns")
    credentials: dict[str, str] = Field(default_factory=dict, description="Login credentials")

    @validator("code")
    def uppercase_code(cls, v):
        """Ensure journal code is uppercase."""
        return v.upper()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class JournalConfig(BaseModel):
    """Extended journal configuration for extractors."""

    code: str = Field(..., description="Journal code (e.g., MF, MOR)")
    name: str = Field(..., description="Full journal name")
    platform: str = Field(..., description="Platform identifier")
    url: str | None = Field(None, description="Journal submission system URL")
    categories: list[str] = Field(default_factory=list, description="AE categories to check")
    patterns: dict[str, Any] = Field(
        default_factory=dict, description="Regex patterns and other patterns"
    )
    credentials: dict[str, Any] = Field(
        default_factory=dict, description="Login credentials configuration"
    )
    settings: dict[str, Any] = Field(default_factory=dict, description="Journal-specific settings")
    platform_config: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific configuration"
    )

    @validator("code")
    def uppercase_code(cls, v):
        """Ensure journal code is uppercase."""
        return v.upper() if v else v

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ExtractionResult(BaseModel):
    """Result of an extraction operation."""

    journal: Journal
    manuscripts: list[Manuscript] = Field(default_factory=list)
    extraction_date: datetime = Field(default_factory=datetime.now)
    duration_seconds: float | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return len(self.manuscripts) > 0 and len(self.errors) == 0

    @property
    def total_referees(self) -> int:
        """Get total number of referees across all manuscripts."""
        return sum(len(m.referees) for m in self.manuscripts)

    @property
    def total_pdfs(self) -> int:
        """Get total number of PDFs downloaded."""
        manuscript_pdfs = sum(1 for m in self.manuscripts if m.pdf_path)
        referee_pdfs = sum(
            1 for m in self.manuscripts for r in m.referees if r.report and r.report.pdf_path
        )
        return manuscript_pdfs + referee_pdfs

    def to_summary(self) -> dict[str, Any]:
        """Generate a summary of the extraction result."""
        return {
            "journal": self.journal.code,
            "extraction_date": self.extraction_date.isoformat(),
            "manuscripts_count": len(self.manuscripts),
            "referees_count": self.total_referees,
            "pdfs_downloaded": self.total_pdfs,
            "success": self.success,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "duration_seconds": self.duration_seconds,
        }

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
