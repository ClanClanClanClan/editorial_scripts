"""
Database models for AI analysis results
Maps AI domain models to PostgreSQL tables
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import uuid

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    Text, JSON, ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .engine import Base
from ...ai.models.manuscript_analysis import (
    AnalysisRecommendation, QualityIssueType
)


class AIAnalysisModel(Base):
    """Database model for AI manuscript analysis results"""
    __tablename__ = 'ai_analyses'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Manuscript identification
    manuscript_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    journal_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Analysis metadata
    analysis_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    processing_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    ai_model_versions: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    
    # Content information
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)  # SHA-256 hash
    pdf_path: Mapped[Optional[str]] = mapped_column(Text)
    text_extracted: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis_quality: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Desk rejection analysis (embedded JSON for flexibility)
    desk_rejection_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON)
    
    # Manuscript metadata (embedded JSON)
    manuscript_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON)
    
    # Human validation
    human_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_notes: Mapped[str] = mapped_column(Text, default="")
    validation_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime)
    validation_user_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Performance tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    referee_recommendations = relationship("AIRefereeRecommendationModel", back_populates="analysis")
    quality_issues = relationship("AIQualityIssueModel", back_populates="analysis")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_ai_analyses_manuscript_journal', 'manuscript_id', 'journal_code'),
        Index('idx_ai_analyses_timestamp', 'analysis_timestamp'),
        Index('idx_ai_analyses_hash', 'content_hash'),
        Index('idx_ai_analyses_validated', 'human_validated'),
    )


class AIRefereeRecommendationModel(Base):
    """Database model for AI referee recommendations"""
    __tablename__ = 'ai_referee_recommendations'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to analysis
    analysis_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey('ai_analyses.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Referee information
    referee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Scoring (0.0 to 1.0)
    expertise_match: Mapped[float] = mapped_column(Float, nullable=False)
    availability_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    workload_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Detailed information (JSON for flexibility)
    expertise_areas: Mapped[List[str]] = mapped_column(JSON, default=list)
    matching_keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    contact_info: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    
    # Analysis details
    rationale: Mapped[str] = mapped_column(Text, default="")
    institution: Mapped[Optional[str]] = mapped_column(String(300))
    recent_publications: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Historical performance (if available)
    historical_response_rate: Mapped[Optional[float]] = mapped_column(Float)
    average_review_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    review_quality_rating: Mapped[Optional[float]] = mapped_column(Float)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    analysis = relationship("AIAnalysisModel", back_populates="referee_recommendations")
    
    # Indexes
    __table_args__ = (
        Index('idx_referee_rec_analysis', 'analysis_id'),
        Index('idx_referee_rec_score', 'overall_score'),
        Index('idx_referee_rec_name', 'referee_name'),
    )


class AIQualityIssueModel(Base):
    """Database model for AI-identified quality issues"""
    __tablename__ = 'ai_quality_issues'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to analysis
    analysis_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey('ai_analyses.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Issue details
    issue_type: Mapped[QualityIssueType] = mapped_column(SQLEnum(QualityIssueType), nullable=False)
    severity: Mapped[float] = mapped_column(Float, nullable=False, index=True)  # 0.0 to 1.0
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200))  # Section or page reference
    suggestion: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    analysis = relationship("AIAnalysisModel", back_populates="quality_issues")
    
    # Indexes
    __table_args__ = (
        Index('idx_quality_issue_analysis', 'analysis_id'),
        Index('idx_quality_issue_type', 'issue_type'),
        Index('idx_quality_issue_severity', 'severity'),
    )


class AIUsageStatsModel(Base):
    """Database model for tracking AI service usage"""
    __tablename__ = 'ai_usage_stats'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Usage tracking
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'openai', 'fallback', etc.
    operation: Mapped[str] = mapped_column(String(50), nullable=False)  # 'desk_rejection', 'metadata', etc.
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Metrics
    request_count: Mapped[int] = mapped_column(Integer, default=1)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Cost tracking
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    
    # Additional metadata
    journal_code: Mapped[Optional[str]] = mapped_column(String(10))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Indexes for analytics
    __table_args__ = (
        Index('idx_usage_stats_date', 'date'),
        Index('idx_usage_stats_service', 'service_type', 'operation'),
        Index('idx_usage_stats_success', 'success'),
        Index('idx_usage_stats_journal', 'journal_code'),
    )


class AIModelPerformanceModel(Base):
    """Database model for tracking AI model performance over time"""
    __tablename__ = 'ai_model_performance'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Model information
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Performance metrics
    accuracy_score: Mapped[Optional[float]] = mapped_column(Float)  # Overall accuracy
    precision_score: Mapped[Optional[float]] = mapped_column(Float)
    recall_score: Mapped[Optional[float]] = mapped_column(Float)
    f1_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Human validation metrics
    human_agreement_rate: Mapped[Optional[float]] = mapped_column(Float)
    false_positive_rate: Mapped[Optional[float]] = mapped_column(Float)
    false_negative_rate: Mapped[Optional[float]] = mapped_column(Float)
    
    # Task-specific metrics
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'desk_rejection', 'metadata', etc.
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    evaluation_method: Mapped[str] = mapped_column(String(100))  # How the evaluation was conducted
    
    # Performance notes
    notes: Mapped[str] = mapped_column(Text, default="")
    evaluator_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Indexes
    __table_args__ = (
        Index('idx_model_perf_model', 'model_name', 'model_version'),
        Index('idx_model_perf_date', 'evaluation_date'),
        Index('idx_model_perf_task', 'task_type'),
        Index('idx_model_perf_accuracy', 'accuracy_score'),
    )