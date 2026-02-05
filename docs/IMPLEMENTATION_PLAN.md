# IterateSwarm Production Implementation Plan (Revised)

## Senior Portfolio Priority Stack

### Phase 0: Observability First (The "Eyes") ⚡️ P0
> "If you can't see it, you can't debug it"

| Component | Tool | Port | Purpose |
|-----------|------|------|---------|
| **Jaeger** | Tracing | 16686 | Distributed tracing Go ↔ Python |
| **Grafana** | Metrics | 3000 | Dashboards for monitoring |
| **Prometheus** | Metrics | 9090 | Metrics collection |

**Tasks:**
- [ ] Add Jaeger to docker-compose.yml
- [ ] Add Prometheus scrape config for Go services
- [ ] Add Grafana dashboards for:
  - gRPC request latency (Go → Python)
  - Temporal workflow success/failure rates
  - Feedback processing throughput

---

### Phase 1: Clerk Auth (The "Plumbing") ⚡️ P1
> "30 minutes of work, not 4 hours"

**Frontend (if needed):**
- Clerk React components for sign-in/sign-up

**Go Backend:**
```go
// Just verify Clerk JWT token - don't build auth
func ClerkAuthMiddleware(clerkSecretKey string) fiber.Handler {
    return func(c *fiber.Ctx) error {
        // Extract Bearer token from Authorization header
        // Verify with Clerk's JWKS endpoint
        // Add user claims to context
        // Continue or return 401
    }
}
```

**Effort:** 30 minutes
**Outcome:** Production-ready auth without managing sessions/passwords

---

### Phase 2: AI Brain (The "Showcase") ⚡️ P0
> "This is what makes the project impressive"

#### 2.1 Ollama Embeddings Service (`apps/ai/src/services/embeddings.py`)
```python
class OllamaEmbeddings:
    """Local-first embeddings using nomic-embed-text"""
    def __init__(self, host="http://localhost:11434", model="nomic-embed-text"):
        self.host = host
        self.model = model
        self.dimensions = 768  # nomic-embed-text fixed dimension

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector"""

    async def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate similarity"""

    async def find_duplicates(self, query: str, threshold: float = 0.85) -> list[tuple[str, float]]:
        """Find semantically similar feedback"""
```

#### 2.2 DeepEval Tests (`apps/ai/tests/test_eval.py`)
```python
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric

def test_triage_classification():
    """Test bug vs feature vs question classification"""
    pass

def test_duplicate_detection():
    """Test embedding similarity threshold"""
    pass

def test_spec_quality():
    """Test generated issue spec quality"""
    pass
```

**Outcome:**
- Local embeddings (no API costs)
- Duplicate detection with 0.85 similarity threshold
- Measurable AI quality via DeepEval

---

### Phase 3: E2E Testing (The "Contract") ⚡️ P1
> "Unit tests are for functions. E2E tests for distributed systems."

#### 3.1 Mockoon API Mocks (`mockoon.json`)
```json
{
  "environments": [{
    "name": "iterateswarm-test",
    "port": 3005,
    "routes": [
      {"method": "POST", "path": "/webhooks/discord", "response": "success"},
      {"method": "POST", "path": "/api/feedback", "response": "created"},
      {"method": "POST", "path": "/ai/analyze", "response": "analysis"}
    ]
  }]
}
```

#### 3.2 Workflow Tests (`tests/e2e/workflow.sh`)
```bash
#!/bin/bash
# E2E Test: Full feedback → issue creation flow

# 1. Submit feedback (Discord webhook mock)
curl -X POST http://localhost:3005/webhooks/discord \
  -d '{"content": "Login bug", "author": "user123"}'

# 2. Verify feedback stored in PostgreSQL
psql -c "SELECT * FROM feedback WHERE content LIKE '%Login bug%'"

# 3. Verify AI analysis completed
curl http://localhost:3000/api/feedback/status

# 4. Verify duplicate check ran
curl http://localhost:6333/collections/feedback_items
```

---

## Service Ports Reference

| Service | Port | URL | Status |
|---------|------|-----|--------|
| **Go API** | 3000 | http://localhost:3000 | Existing |
| **Grafana** | 3000 | http://localhost:3000 | New |
| **PostgreSQL** | 5432 | localhost:5432 | Docker |
| **Jaeger UI** | 16686 | http://localhost:16686 | New |
| **Prometheus** | 9090 | http://localhost:9090 | New |
| **Qdrant** | 6333 | localhost:6333 | Docker |
| **Ollama** | 11434 | localhost:11434 | Docker |
| **Temporal UI** | 8088 | http://localhost:8088 | Existing |

---

## Files Modified/Created

| File | Phase | Action |
|------|-------|--------|
| `docker-compose.yml` | P0 | Add Jaeger, Prometheus, Grafana |
| `apps/core/internal/auth/clerk.go` | P1 | JWT verification middleware |
| `apps/core/cmd/server/main.go` | P1 | Integrate Clerk middleware |
| `apps/ai/src/services/embeddings.py` | P2 | Ollama embeddings class |
| `apps/ai/tests/test_eval.py` | P2 | DeepEval tests |
| `mockoon.json` | P3 | API mocks |
| `tests/e2e/workflow.sh` | P3 | E2E tests |

---

## Effort Estimation

| Phase | Effort | Priority |
|-------|--------|----------|
| P0: Observability | 2h | P0 |
| P1: Clerk Auth | 30m | P1 |
| P2: AI Brain | 4h | P0 |
| P3: E2E Tests | 2h | P1 |
| **Total** | **~8.5h** | |

---

## Success Criteria

| Criterion | Metric |
|-----------|--------|
| Traces visible | Jaeger shows Go → Python spans |
| Auth working | Protected endpoints return 401 without token |
| Embeddings | nomic-embed-text generates 768-dim vectors |
| Duplicate detection | Similar items found at 0.85 threshold |
| AI Quality | DeepEval scores > 0.8 on all metrics |
| E2E Flow | Full feedback → issue workflow completes |
