-- Week 3: Dashboard + Snooze Tracking
-- Migration 005: Materialized view for dashboard summary, snooze fields, and NOTIFY triggers

-- Snooze tracking for trigger_log
ALTER TABLE trigger_log
    ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS snooze_count  INTEGER DEFAULT 0;

-- Dashboard summary materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS founder_dashboard_summary AS
SELECT
    f.id                                    AS founder_id,
    f.name,
    f.stage,
    COUNT(c.id) FILTER (WHERE c.completed = true)::float /
        NULLIF(COUNT(c.id), 0)              AS commitment_rate,
    COUNT(c.id) FILTER (
        WHERE c.completed = false
        AND c.due_date < NOW())             AS overdue_count,
    COUNT(tl.id) FILTER (
        WHERE tl.fired = true
        AND tl.created_at > NOW() - INTERVAL '30 days')
                                            AS triggers_fired_30d,
    COUNT(tl.id) FILTER (
        WHERE tl.fired = false
        AND tl.created_at > NOW() - INTERVAL '30 days')
                                            AS triggers_suppressed_30d,
    COUNT(tl.id) FILTER (
        WHERE tl.founder_rating = 1)        AS positive_ratings,
    COUNT(tl.id) FILTER (
        WHERE tl.founder_rating = -1)       AS negative_ratings,
    MAX(wr.created_at)                      AS last_reflection_at,
    EXTRACT(EPOCH FROM (NOW() - MAX(wr.created_at)))/86400
                                            AS days_since_reflection,
    ARRAY(
        SELECT energy_score
        FROM weekly_reflections
        WHERE founder_id = f.id
        ORDER BY created_at DESC
        LIMIT 4
    )                                       AS energy_trend
FROM founders f
LEFT JOIN commitments       c  ON c.founder_id = f.id
LEFT JOIN trigger_log       tl ON tl.founder_id = f.id
LEFT JOIN weekly_reflections wr ON wr.founder_id = f.id
GROUP BY f.id, f.name, f.stage;

-- Index for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_dashboard_summary_founder_id 
    ON founder_dashboard_summary(founder_id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_dashboard_summary()
RETURNS void AS $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY founder_dashboard_summary;
$$ LANGUAGE sql;

-- NOTIFY for SSE
CREATE OR REPLACE FUNCTION notify_dashboard_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('dashboard_update',
        json_build_object('founder_id', NEW.founder_id)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop triggers if exist (for idempotent migration)
DROP TRIGGER IF EXISTS commitment_dashboard_notify ON commitments;
DROP TRIGGER IF EXISTS trigger_log_dashboard_notify ON trigger_log;

CREATE TRIGGER commitment_dashboard_notify
    AFTER INSERT OR UPDATE ON commitments
    FOR EACH ROW EXECUTE FUNCTION notify_dashboard_update();

CREATE TRIGGER trigger_log_dashboard_notify
    AFTER INSERT OR UPDATE ON trigger_log
    FOR EACH ROW EXECUTE FUNCTION notify_dashboard_update();

-- Comment: This migration adds:
-- - snoozed_until, snooze_count to trigger_log for snooze functionality
-- - founder_dashboard_summary materialized view for fast dashboard queries
-- - refresh_dashboard_summary() function for manual/periodic refresh
-- - notify_dashboard_update() + triggers for SSE live updates
-- - Unique index on materialized view for CONCURRENTLY refresh
