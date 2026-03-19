# Vectorless RAG Implementation Checklist

**Project:** Sarthi Document Processing Pipeline  
**Version:** 1.0.0  
**Created:** March 19, 2026  
**Status:** 🟡 In Progress

---

## Phase 1: Docling Integration (PDF → JSON)

**Duration:** 2-3 days  
**Owner:** Backend Developer  
**Status:** ⬜ Not Started

### Setup
- [ ] Install docling Python package: `uv add docling`
- [ ] Verify Ollama has `ibm/granite-docling:latest` model
- [ ] Create sample test PDFs directory: `apps/ai/tests/fixtures/pdfs/`
- [ ] Add sample documents:
  - [ ] Bank statement (2-3 pages, with tables)
  - [ ] Invoice (AWS/Azure-style, with line items)
  - [ ] Board deck (quarterly metrics, commitments table)

### Implementation
- [ ] Create `apps/ai/src/document_processing/docling_parser.py`
- [ ] Implement `DoclingParser` class with methods:
  - [ ] `parse_pdf(pdf_path: str) -> Dict[str, Any]`
  - [ ] `parse_to_doc_chunks(pdf_path: str) -> List[DocChunk]`
  - [ ] `extract_tables(pdf_path: str) -> List[Dict[str, Any]]`
- [ ] Add type hints (mypy --strict compatible)
- [ ] Add Google-style docstrings with examples
- [ ] Write `apps/ai/src/document_processing/__init__.py`

### Testing
- [ ] Test PDF parsing on sample bank statement
  - [ ] Verify page count matches
  - [ ] Verify text extraction accuracy
- [ ] Verify table structure preservation
  - [ ] Check cell row/column indices
  - [ ] Check bounding box coordinates
- [ ] Create output schema for Sarthi documents
  - [ ] Invoice schema validation
  - [ ] Bank statement schema validation
  - [ ] Board deck schema validation
- [ ] Write `apps/ai/tests/test_docling_parser.py`
  - [ ] `test_parse_invoice_pdf()`
  - [ ] `test_extract_tables_from_bank_statement()`
  - [ ] `test_bounding_box_coordinates()`

### Benchmarking
- [ ] Measure parse latency per page
  - [ ] Target: < 5s/page
  - [ ] Record P50, P95, P99
- [ ] Measure memory usage
  - [ ] Target: < 500MB for 10-page document
- [ ] Document results in `docs/benchmarks/docling_performance.md`

### Deliverables
- [ ] `apps/ai/src/document_processing/docling_parser.py` ✅
- [ ] `apps/ai/tests/test_docling_parser.py`
- [ ] Benchmark report

---

## Phase 2: LangExtract Integration (JSON → Metadata Chunks)

**Duration:** 3-4 days  
**Owner:** LLM Engineer  
**Status:** ⬜ Not Started

### Setup
- [ ] Install langextract: `uv add langextract`
- [ ] Verify LangExtract version: `v1_0_7`
- [ ] Configure Ollama model for extraction: `qwen3:0.6b`
- [ ] Create few-shot examples directory: `apps/ai/src/document_processing/examples/`

### Schema Definition
- [ ] Define schema for invoices (`INVOICE_SCHEMA`)
  - [ ] `vendor_name`: string (exact company name)
  - [ ] `invoice_amount`: float (in INR, without currency symbol)
  - [ ] `invoice_date`: date (YYYY-MM-DD format)
  - [ ] `invoice_number`: string (invoice ID)
  - [ ] `category`: enum[infrastructure, payroll, marketing, office, misc]
  - [ ] `anomaly_flag`: boolean (true if amount > 2x average)
- [ ] Define schema for bank statements (`BANK_STATEMENT_SCHEMA`)
  - [ ] `transactions`: array of transaction objects
  - [ ] `transaction.date`: date (YYYY-MM-DD)
  - [ ] `transaction.description`: string
  - [ ] `transaction.debit`: float
  - [ ] `transaction.credit`: float
  - [ ] `transaction.balance`: float
  - [ ] `transaction.category`: enum
- [ ] Define schema for board decks (`BOARD_DECK_SCHEMA`)
  - [ ] `quarter`: string (e.g., Q1_2026)
  - [ ] `revenue`: float (quarterly revenue in INR)
  - [ ] `burn_rate`: float (monthly burn in INR)
  - [ ] `runway_months`: float
  - [ ] `key_metrics`: array
  - [ ] `commitments_made`: array with status tracking

### Implementation
- [ ] Create `apps/ai/src/document_processing/langextract_schema.py`
- [ ] Implement `create_invoice_examples() -> List[lx.data.ExampleData]`
- [ ] Implement `create_bank_statement_examples() -> List[lx.data.ExampleData]`
- [ ] Implement `create_board_deck_examples() -> List[lx.data.ExampleData]`
- [ ] Implement `extract_from_document()` function with:
  - [ ] Schema enforcement
  - [ ] Source span tracing
  - [ ] Parallel processing config
  - [ ] Error handling
- [ ] Add retry logic for batch API failures
  - [ ] Use `tenacity` library
  - [ ] Max retries: 3
  - [ ] Backoff: exponential

### Testing
- [ ] Write extraction script with source span tracing
  - [ ] Verify character-level alignment
  - [ ] Test `entity.char_interval.start_pos-end_pos`
- [ ] Test parallel processing on large documents
  - [ ] Config: `max_char_buffer=500, batch_length=1000, max_workers=4`
  - [ ] Test on 50+ page document
- [ ] Write `apps/ai/tests/test_langextract_schema.py`
  - [ ] `test_invoice_extraction()`
  - [ ] `test_bank_statement_transaction_extraction()`
  - [ ] `test_board_deck_commitment_extraction()`
  - [ ] `test_source_span_tracing()`
  - [ ] `test_parallel_processing()`

### Benchmarking
- [ ] Measure extraction latency per page
  - [ ] Target: < 10s/page
  - [ ] Record P50, P95, P99
- [ ] Measure extraction accuracy
  - [ ] Manual validation on 20 sample documents
  - [ ] Target: > 95% accuracy
- [ ] Document results in `docs/benchmarks/langextract_performance.md`

### Deliverables
- [ ] `apps/ai/src/document_processing/langextract_schema.py` ✅
- [ ] `apps/ai/tests/test_langextract_schema.py`
- [ ] Few-shot examples for 3 document types
- [ ] Benchmark report

---

## Phase 3: Elasticsearch Setup

**Duration:** 2-3 days  
**Owner:** Backend Developer  
**Status:** ⬜ Not Started

### Infrastructure
- [ ] Add Elasticsearch to `docker-compose.yml`
  ```yaml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.18.3
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=sarthi-es-password
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 5
  ```
- [ ] Add volume: `volumes: es_data:`
- [ ] Update `.env.example` with ES credentials
- [ ] Create `scripts/start_elasticsearch.sh`
- [ ] Create `scripts/stop_elasticsearch.sh`

### Index Configuration
- [ ] Create `apps/ai/src/document_processing/elasticsearch_index.py`
- [ ] Implement `create_sarthi_index(tenant_id: str) -> None`
  - [ ] Index name: `sarthi-docs-{tenant_id}`
  - [ ] Mappings with metadata fields
  - [ ] Analyzers for full-text search
- [ ] Implement `index_document(tenant_id: str, doc: Dict[str, Any]) -> str`
- [ ] Implement `bulk_index_documents(tenant_id: str, docs: List[Dict]) -> List[str]`
- [ ] Implement `delete_index(tenant_id: str) -> None`

### Query Implementation
- [ ] Implement `query_invoices_for_vendor()`
  - [ ] Metadata filter: vendor_name (term)
  - [ ] Metadata filter: invoice_amount (range)
  - [ ] BM25: text content match
- [ ] Implement `query_bank_transactions()`
  - [ ] Date range filter
  - [ ] Amount range filter
  - [ ] Category filter
- [ ] Implement `query_board_commitments()`
  - [ ] Quarter filter
  - [ ] Status filter
  - [ ] Deadline range
- [ ] Implement `build_filters()` helper function

### Hybrid Search (Optional)
- [ ] Configure semantic_text field in index mapping
- [ ] Set up embedding model inference in ES
  - [ ] Model: `sarthi-embedding-model`
  - [ ] Configure inference endpoint
- [ ] Implement `hybrid_search_with_rrf()`
  - [ ] RRF config: `rank_window_size=50, rank_constant=20`
  - [ ] BM25 retriever
  - [ ] Semantic retriever
  - [ ] RRF fusion
- [ ] Test hybrid queries vs pure BM25

### Testing
- [ ] Write `apps/ai/tests/test_elasticsearch_index.py`
  - [ ] `test_create_index()`
  - [ ] `test_index_document()`
  - [ ] `test_bulk_index()`
  - [ ] `test_query_invoices_for_vendor()`
  - [ ] `test_query_bank_transactions()`
  - [ ] `test_metadata_filters()`
  - [ ] `test_hybrid_search_with_rrf()` (optional)
- [ ] Test BM25 queries
  - [ ] Relevance scoring accuracy
  - [ ] Query latency
- [ ] Test metadata filters
  - [ ] Term filters (vendor, category)
  - [ ] Range filters (amount, date)
  - [ ] Bool filters (AND, OR)

### Benchmarking
- [ ] Measure query latency
  - [ ] Target: P95 < 100ms
  - [ ] Test with 10K, 100K, 1M documents
- [ ] Measure indexing throughput
  - [ ] Target: > 1000 docs/second
- [ ] Document results in `docs/benchmarks/elasticsearch_performance.md`

### Deliverables
- [ ] `apps/ai/src/document_processing/elasticsearch_index.py` ✅
- [ ] `docker-compose.yml` updated with ES
- [ ] `apps/ai/tests/test_elasticsearch_index.py`
- [ ] Benchmark report

---

## Phase 4: Agent Integration

**Duration:** 3-4 days  
**Owner:** AI Agent Developer  
**Status:** ⬜ Not Started

### Finance Monitor Upgrade
- [ ] Locate Finance Monitor agent: `apps/ai/src/agents/finance_monitor.py`
- [ ] Add document query function:
  - [ ] `query_vendor_spend()`
  - [ ] `detect_invoice_anomalies()`
  - [ ] `get_monthly_spend_by_category()`
- [ ] Update agent prompt with document retrieval capability
- [ ] Add tool registration for document queries
- [ ] Write integration tests:
  - [ ] `test_finance_monitor_invoice_query()`
  - [ ] `test_finance_monitor_anomaly_detection()`

### Chief of Staff Upgrade
- [ ] Locate Chief of Staff agent: `apps/ai/src/agents/chief_of_staff.py`
- [ ] Add document query function:
  - [ ] `query_board_commitments()`
  - [ ] `track_commitments_by_deadline()`
  - [ ] `get_quarterly_metrics()`
- [ ] Update agent prompt with document retrieval capability
- [ ] Add tool registration for document queries
- [ ] Write integration tests:
  - [ ] `test_chief_of_staff_commitment_tracking()`
  - [ ] `test_chief_of_staff_quarterly_metrics()`

### End-to-End Testing
- [ ] Write integration tests (PDF → agent answer)
  - [ ] `test_pdf_to_finance_answer()`
  - [ ] `test_pdf_to_chief_of_staff_answer()`
- [ ] Create E2E test fixtures:
  - [ ] Sample invoice PDF
  - [ ] Sample board deck PDF
  - [ ] Expected agent responses
- [ ] Run E2E tests with Playwright (if UI involved)

### Performance Benchmarking
- [ ] Benchmark latency vs Qdrant-only approach
  - [ ] Query: "AWS invoices over ₹30,000"
  - [ ] Measure: Vectorless vs Hybrid vs Vector-only
  - [ ] Record: Latency, accuracy, cost
- [ ] A/B test accuracy on financial queries
  - [ ] 20 sample queries
  - [ ] Manual evaluation
  - [ ] Target: > 90% accuracy

### Deliverables
- [ ] Updated Finance Monitor agent
- [ ] Updated Chief of Staff agent
- [ ] Integration test suite
- [ ] Benchmark comparison report

---

## Phase 5: Production Hardening

**Duration:** 3-5 days  
**Owner:** Backend Developer + DevOps  
**Status:** ⬜ Not Started

### Error Handling
- [ ] Add error handling for corrupt PDFs
  - [ ] Catch `docling.exceptions.PDFParseError`
  - [ ] Log error with filename
  - [ ] Return structured error response
- [ ] Add error handling for extraction failures
  - [ ] Catch `langextract.exceptions.ExtractionError`
  - [ ] Retry with smaller chunks
  - [ ] Fallback to manual review queue
- [ ] Add error handling for ES indexing failures
  - [ ] Catch `elasticsearch.exceptions.ElasticsearchException`
  - [ ] Retry with exponential backoff
  - [ ] Dead letter queue for failed docs

### Retry Logic
- [ ] Add retry logic for LangExtract batch API
  - [ ] Library: `tenacity`
  - [ ] Max retries: 3
  - [ ] Backoff: exponential (1s, 2s, 4s)
  - [ ] Jitter: random (0-1s)
- [ ] Add retry logic for ES bulk indexing
  - [ ] Max retries: 3
  - [ ] Backoff: exponential
- [ ] Add circuit breaker for external APIs
  - [ ] Library: `pybreaker`
  - [ ] Failure threshold: 5
  - [ ] Recovery timeout: 30s

### Monitoring
- [ ] Add monitoring for extraction latency
  - [ ] Metric: `docling_parse_latency_seconds`
  - [ ] Metric: `langextract_latency_seconds`
  - [ ] Metric: `es_index_latency_seconds`
- [ ] Add monitoring for query latency
  - [ ] Metric: `es_query_latency_seconds`
  - [ ] Histogram: P50, P95, P99
- [ ] Add monitoring for error rates
  - [ ] Metric: `document_ingestion_errors_total`
  - [ ] Metric: `extraction_failures_total`
- [ ] Set up alerts:
  - [ ] Alert: Extraction latency > 30s
  - [ ] Alert: Query latency P95 > 500ms
  - [ ] Alert: Error rate > 5%

### Observability
- [ ] Add structured logging
  - [ ] Library: `structlog` or `loguru`
  - [ ] Log: document_id, tenant_id, latency, status
- [ ] Add distributed tracing
  - [ ] Library: OpenTelemetry
  - [ ] Trace: PDF → Docling → LangExtract → ES
- [ ] Create dashboards:
  - [ ] Document ingestion pipeline
  - [ ] Query performance
  - [ ] Error rates

### Documentation
- [ ] Write runbook for document ingestion failures
  - [ ] Symptoms: Failed extractions
  - [ ] Diagnosis: Check logs, metrics
  - [ ] Resolution: Retry, manual review
- [ ] Write runbook for ES cluster issues
  - [ ] Symptoms: High query latency
  - [ ] Diagnosis: Check cluster health
  - [ ] Resolution: Scale, optimize queries
- [ ] Update `docs/VECTORLESS_RAG_ARCHITECTURE.md` with lessons learned

### Security
- [ ] Validate all input PDFs
  - [ ] Max file size: 50MB
  - [ ] Allowed MIME types: application/pdf
  - [ ] Virus scan (optional: ClamAV)
- [ ] Encrypt ES data at rest
  - [ ] Enable X-Pack security
  - [ ] TLS for ES connections
- [ ] Audit logging
  - [ ] Log: who uploaded, when, what document
  - [ ] Retain logs: 90 days

### Deliverables
- [ ] Error handling implementation
- [ ] Retry logic with tenacity
- [ ] Monitoring dashboards
- [ ] Runbooks for operations
- [ ] Security hardening checklist

---

## Phase 6: Hybrid Search (RRF with Qdrant)

**Duration:** 3-5 days  
**Owner:** LLM Engineer + Backend Developer  
**Status:** ⬜ Not Started

### Elasticsearch Configuration
- [ ] Configure semantic_text field
  - [ ] Inference ID: `sarthi-embedding-model`
  - [ ] Model: BGE-M3 or similar
- [ ] Set up embedding model inference
  - [ ] Option 1: ES inference API
  - [ ] Option 2: External embedding service
- [ ] Test semantic search queries

### Qdrant Integration
- [ ] Create Qdrant index for same documents
  - [ ] Collection: `sarthi-docs-{tenant_id}-vectors`
  - [ ] Vector size: 1024 (BGE-M3)
  - [ ] Distance: cosine
- [ ] Index documents with embeddings
  - [ ] Embed text field from Docling output
  - [ ] Store same metadata as ES
- [ ] Implement dual-write pipeline
  - [ ] Write to ES + Qdrant atomically
  - [ ] Handle failures gracefully

### RRF Implementation
- [ ] Implement RRF retriever in ES
  - [ ] BM25 retriever (ES)
  - [ ] kNN retriever (Qdrant via ES remote)
  - [ ] RRF fusion
- [ ] Tune RRF parameters
  - [ ] `rank_window_size`: 50, 100, 200
  - [ ] `rank_constant`: 20, 40, 60
  - [ ] Measure accuracy for each config
- [ ] Compare RRF vs BM25-only vs Vector-only
  - [ ] 20 sample queries
  - [ ] Manual relevance scoring
  - [ ] Select best configuration

### Testing
- [ ] Write `apps/ai/tests/test_hybrid_search.py`
  - [ ] `test_rrf_fusion()`
  - [ ] `test_hybrid_vs_bm25()`
  - [ ] `test_hybrid_vs_vector_only()`
- [ ] Benchmark hybrid search latency
  - [ ] Target: P95 < 200ms (vs 100ms for BM25-only)

### Deliverables
- [ ] Hybrid search implementation
- [ ] RRF tuning report
- [ ] Accuracy comparison: Vectorless vs Hybrid

---

## Summary Checklist

### Code Files
- [ ] `apps/ai/src/document_processing/__init__.py`
- [ ] `apps/ai/src/document_processing/docling_parser.py` ✅
- [ ] `apps/ai/src/document_processing/langextract_schema.py` ✅
- [ ] `apps/ai/src/document_processing/elasticsearch_index.py` ✅
- [ ] `apps/ai/src/document_processing/pipeline.py` (full pipeline)

### Test Files
- [ ] `apps/ai/tests/test_docling_parser.py`
- [ ] `apps/ai/tests/test_langextract_schema.py`
- [ ] `apps/ai/tests/test_elasticsearch_index.py`
- [ ] `apps/ai/tests/test_hybrid_search.py`
- [ ] `apps/ai/tests/test_integration_e2e.py`

### Documentation
- [ ] `docs/VECTORLESS_RAG_ARCHITECTURE.md` ✅
- [ ] `docs/VECTORLESS_RAG_CHECKLIST.md` ✅
- [ ] `docs/benchmarks/docling_performance.md`
- [ ] `docs/benchmarks/langextract_performance.md`
- [ ] `docs/benchmarks/elasticsearch_performance.md`
- [ ] `docs/runbooks/document_ingestion_failures.md`

### Infrastructure
- [ ] `docker-compose.yml` updated with ES
- [ ] `.env.example` updated with ES credentials
- [ ] `scripts/start_elasticsearch.sh`
- [ ] `scripts/stop_elasticsearch.sh`

### Agent Updates
- [ ] Finance Monitor agent updated
- [ ] Chief of Staff agent updated
- [ ] Tool registration for document queries

---

## Progress Tracking

| Phase | Status | Start Date | End Date | Notes |
|-------|--------|------------|----------|-------|
| Phase 1: Docling | ⬜ Not Started | - | - | - |
| Phase 2: LangExtract | ⬜ Not Started | - | - | - |
| Phase 3: Elasticsearch | ⬜ Not Started | - | - | - |
| Phase 4: Agent Integration | ⬜ Not Started | - | - | - |
| Phase 5: Production Hardening | ⬜ Not Started | - | - | - |
| Phase 6: Hybrid Search | ⬜ Not Started | - | - | Optional |

---

**Last Updated:** March 19, 2026  
**Next Review:** March 26, 2026
