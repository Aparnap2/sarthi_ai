-- Migration: Replace Redis with PostgreSQL tables
-- Date: 2026-03-02
-- Purpose: Azure has no free Redis tier - consolidate on PostgreSQL

-- Idempotency keys (replaces Redis SETNX)
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key         VARCHAR(255) PRIMARY KEY,
    source      VARCHAR(50) NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_idempotency_created
    ON idempotency_keys(created_at);

-- Token budget (replaces Redis INCRBY)
CREATE TABLE IF NOT EXISTS token_budgets (
    task_id         VARCHAR(255) PRIMARY KEY,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    tokens_limit    INTEGER NOT NULL DEFAULT 50000,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_token_budget_task
    ON token_budgets(task_id);

-- Shared agent context (replaces Redis SharedContext)
CREATE TABLE IF NOT EXISTS agent_context (
    task_id     VARCHAR(255) NOT NULL,
    agent_role  VARCHAR(100) NOT NULL,
    findings    JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (task_id, agent_role)
);
CREATE INDEX IF NOT EXISTS idx_agent_context_task
    ON agent_context(task_id);

-- HITL pending approvals (replaces Redis hitl:pending:*)
CREATE TABLE IF NOT EXISTS hitl_queue (
    task_id         VARCHAR(255) PRIMARY KEY,
    workflow_id     VARCHAR(255) NOT NULL,
    issue_title     VARCHAR(500),
    issue_body      TEXT,
    severity        VARCHAR(50),
    status          VARCHAR(50) DEFAULT 'pending',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE
                        DEFAULT NOW() + INTERVAL '48 hours'
);
CREATE INDEX IF NOT EXISTS idx_hitl_status
    ON hitl_queue(status);
CREATE INDEX IF NOT EXISTS idx_hitl_expires
    ON hitl_queue(expires_at);

-- Agent events table (replaces Redis Pub/Sub)
-- Using PostgreSQL LISTEN/NOTIFY with this table for persistence
CREATE TABLE IF NOT EXISTS agent_events (
    id          SERIAL PRIMARY KEY,
    event_type  VARCHAR(100) NOT NULL,
    task_id     VARCHAR(255),
    agent_name  VARCHAR(100),
    message     TEXT,
    severity    VARCHAR(50) DEFAULT 'info',
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_events_task
    ON agent_events(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_created
    ON agent_events(created_at DESC);

-- Function to notify on agent events (for LISTEN/NOTIFY)
CREATE OR REPLACE FUNCTION notify_agent_event()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('agent_events', json_build_object(
        'id', NEW.id,
        'event_type', NEW.event_type,
        'task_id', NEW.task_id,
        'agent_name', NEW.agent_name,
        'message', NEW.message,
        'severity', NEW.severity,
        'created_at', NEW.created_at
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for agent events
DROP TRIGGER IF EXISTS agent_event_trigger ON agent_events;
CREATE TRIGGER agent_event_trigger
    AFTER INSERT ON agent_events
    FOR EACH ROW
    EXECUTE FUNCTION notify_agent_event();

-- Comments
COMMENT ON TABLE idempotency_keys IS 'Idempotency key storage (replaces Redis SETNX)';
COMMENT ON TABLE token_budgets IS 'Token usage tracking per task (replaces Redis INCRBY)';
COMMENT ON TABLE agent_context IS 'Shared agent context storage (replaces Redis SharedContext)';
COMMENT ON TABLE hitl_queue IS 'Human-in-the-loop approval queue (replaces Redis hitl:pending)';
COMMENT ON TABLE agent_events IS 'Agent event log with NOTIFY trigger (replaces Redis Pub/Sub)';

-- Dead Letter Queue for poison pill tasks
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     VARCHAR(255) NOT NULL,
    payload     JSONB NOT NULL,
    error_msg   TEXT NOT NULL,
    attempts    INTEGER NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dlq_task ON dead_letter_queue(task_id);
CREATE INDEX IF NOT EXISTS idx_dlq_created ON dead_letter_queue(created_at);
