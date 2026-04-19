# IterateSwarm — Actual Code Files (Excluding Tests)

> **Goal**: List only the **production code files** (no tests, no generated code, no docs) that you need to understand to work with the codebase.

---

## Go Backend (`apps/core`) — Production Code Only

### Entry Points
- `cmd/server/main.go` – HTTP server entry (receives webhooks, publishes to Redpanda)
- `cmd/worker/main.go` – Temporal worker entry (executes workflows & activities)
- `cmd/consumer/main.go` – Redpanda consumer (consumes events from Redpanda, triggers Temporal workflows)
> **Architecture Note**: The three entry points form a pipeline:  
> 1. **HTTP server** receives webhooks and publishes events to Redpanda  
> 2. **Consumer** reads events from Redpanda and starts Temporal workflows  
> 3. **Temporal worker** executes workflow activities  
> All three are required for the system to function.

### HTTP Layer (`internal/api/`)
- `handlers.go` – All HTTP endpoints
- `middleware.go` – JWT auth, CORS, logging
- `auth.go` – GitHub OAuth login
- `telegram.go` – Telegram onboarding
- `slack_onboarding.go` – Slack onboarding

### Workflows (`internal/workflow/`)
- `workflow.go` – FeedbackWorkflow
- `sarthi_router.go` – SarthiRouter + child workflows
- `business_os_workflow.go` – BusinessOSWorkflow
- `onboarding_workflow.go` – OnboardingWorkflow
- `onboarding_activities.go` – Onboarding activities
- `activities.go` – All activity implementations
- `stubs.go` – Workflow stubs (for testing, but still code)

### AI Agents (`internal/agents/`)
- `agents.go` – Agent registry
- `stubs.go` – TriageAgent + SpecAgent stubs

### Events (`internal/events/`)
- `envelope.go` – EventEnvelope struct
- `dictionary.go` – Event type constants
- `normalizer.go` – Event normalization

### Database (`internal/db/`)
- `repository.go` – Main repository
- `dbsqlc/` – **Generated** (ignore for editing)
- `migrations/` – SQL migration files (001_sarthi_sop_runtime.sql, etc.)
- `queries/` – SQL query files
- `schema/` – SQL schema files

### Root Migrations (`migrations/`)
- `001_create_users_table.sql` – Users table for GitHub OAuth
- `002_replace_redis.sql` – Redis replacement migration
- `003_saarathi_pivot.sql` – Saarathi pivot migration
- `005_week3_dashboard.sql` – Dashboard migration
- `006_onboarding.sql` – Onboarding migration
- `007_onboarding_telegram.sql` – Telegram onboarding migration
- `008_sarthi_internal_ops.sql` – Internal ops migration

### External Integrations (`internal/`)
- `temporal/client.go` – Temporal client wrapper
- `redpanda/client.go` – Redpanda client wrapper
- `grpc/client.go` – gRPC client to Python
- `webhooks/handlers.go` – Generic webhook processing
- `webhooks/payments.go` – Payment webhooks
- `webhooks/repository.go` – Webhook repository
- `integrations/adapter.go` – Integration adapter

### Web UI (`internal/web/`)
- `handler.go` – Admin dashboard
- `founder_handler.go` – Founder dashboard with SSE
- `admin_handler.go` – Admin handler
- `sse.go` – Server-Sent Events
- `razorpay.go` – Razorpay integration
- `telegram.go` – Telegram web UI
- `templates/` – HTML templates (including partials/)

### Debug Tools (`internal/debug/`)
- `handlers.go` – LiteDebug Console
- `kafka_browser.go` – Redpanda topic browser
- `workflow_inspector.go` – Temporal workflow inspector
- `trace_viewer.go` – Trace viewer

### Utilities (`internal/`)
- `logging/logger.go` – Structured logging
- `retry/retry.go` – Retry logic
- `memory/memory.go` – Memory interface
- `memory/qdrant_stub.go` – Qdrant stub
- `security/` – Security utilities (excluding `*_test.go`)

---

## Python AI Service (`apps/ai`) — Production Code Only

### Entry Points
- `src/main.py` – Main entry (Temporal + gRPC)
- `src/worker.py` – Temporal worker
- `src/debug_server.py` – Debug HTTP server
- `src/grpc_server.py` – AgentService + SOPExecutor implementation

### AI Agents (`src/agents/`)
- `base.py` – BaseAgent with banned‑jargon validation
- `anomaly/`
  - `state.py` – AnomalyState TypedDict
  - `graph.py` – LangGraph definition
  - `nodes.py` – Node functions
  - `prompts.py` – DSPy predictors
  - `thresholds.py` – Rule‑based thresholds
- `investor/`
  - `state.py`, `graph.py`, `nodes.py`, `prompts.py`
- `pulse/`
  - `state.py`, `graph.py`, `nodes.py`, `prompts.py`
- `qa/`
  - `state.py`, `graph.py`, `nodes.py`, `prompts.py`

### Activities (`src/activities/`)
- `run_anomaly_agent.py`
- `run_investor_agent.py`
- `run_pulse_agent.py`
- `run_qa_agent.py`
- `run_guardian_watchlist.py`
- `send_slack_message.py`
- `send_telegram.py`
- `base.py` – Base activity class

### Memory (`src/memory/`)
- `qdrant_ops.py` – Main Qdrant client (upsert, search, query, delete)
- `spine.py` – MemorySpine
- `rag_kernel.py` – RAG context loading
- `compressor.py` – Memory compression
- `compressed.py` – Compressed memory representation
- `episodic.py` – Episodic memory
- `procedural.py` – Procedural memory
- `semantic.py` – Semantic memory
- `working.py` – Working memory
- `state_manager.py` – State management

### Integrations (`src/integrations/`)
- `slack.py` – Slack + Telegram delivery
- `stripe.py` – Stripe webhook integration
- `plaid.py` – Plaid bank statement integration
- `product_db.py` – Product database client

### Services (`src/services/`)
- `embeddings.py` – Embedding generation
- `qdrant.py` – Qdrant service wrapper
- `relevance_scorer.py` – Relevance scoring
- `tone_filter.py` – Banned jargon check
- `langfuse_client.py` – Langfuse tracing
- `slack_notifier.py` – Slack notification service
- `crawler_service.py` – Web crawler
- `sandbox_client.py` – Sandbox execution
- `weekly_checkin.py` – Weekly check‑in logic

### Config (`src/config/`)
- `config_module.py` – Pydantic config models
- `llm.py` – LLM client configuration
- `llm_guard.py` – LLM output guardrails
- `event_dictionary.py` – Event type definitions

### SOPs (`src/sops/`)
- `base.py` – Base SOP class
- `registry.py` – SOP registry
- `bank_statement_ingest.py` – Bank statement ingestion SOP
- `revenue_received.py` – Revenue received SOP
- `weekly_briefing.py` – Weekly briefing SOP

### Workflows (`src/workflows/`)
- `compression_workflow.py`
- `eval_loop_workflow.py`
- `investor_workflow.py`
- `pulse_workflow.py`
- `qa_workflow.py`
- `self_analysis_workflow.py`
- `weight_decay_workflow.py`

### LLM Operations (`src/llmops/`)
- `eval_loop.py` – Agent evaluation loop
- `self_analysis.py` – Agent self‑analysis (DSPy)
- `tracer.py` – OpenTelemetry tracing

### HITL (`src/hitl/`)
- `manager.py` – Human‑in‑the‑loop manager
- `confidence.py` – Confidence scoring

### Guardian (`src/guardian/`)
- `detector.py` – Watchlist pattern detection
- `insight_builder.py` – Insight generation
- `watchlist.py` – Watchlist management

### Schemas (`src/schemas/`)
- `desk_results.py` – Desk result schemas
- `event_envelope.py` – Event envelope schemas

### Database (`src/db/`)
- `agent_outputs.py`
- `compliance.py`
- `contracts.py`
- `forecast.py`
- `hitl_actions.py`
- `people.py`
- `policy.py`
- `raw_events.py`
- `saas.py`
- `transactions.py`

### Setup (`src/setup/`)
- `init_qdrant_collections.py` – Qdrant collection initialization

### Scripts (`scripts/`)
- `seed_qdrant.py` – Qdrant seeding script

---

## Proto Definitions (`proto/`)
- `ai/v1/agent.proto` – gRPC service definitions

---

## Configuration Files (Root)
- `docker-compose.yml` – Local development services
- `Makefile` – Common commands
- `pyproject.toml` (in `apps/ai/`) – Python dependencies
- `go.mod` (in `apps/core/`) – Go dependencies
- `.env.example` – Environment variables template
- `sqlc.yaml` – SQLC configuration
- `buf.yaml`, `buf.gen.yaml` – Protobuf generation config

## Docker Files
- `apps/core/Dockerfile` – Go backend container
- `apps/ai/Dockerfile` – Python AI service container

---

## What’s Excluded (Not Production Code)

### Tests
- All `*_test.go` files (e.g., `handlers_test.go`, `envelope_test.go`)
- All `*_test.py` files
- All `tests/` directories (`apps/ai/tests/`, `apps/core/..._test.go`)
- `conftest.py`, `test_*.py`

### Generated Code
- `gen/` directory (protobuf‑generated code)
- `dbsqlc/` (sqlc‑generated Go code)

### Documentation
- `*.md` files (except this one)
- `ARCHITECTURE.md`, `README.md`, `AGENTS.md`, etc.

### Build Artifacts
- `bin/`, `dist/`, `__pycache__/`, `*.pyc`

### Configuration‑only
- `.github/workflows/` (CI/CD)
- `.vscode/`, `.idea/` (IDE config)

---

## Quick Count

| Service | Production Files (approx) |
|---------|---------------------------|
| Go Backend | ~50 files |
| Python AI | ~85 files |
| Proto/Config | ~12 files |
| **Total** | **~147 files** |

> **Note**: This is the actual code you need to read to understand the system. Tests and generated code are excluded as requested.
