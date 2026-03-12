-- Founders
CREATE TABLE IF NOT EXISTS founders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_user_id VARCHAR(50) UNIQUE NOT NULL,
    slack_team_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    archetype VARCHAR(20) DEFAULT 'unknown',
    stage VARCHAR(30) DEFAULT 'pre_revenue',
    onboarding_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Company context
CREATE TABLE IF NOT EXISTS company_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    context_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,
    captured_from VARCHAR(100),
    confidence FLOAT DEFAULT 1.0,
    valid_until TIMESTAMPTZ,
    qdrant_point_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Weekly reflections
CREATE TABLE IF NOT EXISTS weekly_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    week_number INT NOT NULL,
    year INT NOT NULL,
    q1_done TEXT,
    q2_avoided TEXT,
    q3_decision TEXT,
    q4_customer TEXT,
    q5_emotion VARCHAR(50),
    raw_text TEXT,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(founder_id, week_number, year)
);

-- Commitments
CREATE TABLE IF NOT EXISTS commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    committed_at TIMESTAMPTZ DEFAULT NOW(),
    due_by TIMESTAMPTZ,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    source_trigger_id UUID,
    category VARCHAR(30),
    CONSTRAINT commitments_category_check
      CHECK (category IN ('customer_call','build','decision','admin','other'))
);

-- Trigger log
CREATE TABLE IF NOT EXISTS trigger_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) NOT NULL,
    score FLOAT NOT NULL,
    threshold_used FLOAT NOT NULL,
    fired BOOLEAN NOT NULL,
    suppression_reason TEXT,
    signal_payload JSONB,
    message_sent TEXT,
    slack_message_ts VARCHAR(50),
    founder_feedback VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory snapshots
CREATE TABLE IF NOT EXISTS memory_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    snapshot_type VARCHAR(30) NOT NULL,
    commitment_completion_rate FLOAT,
    customer_call_frequency FLOAT,
    coding_vs_customer_ratio FLOAT,
    decision_stall_avg_days FLOAT,
    momentum_score FLOAT,
    dominant_archetype VARCHAR(20),
    detected_patterns JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
