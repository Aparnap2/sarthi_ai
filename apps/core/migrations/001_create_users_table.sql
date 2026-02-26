-- Migration: Create users table for GitHub OAuth authentication
-- Run: docker exec -i iterateswarm-postgres psql -U iterateswarm -d iterateswarm < apps/core/migrations/001_create_users_table.sql

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups by github_id
CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);

-- Index for faster lookups by username
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Comment on table
COMMENT ON TABLE users IS 'User accounts for GitHub OAuth authentication';
COMMENT ON COLUMN users.id IS 'Unique user identifier';
COMMENT ON COLUMN users.github_id IS 'GitHub user ID for OAuth linkage';
COMMENT ON COLUMN users.username IS 'GitHub username';
COMMENT ON COLUMN users.email IS 'User email from GitHub (may be null if private)';
COMMENT ON COLUMN users.avatar_url IS 'GitHub avatar URL';
COMMENT ON COLUMN users.created_at IS 'Account creation timestamp';
COMMENT ON COLUMN users.last_login IS 'Last login timestamp';
