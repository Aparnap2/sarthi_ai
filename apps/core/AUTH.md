# Authentication System

## Overview

IterateSwarm uses native JWT authentication with GitHub OAuth for admin panel access. This replaces the third-party Clerk dependency with a self-contained solution.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│  GitHub OAuth│────▶│  JWT Token  │
│  Browser    │     │   Exchange   │     │  (Cookie)   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │  (users)     │
                    └──────────────┘
```

## Components

### 1. GitHub OAuth Handler (`internal/api/auth.go`)

Handles the OAuth 2.0 flow:
- `/auth/github/login` - Initiates OAuth flow
- `/auth/github/callback` - Handles callback and creates JWT
- `/auth/logout` - Clears auth cookie

### 2. JWT Middleware (`internal/api/middleware.go`)

Validates JWT tokens on protected routes:
- Extracts token from `auth_token` cookie
- Validates signature using HMAC-SHA256
- Sets user context (`user_id`, `username`)

### 3. Test Mode Bypass

**CRITICAL FOR E2E TESTS**: When `TEST_MODE=true` or `DEV_MODE=true`:
- Authentication is bypassed
- Test user context is automatically set
- No valid JWT token required

## Environment Variables

```bash
# Required for JWT auth
JWT_SECRET=super_secret_dev_key_replace_in_prod
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
APP_URL=http://localhost:3000

# Development/Test modes
DEV_MODE=true    # Bypass auth for local development
TEST_MODE=true   # Bypass auth for E2E tests
```

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Protected Routes

All routes under these prefixes require authentication:
- `/admin/*` - Admin dashboard pages
- `/api/admin/*` - Admin API endpoints
- `/api/*` - General API endpoints
- `/api/stream/events` - SSE events

## OAuth Flow

1. User clicks "Login with GitHub"
2. Redirect to GitHub OAuth consent screen
3. User authorizes application
4. GitHub redirects back with authorization code
5. Exchange code for access token
6. Fetch user info from GitHub API
7. Upsert user in PostgreSQL
8. Generate JWT token (7-day expiry)
9. Set HTTP-only cookie
10. Redirect to admin dashboard

## JWT Token Structure

```json
{
  "sub": "user-uuid",
  "username": "github-username",
  "exp": 1234567890
}
```

## Security Features

- **HTTP-only cookies**: Prevents XSS token theft
- **Secure flag**: Enabled in production (HTTPS only)
- **SameSite=Lax**: CSRF protection
- **HMAC-SHA256**: Secure signing algorithm
- **7-day expiry**: Tokens automatically expire

## Testing

Run middleware tests:
```bash
cd apps/core
go test ./internal/api/middleware_test.go ./internal/api/middleware.go -v
```

Test cases cover:
- TEST_MODE bypass
- DEV_MODE bypass
- Production mode (requires valid token)
- Empty user context helpers

## Migration

Apply database migration:
```bash
docker exec -i iterateswarm-postgres psql -U iterateswarm -d iterateswarm < apps/core/migrations/001_create_users_table.sql
```

## GitHub OAuth Setup

1. Go to GitHub Settings > Developer Settings > OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `http://localhost:3000/auth/github/callback`
4. Copy Client ID and Client Secret to `.env`

## Local Development

For local development without GitHub OAuth:

1. Set `DEV_MODE=true` in `.env`
2. All routes will accept test user context
3. No GitHub account required

## E2E Tests

For E2E tests:

1. Set `TEST_MODE=true` in test environment
2. Tests run with test user context
3. No authentication setup required

## Troubleshooting

### 401 Unauthorized errors

1. Check if `DEV_MODE` or `TEST_MODE` is set correctly
2. Verify JWT_SECRET is set in `.env`
3. Check browser cookies for `auth_token`
4. Ensure database is accessible

### GitHub OAuth callback fails

1. Verify callback URL matches GitHub app settings
2. Check GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
3. Ensure APP_URL is correct

### Token validation fails

1. Check JWT_SECRET hasn't changed
2. Verify token hasn't expired (7 days)
3. Clear browser cookies and re-login
