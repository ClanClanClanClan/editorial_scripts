"""SQLAlchemy async models for PostgreSQL database."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.ecc.core.domain.models import (
    AnalysisType,
    DocumentType,
    ManuscriptStatus,
    RefereeStatus,
)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class ManuscriptModel(Base):
    """Manuscript database model."""
    
    __tablename__ = "manuscripts"
    __table_args__ = (
        UniqueConstraint("journal_id", "external_id", name="uq_journal_manuscript"),
    )
    
    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Identifiers
    journal_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Basic info
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    
    # Status
    current_status: Mapped[ManuscriptStatus] = mapped_column(
        Enum(ManuscriptStatus), 
        default=ManuscriptStatus.SUBMITTED,
        index=True
    )
    submission_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Counts
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    figure_count: Mapped[Optional[int]] = mapped_column(Integer)
    table_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Additional fields
    funding_information: Mapped[Optional[str]] = mapped_column(Text)
    conflict_of_interest: Mapped[Optional[str]] = mapped_column(Text)
    data_availability: Mapped[Optional[str]] = mapped_column(Text)
    msc_codes: Mapped[list] = mapped_column(JSON, default=list)
    topic_area: Mapped[Optional[str]] = mapped_column(String(200))
    editor_assigned: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Version for optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Relationships
    authors: Mapped[list["AuthorModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    referees: Mapped[list["RefereeModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    reports: Mapped[list["ReportModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    files: Mapped[list["FileModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    ai_analyses: Mapped[list["AIAnalysisModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["AuditEventModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )
    status_changes: Mapped[list["StatusChangeModel"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan"
    )


class AuthorModel(Base):
    """Author database model."""
    
    __tablename__ = "authors"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    orcid: Mapped[Optional[str]] = mapped_column(String(50))
    institution: Mapped[Optional[str]] = mapped_column(String(500))
    department: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    is_corresponding: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="authors")


class RefereeModel(Base):
    """Referee database model."""
    
    __tablename__ = "referees"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200))
    institution: Mapped[Optional[str]] = mapped_column(String(500))
    department: Mapped[Optional[str]] = mapped_column(String(200))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    
    status: Mapped[RefereeStatus] = mapped_column(
        Enum(RefereeStatus),
        default=RefereeStatus.INVITED
    )
    
    invited_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    agreed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    report_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    report_submitted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    expertise_score: Mapped[Optional[float]] = mapped_column(Float)
    conflict_of_interest: Mapped[bool] = mapped_column(Boolean, default=False)
    historical_performance: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="referees")
    reports: Mapped[list["ReportModel"]] = relationship(back_populates="referee")


class ReportModel(Base):
    """Referee report database model."""
    
    __tablename__ = "reports"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    referee_id: Mapped[UUID] = mapped_column(ForeignKey("referees.id"), nullable=False)
    
    recommendation: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text, default="")
    major_comments: Mapped[str] = mapped_column(Text, default="")
    minor_comments: Mapped[str] = mapped_column(Text, default="")
    confidential_comments: Mapped[str] = mapped_column(Text, default="")
    
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    submitted_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="reports")
    referee: Mapped["RefereeModel"] = relationship(back_populates="reports")


class FileModel(Base):
    """File attachment database model."""
    
    __tablename__ = "files"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType),
        default=DocumentType.MANUSCRIPT
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    checksum: Mapped[str] = mapped_column(String(100), default="")
    
    uploaded_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="files")


class AIAnalysisModel(Base):
    """AI analysis database model."""
    
    __tablename__ = "ai_analyses"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    
    analysis_type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType),
        nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    human_review: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="ai_analyses")


class AuditEventModel(Base):
    """Audit event database model."""
    
    __tablename__ = "audit_events"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("manuscripts.id"))
    
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
    request_id: Mapped[str] = mapped_column(String(100), default="")
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    manuscript: Mapped[Optional["ManuscriptModel"]] = relationship(back_populates="audit_events")


class StatusChangeModel(Base):
    """Status change history model."""
    
    __tablename__ = "status_changes"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manuscript_id: Mapped[UUID] = mapped_column(ForeignKey("manuscripts.id"), nullable=False)
    
    from_status: Mapped[ManuscriptStatus] = mapped_column(Enum(ManuscriptStatus), nullable=False)
    to_status: Mapped[ManuscriptStatus] = mapped_column(Enum(ManuscriptStatus), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    manuscript: Mapped["ManuscriptModel"] = relationship(back_populates="status_changes")