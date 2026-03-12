-- Onboarding answers table
CREATE TABLE IF NOT EXISTS onboarding_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID REFERENCES founders(id) ON DELETE CASCADE,
    question_id VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    raw_answer TEXT NOT NULL,
    extracted_context_type VARCHAR(50),
    extracted_content TEXT,
    confidence FLOAT DEFAULT 1.0,
    qdrant_point_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(founder_id, question_id)
);

-- Add onboarding tracking to founders table
ALTER TABLE founders
    ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS onboarding_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS archetype VARCHAR(30),
    ADD COLUMN IF NOT EXISTS dynamic_threshold FLOAT DEFAULT 0.60;

-- Add index for fast onboarding lookups
CREATE INDEX IF NOT EXISTS idx_onboarding_answers_founder_id ON onboarding_answers(founder_id);
CREATE INDEX IF NOT EXISTS idx_onboarding_answers_question_id ON onboarding_answers(question_id);

-- Add column for onboarding thread tracking
ALTER TABLE founders
    ADD COLUMN IF NOT EXISTS onboarding_thread_ts VARCHAR(100);

-- Comment: This migration adds:
-- - onboarding_answers table: stores extracted context from 6-question interview
-- - founders.onboarding_complete: tracks if founder finished onboarding
-- - founders.onboarding_started_at: when founder started onboarding
-- - founders.archetype: detected founder archetype (builder/hustler/analyst/operator)
-- - founders.dynamic_threshold: personalized trigger threshold based on archetype
-- - founders.onboarding_thread_ts: Slack thread TS for onboarding conversation
