"""
PostgreSQL models for referee analytics and performance tracking
"""

import uuid
from datetime import datetime
from typing import List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, Index, CheckConstraint, JSON, Date, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from .models import Base


class RefereeAnalyticsModel(Base):
    """Core referee information model for analytics"""
    __tablename__ = 'referees_analytics'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    institution: Mapped[str] = mapped_column(String(300), nullable=True, index=True)
    h_index: Mapped[int] = mapped_column(Integer, nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    # Relationships
    expertise: Mapped[List["RefereeExpertiseModel"]] = relationship("RefereeExpertiseModel", back_populates="referee")
    review_history: Mapped[List["ReviewHistoryModel"]] = relationship("ReviewHistoryModel", back_populates="referee")
    analytics_cache: Mapped["RefereeAnalyticsCacheModel"] = relationship("RefereeAnalyticsCacheModel", back_populates="referee", uselist=False)
    metrics_history: Mapped[List["RefereeMetricsHistoryModel"]] = relationship("RefereeMetricsHistoryModel", back_populates="referee")
    
    # Indexes
    __table_args__ = (
        Index('idx_referee_email', 'email'),
        Index('idx_referee_institution', 'institution'),
        Index('idx_referee_h_index', 'h_index'),
        Index('idx_referee_active', 'active'),
    )


class RefereeExpertiseModel(Base):
    """Referee expertise areas with confidence scores"""
    __tablename__ = 'referee_expertise'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    expertise_area: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    referee: Mapped["RefereeAnalyticsModel"] = relationship("RefereeAnalyticsModel", back_populates="expertise")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='check_confidence_range'),
        CheckConstraint('evidence_count >= 0', name='check_evidence_count'),
        Index('idx_expertise_referee_area', 'referee_id', 'expertise_area'),
        Index('idx_expertise_confidence', 'confidence_score'),
    )


class ManuscriptAnalyticsModel(Base):
    """Manuscript information for review tracking"""
    __tablename__ = 'manuscripts_analytics'
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Journal manuscript ID
    journal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, nullable=True)
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    research_area: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    submission_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    decision_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    final_decision: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    review_history: Mapped[List["ReviewHistoryModel"]] = relationship("ReviewHistoryModel", back_populates="manuscript")
    
    # Indexes
    __table_args__ = (
        Index('idx_manuscript_journal', 'journal_code'),
        Index('idx_manuscript_research_area', 'research_area'),
        Index('idx_manuscript_decision', 'final_decision'),
        Index('idx_manuscript_submission_date', 'submission_date'),
    )


class ReviewHistoryModel(Base):
    """Individual review assignment history"""
    __tablename__ = 'review_history'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    manuscript_id: Mapped[str] = mapped_column(String(100), ForeignKey('manuscripts_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Review lifecycle timestamps
    invited_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    responded_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    submitted_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    
    # Decision and quality
    decision: Mapped[str] = mapped_column(String(20), nullable=True, index=True)  # 'accepted', 'declined', NULL (no response)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)  # 1-10 scale
    report_length: Mapped[int] = mapped_column(Integer, nullable=True)  # Character count
    
    # Communication tracking
    reminder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Metadata
    editor_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    referee: Mapped["RefereeAnalyticsModel"] = relationship("RefereeAnalyticsModel", back_populates="review_history")
    manuscript: Mapped["ManuscriptAnalyticsModel"] = relationship("ManuscriptAnalyticsModel", back_populates="review_history")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('quality_score IS NULL OR (quality_score >= 1.0 AND quality_score <= 10.0)', name='check_quality_range'),
        CheckConstraint('reminder_count >= 0', name='check_reminder_count'),
        CheckConstraint('follow_up_count >= 0', name='check_followup_count'),
        Index('idx_review_referee_manuscript', 'referee_id', 'manuscript_id'),
        Index('idx_review_invited_date', 'invited_date'),
        Index('idx_review_decision', 'decision'),
        Index('idx_review_quality', 'quality_score'),
    )


class RefereeAnalyticsCacheModel(Base):
    """Cached referee analytics for performance"""
    __tablename__ = 'referee_analytics_cache'
    
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees.id', ondelete='CASCADE'), primary_key=True)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    data_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Relationships
    referee: Mapped["RefereeAnalyticsModel"] = relationship("RefereeAnalyticsModel", back_populates="analytics_cache")
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_cache_valid', 'valid_until'),
        Index('idx_analytics_cache_calculated', 'calculated_at'),
    )


class RefereeMetricsHistoryModel(Base):
    """Historical daily metrics for trend analysis"""
    __tablename__ = 'referee_metrics_history'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    metric_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    
    # Core performance scores (0-1 normalized)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    speed_score: Mapped[float] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=True)
    expertise_score: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Current workload metrics
    current_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_average: Mapped[float] = mapped_column(Float, nullable=True)
    burnout_risk: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Percentile rankings
    speed_percentile: Mapped[float] = mapped_column(Float, nullable=True)
    quality_percentile: Mapped[float] = mapped_column(Float, nullable=True)
    reliability_percentile: Mapped[float] = mapped_column(Float, nullable=True)
    overall_percentile: Mapped[float] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    
    # Relationships
    referee: Mapped["RefereeAnalyticsModel"] = relationship("RefereeAnalyticsModel", back_populates="metrics_history")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('overall_score IS NULL OR (overall_score >= 0.0 AND overall_score <= 1.0)', name='check_overall_score_range'),
        CheckConstraint('speed_score IS NULL OR (speed_score >= 0.0 AND speed_score <= 1.0)', name='check_speed_score_range'),
        CheckConstraint('quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)', name='check_quality_score_range'),
        CheckConstraint('reliability_score IS NULL OR (reliability_score >= 0.0 AND reliability_score <= 1.0)', name='check_reliability_score_range'),
        CheckConstraint('current_reviews >= 0', name='check_current_reviews'),
        Index('idx_metrics_history_referee_date', 'referee_id', 'metric_date', unique=True),
        Index('idx_metrics_history_date', 'metric_date'),
        Index('idx_metrics_history_overall_score', 'overall_score'),
    )


class JournalSpecificMetricsModel(Base):
    """Journal-specific performance metrics for referees"""
    __tablename__ = 'journal_specific_metrics'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    journal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Performance metrics
    reviews_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acceptance_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    avg_review_time_days: Mapped[float] = mapped_column(Float, nullable=True)
    familiarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Timestamps
    first_review_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_review_date: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('reviews_completed >= 0', name='check_reviews_completed'),
        CheckConstraint('acceptance_rate >= 0.0 AND acceptance_rate <= 1.0', name='check_acceptance_rate'),
        CheckConstraint('avg_quality_score IS NULL OR (avg_quality_score >= 1.0 AND avg_quality_score <= 10.0)', name='check_avg_quality'),
        CheckConstraint('familiarity_score >= 0.0 AND familiarity_score <= 1.0', name='check_familiarity_score'),
        Index('idx_journal_metrics_referee_journal', 'referee_id', 'journal_code', unique=True),
        Index('idx_journal_metrics_journal', 'journal_code'),
        Index('idx_journal_metrics_familiarity', 'familiarity_score'),
    )


class PerformanceTierModel(Base):
    """Performance tier assignments for referees"""
    __tablename__ = 'performance_tiers'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('referees_analytics.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Tier information
    tier: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # elite, high_performer, etc.
    tier_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    tier_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Context
    assessment_date: Mapped[datetime] = mapped_column(Date, nullable=False, default=func.current_date(), index=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Number of reviews considered
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # Confidence in tier assignment
    
    # Comparison context
    peer_group_size: Mapped[int] = mapped_column(Integer, nullable=True)  # Size of comparison group
    journal_context: Mapped[str] = mapped_column(String(10), nullable=True)  # If tier is journal-specific
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('tier_percentile >= 0.0 AND tier_percentile <= 100.0', name='check_tier_percentile'),
        CheckConstraint('tier_score >= 0.0 AND tier_score <= 10.0', name='check_tier_score'),
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='check_confidence'),
        CheckConstraint('sample_size > 0', name='check_sample_size'),
        Index('idx_performance_tier_referee_date', 'referee_id', 'assessment_date'),
        Index('idx_performance_tier_tier', 'tier'),
        Index('idx_performance_tier_percentile', 'tier_percentile'),
    )