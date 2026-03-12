-- Saarathi Pivot: Core Accountability Loop
-- Migration 003: Founder tracking, reflections, commitments, triggers, and market signals

-- Founder profile (one row per founder)
CREATE TABLE IF NOT EXISTS founders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_user_id   VARCHAR(100) UNIQUE NOT NULL,
    name            VARCHAR(255),
    stage           VARCHAR(50),   -- 'idea' | 'building' | 'launched' | 'scaling'
    icp             TEXT,          -- "B2B SaaS for DevOps teams"
    constraints     TEXT,          -- "solo, 2hrs/day, full-time job"
    timezone        VARCHAR(50) DEFAULT 'UTC',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Weekly reflections (founder fills form each Sunday)
CREATE TABLE IF NOT EXISTS weekly_reflections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID REFERENCES founders(id) ON DELETE CASCADE,
    week_start      DATE NOT NULL,
    shipped         TEXT,          -- "what did you ship?"
    blocked         TEXT,          -- "what's blocking you?"
    energy_score    INTEGER CHECK (energy_score BETWEEN 1 AND 10),
    raw_text        TEXT,          -- full freeform entry
    embedding_id    VARCHAR(255),  -- Qdrant point ID for this reflection
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups by founder
CREATE INDEX IF NOT EXISTS idx_weekly_reflections_founder_id ON weekly_reflections(founder_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reflections_week_start ON weekly_reflections(week_start);

-- Commitments extracted from reflections
CREATE TABLE IF NOT EXISTS commitments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID REFERENCES founders(id) ON DELETE CASCADE,
    reflection_id   UUID REFERENCES weekly_reflections(id) ON DELETE SET NULL,
    description     TEXT NOT NULL,
    due_date        DATE,
    completed       BOOLEAN DEFAULT FALSE,
    completed_at    TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for commitment queries
CREATE INDEX IF NOT EXISTS idx_commitments_founder_id ON commitments(founder_id);
CREATE INDEX IF NOT EXISTS idx_commitments_due_date ON commitments(due_date);
CREATE INDEX IF NOT EXISTS idx_commitments_completed ON commitments(completed);

-- Every trigger decision — fired OR suppressed
CREATE TABLE IF NOT EXISTS trigger_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id      UUID REFERENCES founders(id) ON DELETE CASCADE,
    trigger_type    VARCHAR(100),  -- 'commitment_gap' | 'decision_stall' | 'market_signal' | 'momentum_drop'
    score           DECIMAL(4,3),  -- 0.000 to 1.000
    fired           BOOLEAN NOT NULL,
    suppression_reason TEXT,       -- why it did NOT fire (if fired=false)
    message_sent    TEXT,          -- exact message sent (if fired=true)
    slack_ts        VARCHAR(100),  -- Slack message timestamp for thread replies
    founder_rating  INTEGER,       -- 1=👍, -1=👎, NULL=no rating yet
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for trigger analytics
CREATE INDEX IF NOT EXISTS idx_trigger_log_founder_id ON trigger_log(founder_id);
CREATE INDEX IF NOT EXISTS idx_trigger_log_trigger_type ON trigger_log(trigger_type);
CREATE INDEX IF NOT EXISTS idx_trigger_log_created_at ON trigger_log(created_at);

-- Market signals from crawler
CREATE TABLE IF NOT EXISTS market_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(100),  -- 'indie_hackers' | 'reddit' | 'product_hunt'
    url             TEXT,
    title           TEXT,
    content         TEXT,
    relevance_score DECIMAL(4,3),  -- scored per-founder
    founder_id      UUID REFERENCES founders(id) ON DELETE CASCADE,
    processed       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for market signal queries
CREATE INDEX IF NOT EXISTS idx_market_signals_founder_id ON market_signals(founder_id);
CREATE INDEX IF NOT EXISTS idx_market_signals_source ON market_signals(source);
CREATE INDEX IF NOT EXISTS idx_market_signals_processed ON market_signals(processed);

-- Notify on new market signals for SSE
CREATE OR REPLACE FUNCTION notify_market_signal()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('founder_signals',
        json_build_object(
            'founder_id', NEW.founder_id,
            'source',     NEW.source,
            'score',      NEW.relevance_score
        )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists (for idempotent migration)
DROP TRIGGER IF EXISTS market_signal_notify ON market_signals;

CREATE TRIGGER market_signal_notify
AFTER INSERT ON market_signals
FOR EACH ROW EXECUTE FUNCTION notify_market_signal();

-- Insert default founder for demo
INSERT INTO founders (slack_user_id, name, stage, icp, constraints)
VALUES ('U0123456789', 'Demo Founder', 'building', 
        'B2B SaaS for DevOps teams', 
        'Solo founder, 2hrs/day, full-time job')
ON CONFLICT (slack_user_id) DO NOTHING;

-- Comment: This migration sets up the core accountability loop for Saarathi
-- - founders: Track founder profiles and context
-- - weekly_reflections: Store founder's weekly check-ins
-- - commitments: Track what founders committed to ship
-- - trigger_log: Audit trail of all intervention decisions
-- - market_signals: External signals from indie hackers, Reddit, etc.
