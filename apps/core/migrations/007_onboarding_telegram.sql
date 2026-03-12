-- Add telegram_user_id to founders table for Telegram bot integration
-- This column links the founder to their Telegram user ID for onboarding messages

ALTER TABLE founders
    ADD COLUMN IF NOT EXISTS telegram_user_id VARCHAR(100);

-- Add index for fast Telegram user lookups
CREATE INDEX IF NOT EXISTS idx_founders_telegram_user_id ON founders(telegram_user_id);

-- Comment: This migration adds:
-- - founders.telegram_user_id: Telegram user ID for bot messaging
