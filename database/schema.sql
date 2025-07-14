-- Editorial Scripts Database Schema
-- PostgreSQL 13+ with asyncpg support

-- Create database (run this manually as superuser)
-- CREATE DATABASE editorial_scripts;
-- CREATE USER editorial WITH PASSWORD 'your-password';
-- GRANT ALL PRIVILEGES ON DATABASE editorial_scripts TO editorial;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE journal_code AS ENUM ('SICON', 'SIFIN', 'MF', 'MOR', 'JOTA', 'FS');
CREATE TYPE manuscript_status AS ENUM ('submitted', 'under_review', 'accepted', 'rejected', 'withdrawn');
CREATE TYPE referee_status AS ENUM ('active', 'inactive', 'declined', 'busy');
CREATE TYPE decision_type AS ENUM ('accept', 'reject', 'major_revision', 'minor_revision', 'desk_reject');

-- Manuscripts table
CREATE TABLE manuscripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    abstract TEXT,
    keywords TEXT[],
    authors TEXT[],
    journal_code journal_code NOT NULL,
    submission_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status manuscript_status DEFAULT 'submitted',
    pdf_path TEXT,
    metadata JSONB,
    ai_analysis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Referees table
CREATE TABLE referees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    institution TEXT,
    expertise_areas TEXT[],
    journals journal_code[],
    status referee_status DEFAULT 'active',
    workload_score DECIMAL(3,2) DEFAULT 0.5,
    quality_score DECIMAL(3,2) DEFAULT 0.75,
    response_time_avg INTEGER, -- days
    acceptance_rate DECIMAL(3,2),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manuscript_id UUID REFERENCES manuscripts(id) ON DELETE CASCADE,
    referee_id UUID REFERENCES referees(id) ON DELETE CASCADE,
    invitation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_date TIMESTAMP WITH TIME ZONE,
    review_submitted_date TIMESTAMP WITH TIME ZONE,
    decision decision_type,
    quality_score DECIMAL(3,2),
    timeliness_score DECIMAL(3,2),
    review_content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(manuscript_id, referee_id)
);

-- AI Analysis Cache table
CREATE TABLE ai_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key TEXT UNIQUE NOT NULL,
    analysis_type TEXT NOT NULL, -- 'desk_rejection', 'referee_recommendation', 'comprehensive'
    input_hash TEXT NOT NULL,
    result JSONB NOT NULL,
    confidence_score DECIMAL(3,2),
    model_version TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '24 hours'
);

-- Referee Analytics table
CREATE TABLE referee_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referee_id UUID REFERENCES referees(id) ON DELETE CASCADE,
    journal_code journal_code,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_invitations INTEGER DEFAULT 0,
    total_acceptances INTEGER DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    avg_response_time DECIMAL(5,2), -- days
    avg_review_time DECIMAL(5,2), -- days
    quality_metrics JSONB,
    performance_tier TEXT, -- 'excellent', 'good', 'fair', 'poor'
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(referee_id, journal_code, period_start, period_end)
);

-- Journal Analytics table
CREATE TABLE journal_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    journal_code journal_code NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_submissions INTEGER DEFAULT 0,
    total_desk_rejections INTEGER DEFAULT 0,
    total_accepted INTEGER DEFAULT 0,
    total_rejected INTEGER DEFAULT 0,
    avg_review_time DECIMAL(5,2), -- days
    avg_time_to_decision DECIMAL(5,2), -- days
    referee_pool_size INTEGER DEFAULT 0,
    metrics JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(journal_code, period_start, period_end)
);

-- System Metrics table
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(10,4),
    metric_data JSONB,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_manuscripts_journal_status ON manuscripts(journal_code, status);
CREATE INDEX idx_manuscripts_submission_date ON manuscripts(submission_date DESC);
CREATE INDEX idx_manuscripts_ai_analysis ON manuscripts USING GIN(ai_analysis);

CREATE INDEX idx_referees_expertise ON referees USING GIN(expertise_areas);
CREATE INDEX idx_referees_journals ON referees USING GIN(journals);
CREATE INDEX idx_referees_status ON referees(status);

CREATE INDEX idx_reviews_manuscript ON reviews(manuscript_id);
CREATE INDEX idx_reviews_referee ON reviews(referee_id);
CREATE INDEX idx_reviews_dates ON reviews(invitation_date, review_submitted_date);

CREATE INDEX idx_ai_cache_key ON ai_analysis_cache(cache_key);
CREATE INDEX idx_ai_cache_expires ON ai_analysis_cache(expires_at);
CREATE INDEX idx_ai_cache_type ON ai_analysis_cache(analysis_type);

CREATE INDEX idx_referee_analytics_referee ON referee_analytics(referee_id);
CREATE INDEX idx_referee_analytics_period ON referee_analytics(period_start, period_end);
CREATE INDEX idx_referee_analytics_journal ON referee_analytics(journal_code);

CREATE INDEX idx_journal_analytics_code ON journal_analytics(journal_code);
CREATE INDEX idx_journal_analytics_period ON journal_analytics(period_start, period_end);

CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_recorded ON system_metrics(recorded_at DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_manuscripts_updated_at BEFORE UPDATE ON manuscripts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_referees_updated_at BEFORE UPDATE ON referees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE VIEW referee_performance_summary AS
SELECT 
    r.id,
    r.name,
    r.institution,
    r.status,
    COUNT(rev.id) as total_reviews,
    AVG(rev.quality_score) as avg_quality,
    AVG(EXTRACT(EPOCH FROM (rev.review_submitted_date - rev.invitation_date))/86400) as avg_review_days,
    MAX(ra.performance_tier) as performance_tier
FROM referees r
LEFT JOIN reviews rev ON r.id = rev.referee_id
LEFT JOIN referee_analytics ra ON r.id = ra.referee_id
GROUP BY r.id, r.name, r.institution, r.status;

CREATE VIEW journal_performance_summary AS
SELECT 
    ja.journal_code,
    ja.period_start,
    ja.period_end,
    ja.total_submissions,
    ja.total_desk_rejections,
    ja.total_accepted,
    ja.total_rejected,
    ROUND(ja.total_desk_rejections::DECIMAL / NULLIF(ja.total_submissions, 0) * 100, 2) as desk_rejection_rate,
    ROUND(ja.total_accepted::DECIMAL / NULLIF(ja.total_submissions - ja.total_desk_rejections, 0) * 100, 2) as acceptance_rate,
    ja.avg_review_time,
    ja.avg_time_to_decision
FROM journal_analytics ja
ORDER BY ja.journal_code, ja.period_start DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO editorial;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO editorial;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO editorial;