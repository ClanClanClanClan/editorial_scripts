"""
SQLAlchemy ORM models for PostgreSQL
Maps domain models to database tables
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
import uuid

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean, 
    Text, JSON, ForeignKey, Index, Enum as SQLEnum,
    Table, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .engine import Base
from ...core.domain.models import (
    ManuscriptStatus, RefereeStatus, ReviewQuality
)


# Association table for manuscript-referee many-to-many
manuscript_referees = Table(
    'manuscript_referees',
    Base.metadata,
    Column('manuscript_id', PGUUID(as_uuid=True), ForeignKey('manuscripts.id')),
    Column('referee_id', PGUUID(as_uuid=True), ForeignKey('referees.id'))
)


class ManuscriptModel(Base):
    """Manuscript database model"""
    __tablename__ = 'manuscripts'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    journal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status and metadata
    status: Mapped[ManuscriptStatus] = mapped_column(
        SQLEnum(ManuscriptStatus), 
        default=ManuscriptStatus.SUBMITTED,
        index=True
    )
    current_round: Mapped[int] = mapped_column(Integer, default=1)
    submission_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # People
    editor_name: Mapped[Optional[str]] = mapped_column(String(200))
    associate_editor_name: Mapped[Optional[str]] = mapped_column(String(200))
    authors: Mapped[JSON] = mapped_column(JSON, default=list)  # List of author dicts
    
    # Document info
    keywords: Mapped[JSON] = mapped_column(JSON, default=list)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Metadata
    custom_metadata: Mapped[JSON] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = relationship("ReviewModel", back_populates="manuscript", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint('journal_code', 'external_id', name='uix_journal_external_id'),
        Index('ix_manuscripts_status_journal', 'status', 'journal_code'),
        Index('ix_manuscripts_updated', 'updated_at'),
    )


class RefereeModel(Base):
    """Referee database model"""
    __tablename__ = 'referees'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    institution: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Expertise and metrics
    expertise_areas: Mapped[JSON] = mapped_column(JSON, default=list)
    h_index: Mapped[Optional[int]] = mapped_column(Integer)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    active_reviews: Mapped[int] = mapped_column(Integer, default=0)
    average_review_days: Mapped[Optional[float]] = mapped_column(Float)
    reliability_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = relationship("ReviewModel", back_populates="referee")
    
    # Indexes
    __table_args__ = (
        Index('ix_referees_reliability', 'reliability_score'),
    )


class ReviewModel(Base):
    """Review database model"""
    __tablename__ = 'reviews'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    referee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees.id'), nullable=False)
    manuscript_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('manuscripts.id'), nullable=False)
    
    # Status and dates
    status: Mapped[RefereeStatus] = mapped_column(
        SQLEnum(RefereeStatus),
        default=RefereeStatus.INVITED,
        index=True
    )
    invited_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    responded_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    submitted_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Review content
    quality_score: Mapped[Optional[ReviewQuality]] = mapped_column(SQLEnum(ReviewQuality))
    report_text: Mapped[Optional[str]] = mapped_column(Text)
    recommendation: Mapped[Optional[str]] = mapped_column(String(50))
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20))
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Metadata
    custom_metadata: Mapped[JSON] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    referee = relationship("RefereeModel", back_populates="reviews")
    manuscript = relationship("ManuscriptModel", back_populates="reviews")
    
    # Indexes
    __table_args__ = (
        Index('ix_reviews_referee_status', 'referee_id', 'status'),
        Index('ix_reviews_manuscript_status', 'manuscript_id', 'status'),
        Index('ix_reviews_due_date', 'due_date'),
    )


class ExtractionLogModel(Base):
    """Extraction run logging"""
    __tablename__ = 'extraction_logs'
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    manuscripts_count: Mapped[int] = mapped_column(Integer, default=0)
    referees_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    warnings: Mapped[JSON] = mapped_column(JSON, default=list)
    custom_metadata: Mapped[JSON] = mapped_column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('ix_extraction_logs_journal_date', 'journal_code', 'started_at'),
    )