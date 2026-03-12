# IterateSwarm OS - Fullstack Test Report

**Generated:** 2026-03-11T13:31:09Z

**Services Under Test:**
- Go API (Core): http://localhost:3000
- SwarmChat: http://localhost:4000
- SwarmRepo: http://localhost:4001
- PostgreSQL: localhost:5433/iterateswarm

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | 0 |
| Passed | 0 |
| Failed | 0 |
| Pass Rate | 86% |

---

## 1. Database Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|

## 1. Database Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| PostgreSQL Connection | accepting connections | accepting connections | PASS | N/Ams |  |
| SwarmChat Channels Table | table exists | exists (1 rows) | PASS | N/Ams |  |
| SwarmChat Messages Table | table exists | exists (13 rows) | PASS | N/Ams |  |
| SwarmRepo Repos Table | table exists | exists (1 rows) | PASS | N/Ams |  |
| SwarmRepo Issues Table | table exists | exists (3 rows) | PASS | N/Ams |  |
| SwarmRepo Pull Requests Table | table exists | exists (1 rows) | PASS | N/Ams |  |
| Sample Messages Query | returns data | data returned | PASS | N/Ams |  |
| Sample Issues Query | returns data | data returned | PASS | N/Ams |  |

## 2. CRUD Tests - SwarmChat (Port 4000)

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| SwarmChat CREATE Message | 200 | 400 | FAIL | 8ms |  000{"error":"Content is required"}  |

## 3. CRUD Tests - SwarmRepo (Port 4001)

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| SwarmRepo CREATE Issue | 201 | 400 | FAIL | 7ms |  000{"error":"Title is required"}  |

## 4. CRUD Tests - Go API (Port 3000)

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Go API CREATE Feedback (Webhook) | 200 | 400 | FAIL | 7ms | Failed to create feedback |
| Go API READ Health | 200 | 200 | PASS | 6ms |  |
| Go API READ Detailed Health | 200 | 200 | PASS | 8ms |  |

## 5. Authentication Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Auth GitHub Login Endpoint | 302/200 | 307 | FAIL | 7ms | Login endpoint issue |
| Auth Protected Route (No Token) | 200/401 | 200 | PASS | 6ms |  |
| Auth Invalid Token | 401/200 | 200 | PASS | 6ms |  |

## 6. Route Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| SwarmChat Root Route | 200 | 200 | PASS | 6ms |  |
| SwarmChat Health Route | 200 | 200 | PASS | 6ms |  |
| SwarmChat Messages Route | 200 | 200 | PASS | 8ms |  |
| SwarmRepo Root Route | 200 | 200 | PASS | ms |  |
| SwarmRepo Health Route | 200 | 200 | PASS | 6ms |  |
| SwarmRepo Issues Route | 200 | 200 | PASS | 7ms |  |
| Go API Health Route | 200 | 200 | PASS | 6ms |  |
| Go API Detailed Health Route | 200 | 200 | PASS | 7ms |  |
| SwarmChat 404 Route | 404 | 404 | PASS | 6ms |  |
| SwarmRepo 404 Route | 404 | 404 | PASS | 6ms |  |
| Go API 404 Route | 404 | 404 | PASS | 6ms |  |

## 7. Integration Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Integration: Create Chat Message | 200 | 400 | FAIL | 8ms | Failed to create message |

## 8. Performance Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Performance: SwarmChat Health <100ms | <100ms | 6ms | PASS | 6ms |  |
| Performance: SwarmRepo Health <100ms | <100ms | 6ms | PASS | 6ms |  |
| Performance: Go API Health <100ms | <100ms | 6ms | PASS | 6ms |  |
| Performance: 10 Concurrent Requests <1s | <1000ms | 9ms | PASS | 9ms |  |

## 9. Error Handling Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Error: Invalid JSON | 400 | 400 | PASS | 7ms |  |
| Error: Missing Required Field | 400 | 400 | PASS | 8ms |  |
| Error: Invalid UUID | 400/404 | 404 | PASS | 6ms |  |

## 10. Database Integrity Tests

| Test Name | Expected | Actual | Status | Response Time (ms) | Error |
|-----------|----------|--------|--------|-------------------|-------|
| Integrity: Non-existent Channel | 400/404/500 | 400 | PASS | 7ms |  |
| Integrity: Non-existent Repo | 201/400 | 400 | PASS | 7ms |  |

---

## Test Summary

- **Total Tests:** 37
- **Passed:** 32
- **Failed:** 5
- **Pass Rate:** 86%

## Services Status

| Service | URL | Status |
|---------|-----|--------|
| Go API (Core) | http://localhost:3000 | Tested |
| SwarmChat | http://localhost:4000 | Tested |
| SwarmRepo | http://localhost:4001 | Tested |
| PostgreSQL | localhost:5433 | Tested |

---

*Report generated by IterateSwarm Fullstack Test Suite*
