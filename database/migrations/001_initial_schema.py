"""
Initial database schema migration
Creates all core tables for the Editorial Scripts system
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial schema"""
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create custom types
    journal_code_enum = postgresql.ENUM(
        'SICON', 'SIFIN', 'MF', 'MOR', 'JOTA', 'FS',
        name='journal_code'
    )
    journal_code_enum.create(op.get_bind())
    
    manuscript_status_enum = postgresql.ENUM(
        'submitted', 'under_review', 'accepted', 'rejected', 'withdrawn',
        name='manuscript_status'
    )
    manuscript_status_enum.create(op.get_bind())
    
    referee_status_enum = postgresql.ENUM(
        'active', 'inactive', 'declined', 'busy',
        name='referee_status'
    )
    referee_status_enum.create(op.get_bind())
    
    decision_type_enum = postgresql.ENUM(
        'accept', 'reject', 'major_revision', 'minor_revision', 'desk_reject',
        name='decision_type'
    )
    decision_type_enum.create(op.get_bind())
    
    # Create manuscripts table
    op.create_table(
        'manuscripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('abstract', sa.Text),
        sa.Column('keywords', postgresql.ARRAY(sa.Text)),
        sa.Column('authors', postgresql.ARRAY(sa.Text)),
        sa.Column('journal_code', journal_code_enum, nullable=False),
        sa.Column('submission_date', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('status', manuscript_status_enum, server_default='submitted'),
        sa.Column('pdf_path', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('ai_analysis', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    
    # Create referees table
    op.create_table(
        'referees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('email', sa.Text, unique=True),
        sa.Column('institution', sa.Text),
        sa.Column('expertise_areas', postgresql.ARRAY(sa.Text)),
        sa.Column('journals', postgresql.ARRAY(journal_code_enum)),
        sa.Column('status', referee_status_enum, server_default='active'),
        sa.Column('workload_score', sa.DECIMAL(3,2), server_default='0.5'),
        sa.Column('quality_score', sa.DECIMAL(3,2), server_default='0.75'),
        sa.Column('response_time_avg', sa.Integer),
        sa.Column('acceptance_rate', sa.DECIMAL(3,2)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    
    # Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('manuscript_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('manuscripts.id', ondelete='CASCADE')),
        sa.Column('referee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('referees.id', ondelete='CASCADE')),
        sa.Column('invitation_date', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('response_date', sa.TIMESTAMP(timezone=True)),
        sa.Column('review_submitted_date', sa.TIMESTAMP(timezone=True)),
        sa.Column('decision', decision_type_enum),
        sa.Column('quality_score', sa.DECIMAL(3,2)),
        sa.Column('timeliness_score', sa.DECIMAL(3,2)),
        sa.Column('review_content', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('manuscript_id', 'referee_id')
    )
    
    # Create ai_analysis_cache table
    op.create_table(
        'ai_analysis_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('cache_key', sa.Text, nullable=False, unique=True),
        sa.Column('analysis_type', sa.Text, nullable=False),
        sa.Column('input_hash', sa.Text, nullable=False),
        sa.Column('result', postgresql.JSONB, nullable=False),
        sa.Column('confidence_score', sa.DECIMAL(3,2)),
        sa.Column('model_version', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW() + INTERVAL '24 hours'"))
    )
    
    # Create referee_analytics table
    op.create_table(
        'referee_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('referee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('referees.id', ondelete='CASCADE')),
        sa.Column('journal_code', journal_code_enum),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('total_invitations', sa.Integer, server_default='0'),
        sa.Column('total_acceptances', sa.Integer, server_default='0'),
        sa.Column('total_reviews', sa.Integer, server_default='0'),
        sa.Column('avg_response_time', sa.DECIMAL(5,2)),
        sa.Column('avg_review_time', sa.DECIMAL(5,2)),
        sa.Column('quality_metrics', postgresql.JSONB),
        sa.Column('performance_tier', sa.Text),
        sa.Column('calculated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('referee_id', 'journal_code', 'period_start', 'period_end')
    )
    
    # Create journal_analytics table
    op.create_table(
        'journal_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('journal_code', journal_code_enum, nullable=False),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('total_submissions', sa.Integer, server_default='0'),
        sa.Column('total_desk_rejections', sa.Integer, server_default='0'),
        sa.Column('total_accepted', sa.Integer, server_default='0'),
        sa.Column('total_rejected', sa.Integer, server_default='0'),
        sa.Column('avg_review_time', sa.DECIMAL(5,2)),
        sa.Column('avg_time_to_decision', sa.DECIMAL(5,2)),
        sa.Column('referee_pool_size', sa.Integer, server_default='0'),
        sa.Column('metrics', postgresql.JSONB),
        sa.Column('calculated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('journal_code', 'period_start', 'period_end')
    )
    
    # Create system_metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('metric_name', sa.Text, nullable=False),
        sa.Column('metric_value', sa.DECIMAL(10,4)),
        sa.Column('metric_data', postgresql.JSONB),
        sa.Column('recorded_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )
    
    # Create indexes
    op.create_index('idx_manuscripts_journal_status', 'manuscripts', ['journal_code', 'status'])
    op.create_index('idx_manuscripts_submission_date', 'manuscripts', [sa.desc('submission_date')])
    op.create_index('idx_manuscripts_ai_analysis', 'manuscripts', ['ai_analysis'], postgresql_using='gin')
    
    op.create_index('idx_referees_expertise', 'referees', ['expertise_areas'], postgresql_using='gin')
    op.create_index('idx_referees_journals', 'referees', ['journals'], postgresql_using='gin')
    op.create_index('idx_referees_status', 'referees', ['status'])
    
    op.create_index('idx_reviews_manuscript', 'reviews', ['manuscript_id'])
    op.create_index('idx_reviews_referee', 'reviews', ['referee_id'])
    op.create_index('idx_reviews_dates', 'reviews', ['invitation_date', 'review_submitted_date'])
    
    op.create_index('idx_ai_cache_key', 'ai_analysis_cache', ['cache_key'])
    op.create_index('idx_ai_cache_expires', 'ai_analysis_cache', ['expires_at'])
    op.create_index('idx_ai_cache_type', 'ai_analysis_cache', ['analysis_type'])
    
    op.create_index('idx_referee_analytics_referee', 'referee_analytics', ['referee_id'])
    op.create_index('idx_referee_analytics_period', 'referee_analytics', ['period_start', 'period_end'])
    op.create_index('idx_referee_analytics_journal', 'referee_analytics', ['journal_code'])
    
    op.create_index('idx_journal_analytics_code', 'journal_analytics', ['journal_code'])
    op.create_index('idx_journal_analytics_period', 'journal_analytics', ['period_start', 'period_end'])
    
    op.create_index('idx_system_metrics_name', 'system_metrics', ['metric_name'])
    op.create_index('idx_system_metrics_recorded', 'system_metrics', [sa.desc('recorded_at')])


def downgrade():
    """Drop all tables and types"""
    
    # Drop tables in reverse order
    op.drop_table('system_metrics')
    op.drop_table('journal_analytics')
    op.drop_table('referee_analytics')
    op.drop_table('ai_analysis_cache')
    op.drop_table('reviews')
    op.drop_table('referees')
    op.drop_table('manuscripts')
    
    # Drop custom types
    op.execute('DROP TYPE IF EXISTS decision_type')
    op.execute('DROP TYPE IF EXISTS referee_status')
    op.execute('DROP TYPE IF EXISTS manuscript_status')
    op.execute('DROP TYPE IF EXISTS journal_code')