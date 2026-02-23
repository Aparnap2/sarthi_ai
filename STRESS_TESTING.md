# IterateSwarm Stress Testing Guide

## Overview

This stress testing suite validates the distributed system's performance under load using **real Docker containers** and **real Azure OpenAI API**. It tests:

- **Temporal Workflows**: Concurrent workflow execution
- **Redpanda**: Message queue throughput  
- **Azure OpenAI**: Rate limits (RPM/TPM) and concurrent API calls
- **Go API Server**: Concurrent request handling
- **Circuit Breaker**: Resilience under failure

## Architecture Under Test

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Load Tester │────▶│  Go API      │────▶│  Azure AI       │
│ (this script)│     │  (Fiber)     │     │  (Real API)     │
└─────────────┘     └──────────────┘     └─────────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Temporal    │
                     │  (Workflows) │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Redpanda    │
                     │  (Queue)     │
                     └──────────────┘
```

## Test Phases

### Phase 1: Baseline Performance
- Single request latency measurement
- Establishes baseline for comparison
- Expected: 3-7 seconds (Azure AI processing time)

### Phase 2: Sequential Load Test
- 20 sequential requests
- Tests system stability under sustained load
- Measures throughput without concurrency

### Phase 3: Concurrent Load Test
- 5-20 concurrent requests
- **Critical**: Tests Azure OpenAI rate limits
- Expect 429 errors if RPM limit exceeded
- Measures system behavior under peak load

### Phase 4: Sustained Load Test
- 30-60 seconds of continuous load
- 5 requests/second
- Tests long-term stability
- Validates circuit breaker behavior

### Phase 5: System Metrics
- Docker container resource usage
- API stats (circuit breaker, rate limits)
- Performance degradation detection

## Key Metrics

### Performance Metrics
| Metric | Expected | Notes |
|--------|----------|-------|
| Baseline Latency | 3-7s | Azure AI processing time |
| Concurrent Latency | 5-15s | Queueing under load |
| Throughput | 0.5-2 req/s | Limited by Azure AI |
| Success Rate | >80% | Some 429s expected |

### Azure OpenAI Limits (gpt-oss-120b)
- **RPM**: Requests per minute limit
- **TPM**: Tokens per minute limit
- **Concurrent**: Limited by quota tier

### System Limits
- **Circuit Breaker**: Opens after 5 failures
- **Rate Limiter**: 20 req/min per client
- **Timeout**: 30s per request

## Running the Stress Test

### Quick Test (2 minutes)
```bash
export $(grep -v '^#' .env | xargs)
STRESS_DURATION=30 CONCURRENT_REQUESTS=5 \
  bash scripts/stress_test.sh
```

### Full Test (5 minutes)
```bash
export $(grep -v '^#' .env | xargs)
STRESS_DURATION=60 CONCURRENT_REQUESTS=10 \
  bash scripts/stress_test.sh
```

### Extreme Test (10 minutes)
```bash
export $(grep -v '^#' .env | xargs)
STRESS_DURATION=120 CONCURRENT_REQUESTS=20 \
  bash scripts/stress_test.sh
```

## Expected Results

### Healthy System
```
✅ Baseline: 4203ms
✅ Sequential: 20/20 successful
✅ Concurrent: 4/5 successful (1 rate limited)
✅ Sustained: Stable over 60s
✅ Circuit Breaker: CLOSED
```

### Under Heavy Load
```
⚠️  Baseline: 4203ms
⚠️  Sequential: 20/20 successful
⚠️  Concurrent: 15/20 successful (5 rate limited - 429)
⚠️  Sustained: Degraded after 45s
✅ Circuit Breaker: CLOSED (handling load)
```

### System Failure
```
❌ Baseline: TIMEOUT
❌ Sequential: 10/20 failed
❌ Concurrent: 0/20 failed
❌ Circuit Breaker: OPEN (system protecting itself)
```

## Resource Limits (Docker)

To prevent system crashes during stress testing, set resource limits:

```yaml
# docker-compose.yml
services:
  temporal:
    mem_limit: 512m
    cpus: '1.0'

  redpanda:
    mem_limit: 400m
    cpus: '0.8'

  postgres:
    mem_limit: 150m
    cpus: '0.5'

  qdrant:
    mem_limit: 200m
    cpus: '0.5'
```

## Interpreting Results

### Good Signs
- ✅ Circuit breaker stays CLOSED
- ✅ Most requests succeed (80%+)
- ✅ Latency increases gradually (not spikes)
- ✅ System recovers after load stops

### Warning Signs
- ⚠️ Many 429 errors (hitting Azure limits)
- ⚠️ Latency >15s (queue buildup)
- ⚠️ Memory usage climbing

### Critical Issues
- ❌ Circuit breaker OPEN
- ❌ Container OOM kills
- ❌ Postgres connection pool exhausted

## What This Proves to Recruiters

1. **Real Distributed System**: Not a toy project - handles real load
2. **Production Patterns**: Circuit breaker, rate limiting, timeouts
3. **Real API Integration**: Actually hits Azure OpenAI (not mocked)
4. **Scalability Understanding**: Knows limits and bottlenecks
5. **Observability**: Metrics, logging, health checks

## Stress Test Results Directory

After running, check `stress_test_results_YYYYMMDD_HHMMSS/`:
- `baseline_response.json`: Single request details
- `concurrent_*.result`: Individual concurrent request results
- `summary.txt`: Full test summary

## Next Steps

1. Run stress test with various configurations
2. Identify bottleneck (likely Azure AI rate limits)
3. Optimize with caching or batching if needed
4. Document performance characteristics