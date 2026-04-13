# Mockoon Integration Testing Guide

**Sarthi v1.0** — HITL + BI Query Mock Testing

---

## Overview

This guide documents the Mockoon-based integration testing setup for Sarthi v1.0. Mockoon replaces the real Go server during testing, providing fast, deterministic mock responses for all external-facing endpoints.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEST EXECUTION LAYER                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Bash Tests  │  │ Python Tests │  │ Playwright E2E       │   │
│  │ (test-with- │  │ (pytest)     │  │ (browser automation) │   │
│  │  mockoon.sh)│  │              │  │                      │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │ HTTP requests
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MOCKOON MOCK SERVER                          │
│  Port: 3000                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Routes (6 endpoints):                                   │   │
│  │  • GET  /health                      — Health check      │   │
│  │  • POST /internal/hitl/investigate   — HITL signal       │   │
│  │  • POST /internal/hitl/dismiss       — HITL dismiss      │   │
│  │  • POST /internal/query              — BI query          │   │
│  │  • POST /bot:test-token/sendMessage  — Telegram mock     │   │
│  │  • POST /bot:test-token/sendPhoto    — Telegram mock     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION                                │
│  config/mockoon-sarthi.json — Mockoon environment definition    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- **No Docker overhead** — Mockoon CLI runs as a Node.js process
- **Fast startup** — Ready in ~3 seconds vs 30+ seconds for containers
- **Deterministic responses** — No flakiness from real service dependencies
- **Validation rules** — Mockoon validates request structure automatically

---

## Quick Start

### Prerequisites

```bash
# Install Mockoon CLI (one-time)
npm install -g @mockoon/cli

# Verify installation
mockoon-cli --version
```

### Start Mockoon

```bash
cd /home/aparna/Desktop/iterate_swarm

# Start Mockoon server
bash scripts/start-mockoon.sh
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════╗
║     SARTHI v1.0 — MOCKOON CLI STARTING                  ║
╚══════════════════════════════════════════════════════════╝

✅ Mockoon ready on port 3000

Available endpoints:
  GET  http://localhost:3000/health
  POST http://localhost:3000/internal/hitl/investigate
  POST http://localhost:3000/internal/hitl/dismiss
  POST http://localhost:3000/internal/query
  POST http://localhost:3000bot:test-token/sendMessage
  POST http://localhost:3000bot:test-token/sendPhoto

Process ID: 12345
```

### Stop Mockoon

```bash
bash scripts/stop-mockoon.sh
```

### Verify Mockoon is Running

```bash
curl -sf http://localhost:3000/health | jq
```

**Response:**
```json
{
  "status": "ok",
  "service": "sarthi-core-mock",
  "time": "2026-03-21T18:23:05.847+05:30"
}
```

---

## Available Endpoints

| Method | Endpoint | Description | Status Code |
|--------|----------|-------------|-------------|
| `GET` | `/health` | Health check | 200 |
| `POST` | `/internal/hitl/investigate` | Send HITL investigate signal | 200 / 400 |
| `POST` | `/internal/hitl/dismiss` | Send HITL dismiss signal | 200 |
| `POST` | `/internal/query` | Submit BI query | 202 / 400 |
| `POST` | `/bot:test-token/sendMessage` | Telegram sendMessage mock | 200 |
| `POST` | `/bot:test-token/sendPhoto` | Telegram sendPhoto mock | 200 |

---

## Endpoint Specifications

### GET `/health`

Health check endpoint.

**Request:**
```bash
curl http://localhost:3000/health
```

**Response (200):**
```json
{
  "status": "ok",
  "service": "sarthi-core-mock",
  "time": "2026-03-21T18:23:05.847+05:30"
}
```

---

### POST `/internal/hitl/investigate`

Send Human-in-the-Loop investigate signal to Temporal workflow.

**Request:**
```bash
curl -X POST http://localhost:3000/internal/hitl/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "finance-abc123",
    "tenant_id": "test-tenant",
    "vendor": "AWS"
  }'
```

**Response (200):**
```json
{
  "ok": true,
  "action": "investigate",
  "workflow_id": "finance-abc123",
  "message": "Investigate signal sent to Temporal workflow"
}
```

**Validation:**
- `workflow_id` is required
- Missing `workflow_id` returns 400 with error message

**Response (400):**
```json
{
  "error": "workflow_id required"
}
```

---

### POST `/internal/hitl/dismiss`

Send Human-in-the-Loop dismiss signal to Temporal workflow.

**Request:**
```bash
curl -X POST http://localhost:3000/internal/hitl/dismiss \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "finance-xyz789",
    "tenant_id": "test-tenant",
    "vendor": "Vercel"
  }'
```

**Response (200):**
```json
{
  "ok": true,
  "action": "dismiss",
  "workflow_id": "finance-xyz789",
  "message": "Dismiss signal sent to Temporal workflow"
}
```

---

### POST `/internal/query`

Submit a Business Intelligence query for async processing.

**Request:**
```bash
curl -X POST http://localhost:3000/internal/query \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "query": "What are total expenses by vendor last 30 days?",
    "query_type": "ADHOC"
  }'
```

**Response (202):**
```json
{
  "ok": true,
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow_id": "bi-test-te-550e8400",
  "message": "Query queued. Result sent to Telegram."
}
```

**Validation:**
- `query` field is required
- Missing `query` returns 400 with error message

---

### POST `/bot:test-token/sendMessage`

Mock Telegram Bot API `sendMessage` endpoint.

**Request:**
```bash
curl -X POST http://localhost:3000/bot:test-token/sendMessage \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "42",
    "text": "🔴 Finance Alert: AWS bill 2.3× usual",
    "parse_mode": "Markdown"
  }'
```

**Response (200):**
```json
{
  "ok": true,
  "result": {
    "message_id": 5678,
    "chat": {
      "id": "42",
      "type": "private"
    },
    "date": 1711024985,
    "text": "🔴 Finance Alert: AWS bill 2.3× usual"
  }
}
```

---

### POST `/bot:test-token/sendPhoto`

Mock Telegram Bot API `sendPhoto` endpoint.

**Request:**
```bash
curl -X POST http://localhost:3000/bot:test-token/sendPhoto \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "42",
    "caption": "AWS expenses breakdown"
  }'
```

**Response (200):**
```json
{
  "ok": true,
  "result": {
    "message_id": 5679,
    "chat": {
      "id": "42",
      "type": "private"
    },
    "date": 1711024986,
    "photo": {
      "file_id": "AgACAgIAAxkBAAIB",
      "file_unique_id": "AQADG4cxY6V9a0g"
    },
    "caption": "AWS expenses breakdown"
  }
}
```

---

## Running Tests

### Bash Integration Tests

Run the full test suite (14 tests):

```bash
cd /home/aparna/Desktop/iterate_swarm

# Ensure Mockoon is running
bash scripts/start-mockoon.sh &
sleep 5

# Run tests
bash scripts/test-with-mockoon.sh
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════╗
║     SARTHI v1.0 — MOCKOON INTEGRATION TESTS             ║
╚══════════════════════════════════════════════════════════╝

1. Checking Mockoon...
  ✅ Mockoon running on port 3000

2. Testing HITL Investigate...
  ✅ HITL investigate returns ok=true
  ✅ HITL investigate returns correct action

3. Testing HITL Investigate (validation)...
  ✅ HITL investigate validates workflow_id

4. Testing HITL Dismiss...
  ✅ HITL dismiss returns ok=true
  ✅ HITL dismiss returns correct action

5. Testing BI Query...
  ✅ BI query returns ok=true
  ✅ BI query returns workflow_id
  ✅ BI query returns query_id

6. Testing BI Query (validation)...
  ✅ BI query validates query field

7. Testing Telegram sendMessage mock...
  ✅ Telegram sendMessage returns ok=true
  ✅ Telegram sendMessage returns message_id

8. Testing Telegram sendPhoto mock...
  ✅ Telegram sendPhoto returns ok=true
  ✅ Telegram sendPhoto returns photo object

╔══════════════════════════════════════════════════════════╗
║     TEST SUMMARY                                        ║
╚══════════════════════════════════════════════════════════╝

  Passed: 14
  Failed: 0

✅ ALL TESTS PASSED
```

### Python Integration Tests

```bash
cd /home/aparna/Desktop/iterate_swarm/apps/ai

# Set environment variable
export MOCKOON_BASE_URL=http://localhost:3000

# Run tests
uv run pytest tests/integration/test_mockoon_endpoints.py -v --timeout=30
```

### Smoke Tests (with Mockoon)

The main smoke test script includes Mockoon testing:

```bash
bash scripts/smoke_test.sh
```

This will:
1. Start Mockoon automatically
2. Test health, HITL, and BI query endpoints
3. Keep Mockoon running for subsequent E2E tests
4. Stop Mockoon on completion

---

## Test Coverage Summary

| Component | Endpoints | Tests | Coverage |
|-----------|-----------|-------|----------|
| HITL | 2 | 5 | ✅ Success + Validation |
| BI Query | 1 | 4 | ✅ Success + Validation |
| Telegram Mocks | 2 | 4 | ✅ sendMessage + sendPhoto |
| Health | 1 | 1 | ✅ Basic health check |
| **Total** | **6** | **14** | **100%** |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  mockoon-integration:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Mockoon CLI
        run: npm install -g @mockoon/cli
      
      - name: Start Mockoon
        run: |
          bash scripts/start-mockoon.sh &
          sleep 5
      
      - name: Run Bash Integration Tests
        run: bash scripts/test-with-mockoon.sh
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install Python dependencies
        run: |
          cd apps/ai
          uv sync
      
      - name: Run Python Integration Tests
        run: |
          cd apps/ai
          MOCKOON_BASE_URL=http://localhost:3000 \
            uv run pytest tests/integration/test_mockoon_endpoints.py -v
      
      - name: Stop Mockoon
        if: always()
        run: bash scripts/stop-mockoon.sh
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
integration-tests:
  stage: test
  image: node:20-alpine
  
  before_script:
    - npm install -g @mockoon/cli
    - apk add --no-cache python3 py3-pip
    - pip install uv
  
  script:
    - bash scripts/start-mockoon.sh &
    - sleep 5
    - bash scripts/test-with-mockoon.sh
    - cd apps/ai && uv sync
    - MOCKOON_BASE_URL=http://localhost:3000 uv run pytest tests/integration/ -v
  
  after_script:
    - bash scripts/stop-mockoon.sh || true
```

---

## Troubleshooting

### Mockoon fails to start

```bash
# Check if port 3000 is in use
lsof -i :3000

# Kill any existing Mockoon processes
pkill -f mockoon-cli
bash scripts/stop-mockoon.sh

# Check Mockoon CLI installation
mockoon-cli --version

# Reinstall if needed
npm install -g @mockoon/cli
```

### Tests fail with connection refused

```bash
# Verify Mockoon is running
curl -v http://localhost:3000/health

# Check process
ps aux | grep mockoon

# Check PID file
cat /tmp/sarthi-mockoon.pid
```

### Mockoon returns wrong response

Check the request body matches the expected format:

```bash
# Enable verbose logging
bash scripts/start-mockoon.sh 2>&1 | tee /tmp/mockoon-debug.log

# Check request in real-time
tail -f /tmp/mockoon-sarthi.log
```

---

## Configuration Reference

### Mockoon Data File

Location: `config/mockoon-sarthi.json`

Key configuration options:
- `port`: Server port (default: 3000)
- `hostname`: Bind address (default: 0.0.0.0)
- `cors`: Enable CORS (default: true)
- `routes[]`: Array of route definitions

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_PORT` | 3000 | Mockoon server port |
| `MOCKOON_BASE_URL` | http://localhost:3000 | Base URL for tests |

---

## Best Practices

1. **Always start Mockoon before tests** — Use `scripts/start-mockoon.sh`
2. **Clean up after tests** — Use `scripts/stop-mockoon.sh` or `after_script` in CI
3. **Use environment variables** — Set `MOCKOON_BASE_URL` for test flexibility
4. **Test validation rules** — Verify 400 responses for missing required fields
5. **Keep mocks in sync** — Update `mockoon-sarthi.json` when API changes

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) — System architecture
- [AGENTS.md](../AGENTS.md) — Development guidelines
- [scripts/README.md](./scripts/README.md) — Script documentation

---

**Last Updated:** 2026-03-21  
**Version:** Sarthi v1.0 Phase 4
