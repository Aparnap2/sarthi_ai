"""
Tests for ZincSearch integration.

Tests:
- ZincSearch health
- Index creation
- Document indexing
- BM25 text search
- Metadata filter search
- Anomaly retrieval
- Full pipeline (Docling → LangExtract → ZincSearch)

Requires:
- ZincSearch running on localhost:4080
- Ollama running on localhost:11434
"""
import pytest
import time
import uuid
from apps.ai.src.search.zincsearch_client import (
    ZincSearchClient, ZincDocument, INDICES
)
from apps.ai.src.search.document_pipeline import ingest_document

TENANT = "test-zinc-tenant"
zinc = ZincSearchClient()


class TestZincSearchHealth:
    """Test ZincSearch connectivity."""

    def test_health(self):
        """ZincSearch should be healthy."""
        assert zinc.health() is True

    def test_list_indices_empty_initially(self):
        """Should return empty list or existing indices."""
        indices = zinc.list_indices()
        assert isinstance(indices, list)


class TestZincSearchIndexing:
    """Test ZincSearch indexing operations."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup test index, teardown after."""
        # Create test index
        zinc.create_index("sarthi-invoices")
        yield
        # Cleanup: delete test index (optional)
        # zinc.delete_index("sarthi-invoices")

    def test_create_index(self):
        """Should create index successfully."""
        r = zinc.create_index("sarthi-test-index")
        assert "error" not in str(r).lower() or "already" in str(r).lower()

    def test_index_and_retrieve_invoice(self):
        """Index a document and retrieve it."""
        doc = ZincDocument(
            tenant_id=TENANT,
            doc_type="invoice",
            text="AWS consolidated bill April 2026 infrastructure services",
            vendor_name="AWS",
            amount=42000.0,
            doc_date="2026-04-01",
            category="infrastructure",
            anomaly_flag=True,
        )
        result = zinc.index_document("sarthi-invoices", doc)
        assert result.get("id") == doc.doc_id

        # Wait for ZincSearch to index asynchronously
        time.sleep(1)

        # Retrieve by vendor
        results = zinc.search_by_vendor(
            "sarthi-invoices", TENANT, "AWS"
        )
        assert len(results) >= 1
        assert any(r.get("vendor_name") == "AWS" for r in results)

    def test_search_by_vendor_exact(self):
        """Search by exact vendor name."""
        doc = ZincDocument(
            tenant_id=TENANT, doc_type="invoice",
            text="Vercel Pro plan March 2026",
            vendor_name="Vercel", amount=12000.0,
            doc_date="2026-03-01", category="infrastructure",
        )
        zinc.index_document("sarthi-invoices", doc)
        time.sleep(1)

        results = zinc.search_by_vendor(
            "sarthi-invoices", TENANT, "Vercel"
        )
        assert len(results) >= 1
        assert any(r.get("vendor_name") == "Vercel" for r in results)

    def test_search_anomalies_returns_flagged_only(self):
        """Search should return only anomaly-flagged documents."""
        results = zinc.search_anomalies("sarthi-invoices", TENANT)
        assert all(r.get("anomaly_flag") is True for r in results)

    def test_bm25_text_search(self):
        """BM25 full-text search should work."""
        results = zinc.search_text(
            "sarthi-invoices", TENANT, "consolidated bill"
        )
        # AWS doc indexed in test_index_and_retrieve_invoice
        assert any(
            "AWS" in (r.get("vendor_name") or "")
            or "consolidated" in (r.get("text") or "")
            for r in results
        )

    def test_search_by_metadata(self):
        """Search by arbitrary metadata filters."""
        doc = ZincDocument(
            tenant_id=TENANT, doc_type="invoice",
            text="Stripe payment processing February 2026",
            vendor_name="Stripe", amount=8500.0,
            doc_date="2026-02-15", category="saas",
        )
        zinc.index_document("sarthi-invoices", doc)
        time.sleep(1)

        results = zinc.search_by_metadata(
            "sarthi-invoices", TENANT,
            filters={"category": "saas", "vendor_name": "Stripe"}
        )
        assert len(results) >= 1
        assert any(r.get("vendor_name") == "Stripe" for r in results)

    def test_bulk_index(self):
        """Bulk index multiple documents."""
        docs = [
            ZincDocument(
                tenant_id=TENANT, doc_type="invoice",
                text=f"Test invoice {i}",
                vendor_name=f"Vendor{i}", amount=10000.0 * i,
                doc_date=f"2026-0{i}-01", category="misc",
            )
            for i in range(1, 4)
        ]
        result = zinc.bulk_index("sarthi-invoices", docs)
        assert "items" in result or "errors" not in result

    def test_full_ingest_pipeline(self):
        """
        Full pipeline: raw text → Docling → LangExtract → ZincSearch.
        
        This tests the complete ingestion pipeline with real LLM calls.
        """
        raw = """
        INVOICE #INV-2026-089
        Vendor: AWS India Pvt Ltd
        Date: 2026-03-15
        Services: EC2 t3.medium (730hrs), S3 storage (2TB), CloudFront
        Subtotal: Rs. 38,500
        GST 18%: Rs. 6,930
        TOTAL: Rs. 45,430
        """
        doc = ingest_document(
            tenant_id=TENANT,
            raw_text=raw,
            doc_type="invoice",
        )
        assert doc.vendor_name is not None
        assert doc.amount > 0
        assert doc.category is not None
        print(
            f"\n  Extracted: vendor={doc.vendor_name} "
            f"amount=₹{doc.amount:,.0f} "
            f"category={doc.category} "
            f"anomaly={doc.anomaly_flag}"
        )
