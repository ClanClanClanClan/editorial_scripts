"""
PostgreSQL models for referee analytics - FIXED VERSION
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, Index, CheckConstraint, JSON, Date, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
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


class RefereeAnalyticsCacheModel(Base):
    """Cached referee analytics for performance - FIXED"""
    __tablename__ = 'referee_analytics_cache'
    
    referee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey('referees_analytics.id', ondelete='CASCADE'), 
        primary_key=True
    )
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    data_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Relationship - FIXED
    referee: Mapped["RefereeAnalyticsModel"] = relationship(
        "RefereeAnalyticsModel",
        foreign_keys=[referee_id]
    )


class ManuscriptAnalyticsModel(Base):
    """Manuscript information for review tracking"""
    __tablename__ = 'manuscripts_analytics'
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
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


class RefereeMetricsHistoryModel(Base):
    """Historical daily metrics for trend analysis - SIMPLIFIED"""
    __tablename__ = 'referee_metrics_history'
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referee_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey('referees_analytics.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    metric_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    
    # Core performance scores (0-1 normalized)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)
    speed_score: Mapped[float] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Current workload metrics
    current_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monthly_average: Mapped[float] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    
    # Relationship - FIXED
    referee: Mapped["RefereeAnalyticsModel"] = relationship(
        "RefereeAnalyticsModel",
        foreign_keys=[referee_id]
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint('overall_score IS NULL OR (overall_score >= 0.0 AND overall_score <= 1.0)'),
        CheckConstraint('current_reviews >= 0'),
        Index('idx_metrics_history_referee_date', 'referee_id', 'metric_date', unique=True),
    )