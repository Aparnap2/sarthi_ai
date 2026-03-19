# Sarthi Vectorless RAG Architecture
## ZincSearch + Granite-Docling + LangExtract Pipeline

**Date:** March 19, 2026  
**Stack:** ZincSearch (not Elasticsearch) + Ollama (Granite-Docling, qwen3:0.6b)

---

## Executive Summary

**Vectorless RAG** = Retrieval without embeddings. Instead of converting text to vectors and running similarity search, we use:
- **BM25** (lexical matching) for full-text search
- **Metadata filters** (vendor, amount, date, category) for exact queries
- **Structured document parsing** (Granite-Docling) for table/section preservation

**Why ZincSearch (not Elasticsearch):**
| | ZincSearch | Elasticsearch |
|---|---|---|
| RAM footprint | **< 100MB** | 1–4GB minimum |
| Setup | Single binary, zero config | JVM tuning, cluster config |
| Built-in UI | ✅ `localhost:4080` | Kibana (separate) |
| Already in images | ✅ `zinclabs/zincsearch:latest` | ❌ |
| Redpanda integration | ✅ proven pattern | ✅ |

**When to use Vectorless (ZincSearch) vs Vectors (Qdrant):**
| Query Type | Best Store |
|------------|------------|
| "AWS invoice from March 2026" | ZincSearch (exact date filter) |
| "All invoices over ₹50,000" | ZincSearch (range query) |
| Table data in PDFs | ZincSearch (Docling structure) |
| "Why did burn spike in Q1?" | Hybrid (ZincSearch + Qdrant) |
| "Founder notes on churn pattern" | Qdrant (conversational) |

---

## The Three-Layer Pipeline

```
DOCUMENT INGESTION
  Raw document (PDF invoice, bank statement, contract)
        ↓
  Granite-Docling-258M (via Ollama: ibm/granite-docling:latest)
        ↓
  Structured text: sections, tables, line items preserved
        ↓
  LangExtract pattern (qwen3:0.6b with schema enforcement)
        ↓
  Metadata: {vendor_name, amount, doc_date, category, anomaly_flag}
        ↓
  ZincSearch index (BM25 + metadata filters)

QUERY TIME
  Finance Monitor: "AWS bills over ₹30,000 this quarter"
        ↓
  ZincSearch filter: vendor=AWS AND amount>30000 AND doc_date>2026-01-01
  + BM25 rank on text content
        ↓
  Top-K documents → LLM context → answer with citations
```

---

## Component Details

### 1. ZincSearch (`zinclabs/zincsearch:latest`)

**Start command:**
```bash
docker run -d \
  --name sarthi-zincsearch \
  -p 4080:4080 \
  -e ZINC_FIRST_ADMIN_USER=admin \
  -e ZINC_FIRST_ADMIN_PASSWORD=Sarthi#2026 \
  -e ZINC_DATA_PATH=/data \
  zinclabs/zincsearch:latest
```

**Health check:**
```bash
curl -sf http://localhost:4080/healthz
# → {"status":"ok"}
```

**Index mapping (schemaless, but we define for clarity):**
```json
{
  "name": "sarthi-invoices",
  "storage_type": "disk",
  "mappings": {
    "properties": {
      "tenant_id":   {"type": "keyword"},
      "doc_type":    {"type": "keyword"},
      "vendor_name": {"type": "keyword"},
      "amount":      {"type": "numeric"},
      "doc_date":    {"type": "date", "format": "2006-01-02"},
      "category":    {"type": "keyword"},
      "anomaly_flag":{"type": "bool"},
      "text":        {"type": "text"}
    }
  }
}
```

**Query examples:**
```bash
# BM25 text search
curl -u admin:Sarthi#2026 -X POST http://localhost:4080/api/sarthi-invoices/_search \
  -H 'Content-Type: application/json' \
  -d '{"search_type":"match","query":{"term":"AWS consolidated bill","field":"text"}}'

# Metadata filter (vendor + amount threshold)
curl -u admin:Sarthi#2026 -X POST http://localhost:4080/api/sarthi-invoices/_search \
  -H 'Content-Type: application/json' \
  -d '{"search_type":"querystring","query":{"term":"+tenant_id:tenant-001 +vendor_name:AWS +anomaly_flag:true"}}'
```

---

### 2. Granite-Docling (`ibm/granite-docling:latest` via Ollama)

**Already available in Ollama.** No pull needed.

**Usage:**
```python
from openai import OpenAI

ollama = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

resp = ollama.chat.completions.create(
    model="ibm/granite-docling:latest",
    messages=[{
        "role": "system",
        "content": (
            "You are a document structure extractor. "
            "Extract and structure this invoice. "
            "Preserve: tables (as key:value pairs), "
            "section headers, line items, totals, dates, vendor names. "
            "Return structured plain text. No markdown."
        )
    }, {
        "role": "user",
        "content": raw_pdf_text[:4000],  # Context limit
    }],
    temperature=0.0,
    max_tokens=1000,
)

structured_text = resp.choices[0].message.content.strip()
```

**Output format:**
```
INVOICE #INV-2026-089
Vendor: AWS India Pvt Ltd
Date: 2026-03-15
Services:
  - EC2 t3.medium (730hrs): Rs. 28,000
  - S3 storage (2TB): Rs. 8,500
  - CloudFront: Rs. 2,000
Subtotal: Rs. 38,500
GST 18%: Rs. 6,930
TOTAL: Rs. 45,430
```

---

### 3. LangExtract Pattern (qwen3:0.6b)

**Schema definition:**
```python
INVOICE_SCHEMA = {
    "vendor_name":   "The company or service provider name",
    "amount":        "Total invoice amount as a number (no currency symbol)",
    "doc_date":      "Invoice date in YYYY-MM-DD format",
    "category":      "One of: infrastructure, payroll, marketing, saas, misc",
    "anomaly_flag":  "true if amount seems unusually high, else false",
}
```

**Extraction function:**
```python
def extract_metadata_with_llm(structured_text: str, schema: dict) -> dict:
    schema_prompt = "\n".join(f'  "{k}": {v}' for k, v in schema.items())
    
    resp = ollama.chat.completions.create(
        model="qwen3:0.6b",
        messages=[{
            "role": "system",
            "content": (
                "Extract the following fields from the document text. "
                "Return ONLY valid JSON with these exact keys:\n"
                f"{schema_prompt}\n"
                "If a field is not found, use null. "
                "amount must be a number, not a string."
            )
        }, {
            "role": "user",
            "content": structured_text,
        }],
        temperature=0.0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    
    return json.loads(resp.choices[0].message.content)
```

**Output:**
```json
{
  "vendor_name": "AWS India Pvt Ltd",
  "amount": 45430,
  "doc_date": "2026-03-15",
  "category": "infrastructure",
  "anomaly_flag": true
}
```

---

## Integration with Existing Agents

### Finance Monitor Upgrade

**Current:** Reads structured events from Razorpay/bank webhooks.

**New:** Can also ingest raw PDF invoices.

```python
# In apps/ai/src/agents/finance_monitor.py

def _query_past_invoices(self, tenant_id: str,
                          vendor: str,
                          min_amount: float = 0) -> list[dict]:
    """Query ZincSearch for past invoices from this vendor."""
    from apps.ai.src.search.zincsearch_client import ZincSearchClient
    zinc = ZincSearchClient()
    return zinc.search_by_vendor(
        index="sarthi-invoices",
        tenant_id=tenant_id,
        vendor=vendor,
        min_amount=min_amount,
    )

def _explain_anomaly(self, vendor: str, amount: float,
                      avg: float, multiple: float,
                      desc: str, tenant_id: str) -> str:
    # Pull past invoices from ZincSearch (vectorless — exact filter)
    past_invoices = self._query_past_invoices(
        tenant_id, vendor, min_amount=avg * 1.5
    )

    if past_invoices:
        last = past_invoices[-1]
        memory_context = (
            f"Past high bill: ₹{last.get('amount'):,.0f} "
            f"on {last.get('doc_date', 'unknown date')}. "
            f"Category: {last.get('category', 'unknown')}."
        )
    else:
        memory_context = "First time seeing a high bill from this vendor."

    # LLM generates plain-English headline using real doc history
    client = get_llm_client()
    resp = client.chat.completions.create(
        model=get_chat_model(),
        messages=[{
            "role": "system",
            "content": (
                "Write a 15-word max financial alert for a founder. "
                "Reference past history if provided. "
                "Never fabricate numbers."
            )
        }, {
            "role": "user",
            "content": (
                f"Vendor: {vendor} | Bill: ₹{amount:,.0f} "
                f"({multiple}× usual)\n{memory_context}"
            )
        }],
        temperature=0.1,
        max_tokens=50,
    )
    return resp.choices[0].message.content.strip()
```

---

### Chief of Staff Upgrade

**Current:** Reads from `agent_outputs` table.

**New:** Can ingest board decks, investor emails, financial statements.

```python
# Query example for Chief of Staff
def query_board_decks(tenant_id: str, quarter: str) -> list[dict]:
    zinc = ZincSearchClient()
    return zinc.search_by_metadata(
        index="sarthi-briefings",
        tenant_id=tenant_id,
        filters={"doc_type": "board_deck", "quarter": quarter},
    )
```

---

## Implementation Phases

### Phase 1: ZincSearch Setup ✅
- [x] Docker container started
- [x] Health check verified
- [x] Index mappings defined

### Phase 2: Python Client
- [ ] Create `apps/ai/src/search/zincsearch_client.py`
- [ ] Implement: `health()`, `create_index()`, `index_document()`, `search_text()`, `search_by_vendor()`
- [ ] Write unit tests

### Phase 3: Document Pipeline
- [ ] Create `apps/ai/src/search/document_pipeline.py`
- [ ] Integrate Granite-Docling (Ollama)
- [ ] Integrate LangExtract pattern (qwen3:0.6b)
- [ ] Write end-to-end tests

### Phase 4: Agent Integration
- [ ] Update Finance Monitor with `_query_past_invoices()`
- [ ] Update Chief of Staff with document query functions
- [ ] Write integration tests (PDF → agent answer)

### Phase 5: Production Hardening
- [ ] Add error handling (corrupt PDFs, extraction failures)
- [ ] Add retry logic
- [ ] Add monitoring (extraction latency, query latency)
- [ ] Write runbook

---

## Code Examples

### Full Pipeline: PDF → ZincSearch Index

```python
from apps/ai/src/search/document_pipeline import ingest_document

doc = ingest_document(
    tenant_id="tenant-001",
    raw_text=pdf_text,
    doc_type="invoice",
)

print(f"Indexed: vendor={doc.vendor_name}, amount=₹{doc.amount:,.0f}")
```

### Query Function for Finance Monitor

```python
def query_aws_bills_over_threshold(tenant_id: str, min_amount: float) -> list[dict]:
    zinc = ZincSearchClient()
    return zinc.search_by_vendor(
        index="sarthi-invoices",
        tenant_id=tenant_id,
        vendor="AWS",
        min_amount=min_amount,
    )

# Usage
bills = query_aws_bills_over_threshold("tenant-001", 30000)
for bill in bills:
    print(f"₹{bill['amount']:,.0f} on {bill['doc_date']}")
```

---

## Updated Storage Layer

```
STORAGE LAYER — FINAL:

  PostgreSQL   :5499  — structured state
                   (agent_outputs, hitl_actions,
                    transactions, founders, etc.)

  Qdrant       :6399  — episodic memory
                   (conversational, behavioral,
                    narrative — semantic search)

  ZincSearch   :4080  — document retrieval
                   (invoices, contracts, HR docs,
                    financial statements — BM25 exact)

  Ollama       :11434 — LLM inference
                   qwen3:0.6b       → agent reasoning
                   nomic-embed      → Qdrant embeddings
                   granite-docling  → document parsing

RULE:
  Exact query (vendor, amount, date, ID) → ZincSearch
  Conceptual query (patterns, context)   → Qdrant
  Structured ops data                    → PostgreSQL
```

---

## Next Steps

1. **Create ZincSearch Python client** (`apps/ai/src/search/zincsearch_client.py`)
2. **Create document pipeline** (`apps/ai/src/search/document_pipeline.py`)
3. **Write integration tests** (`apps/ai/tests/test_zincsearch.py`)
4. **Update Finance Monitor agent** with `_query_past_invoices()` method
5. **Add to test script** (`scripts/test_sarthi_local.sh`)

---

**Document Version:** 1.0  
**Last Updated:** March 19, 2026  
**Status:** Ready for Phase 2 implementation
