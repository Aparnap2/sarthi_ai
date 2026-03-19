"""
ZincSearch client for Sarthi vectorless document retrieval.

Wraps Granite-Docling output + LangExtract metadata → index + query.
Uses ZincSearch (not Elasticsearch) for BM25 + metadata filter search.

Environment variables:
  ZINC_URL: ZincSearch base URL (default: http://localhost:4080)
  ZINC_USER: Admin username (default: admin)
  ZINC_PASS: Admin password (default: Sarthi#2026)
"""
import os
import json
import uuid
import requests
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Configuration ───────────────────────────────────────────────────
ZINC_URL = os.getenv("ZINC_URL", "http://localhost:4080")
ZINC_USER = os.getenv("ZINC_USER", "admin")
ZINC_PASS = os.getenv("ZINC_PASS", "Sarthi#2026")
AUTH = (ZINC_USER, ZINC_PASS)

# Index names for different document types
INDICES = {
    "invoices": "sarthi-invoices",      # Finance Monitor
    "deals": "sarthi-deals",            # Revenue Tracker
    "hr_docs": "sarthi-hr-docs",        # People Coordinator
    "briefings": "sarthi-briefings",    # Chief of Staff
}


@dataclass
class ZincDocument:
    """
    Document structure for ZincSearch indexing.
    
    Attributes:
        tenant_id: Tenant identifier for multi-tenant isolation
        doc_type: Document type (invoice | deal | hr_doc | briefing)
        text: Structured text from Granite-Docling
        metadata: Additional metadata from LangExtract
        vendor_name: Vendor/company name (for invoices)
        amount: Document amount (for invoices/deals)
        doc_date: Document date in YYYY-MM-DD format
        category: Category (infrastructure | payroll | marketing | saas | misc)
        anomaly_flag: True if amount seems unusually high
        doc_id: Unique document ID (auto-generated if not provided)
    """
    tenant_id: str
    doc_type: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    doc_date: Optional[str] = None
    category: Optional[str] = None
    anomaly_flag: bool = False
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ZincSearchClient:
    """
    ZincSearch client for Sarthi document retrieval.
    
    Provides:
    - Health check
    - Index creation
    - Single document indexing
    - Bulk indexing
    - BM25 text search
    - Metadata filter search
    - Anomaly document retrieval
    """

    def health(self) -> bool:
        """
        Check ZincSearch health.
        
        Returns:
            True if ZincSearch is healthy and reachable
        """
        try:
            r = requests.get(f"{ZINC_URL}/healthz", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def create_index(self, index_name: str) -> Dict[str, Any]:
        """
        Create ZincSearch index.
        
        ZincSearch is schemaless, but we pre-register indices with mappings
        for clarity and to define field types for filtering.
        
        Args:
            index_name: Index name (e.g., "sarthi-invoices")
            
        Returns:
            ZincSearch response dict
        """
        r = requests.post(
            f"{ZINC_URL}/api/index",
            auth=AUTH,
            json={
                "name": index_name,
                "storage_type": "disk",
                "mappings": {
                    "properties": {
                        "tenant_id": {"type": "keyword"},
                        "doc_type": {"type": "keyword"},
                        "vendor_name": {"type": "keyword"},
                        "amount": {"type": "numeric"},
                        "doc_date": {"type": "date", "format": "2006-01-02"},
                        "category": {"type": "keyword"},
                        "anomaly_flag": {"type": "bool"},
                        "text": {"type": "text"},
                    }
                },
            },
        )
        return r.json()

    def index_document(self, index: str, doc: ZincDocument) -> Dict[str, Any]:
        """
        Index a single document.
        
        Args:
            index: Index name (e.g., "sarthi-invoices")
            doc: ZincDocument to index
            
        Returns:
            ZincSearch response dict with document ID
        """
        r = requests.post(
            f"{ZINC_URL}/api/{index}/_doc/{doc.doc_id}",
            auth=AUTH,
            json={
                "tenant_id": doc.tenant_id,
                "doc_type": doc.doc_type,
                "text": doc.text,
                "vendor_name": doc.vendor_name,
                "amount": doc.amount,
                "doc_date": doc.doc_date,
                "category": doc.category,
                "anomaly_flag": doc.anomaly_flag,
                **doc.metadata,
            },
        )
        return r.json()

    def bulk_index(self, index: str, docs: List[ZincDocument]) -> Dict[str, Any]:
        """
        Bulk index multiple documents.
        
        ZincSearch uses NDJSON format for bulk indexing.
        
        Args:
            index: Index name
            docs: List of ZincDocument objects
            
        Returns:
            ZincSearch bulk response dict
        """
        lines = []
        for doc in docs:
            lines.append(
                json.dumps({
                    "index": {"_index": index, "_id": doc.doc_id}
                })
            )
            lines.append(
                json.dumps({
                    "tenant_id": doc.tenant_id,
                    "doc_type": doc.doc_type,
                    "text": doc.text,
                    "vendor_name": doc.vendor_name,
                    "amount": doc.amount,
                    "doc_date": doc.doc_date,
                    "category": doc.category,
                    "anomaly_flag": doc.anomaly_flag,
                    **doc.metadata,
                })
            )
        
        r = requests.post(
            f"{ZINC_URL}/api/_bulk",
            auth=AUTH,
            data="\n".join(lines),
            headers={"Content-Type": "application/x-ndjson"},
        )
        return r.json()

    def search_text(
        self,
        index: str,
        tenant_id: str,
        term: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Pure BM25 full-text search.
        
        Args:
            index: Index name
            tenant_id: Tenant identifier for filtering
            term: Search term
            max_results: Maximum results to return
            
        Returns:
            List of matching document sources
        """
        r = requests.post(
            f"{ZINC_URL}/api/{index}/_search",
            auth=AUTH,
            json={
                "search_type": "match",
                "query": {"term": term, "field": "text"},
                "max_results": max_results,
                "_source": [],
            },
        )
        hits = r.json().get("hits", {}).get("hits", [])
        return [
            h["_source"]
            for h in hits
            if h["_source"].get("tenant_id") == tenant_id
        ]

    def search_by_vendor(
        self,
        index: str,
        tenant_id: str,
        vendor: str,
        min_amount: float = 0,
    ) -> List[Dict[str, Any]]:
        """
        Metadata filter — exact vendor + amount threshold.
        
        Args:
            index: Index name
            tenant_id: Tenant identifier
            vendor: Vendor name (exact match)
            min_amount: Minimum amount threshold
            
        Returns:
            List of matching document sources
        """
        r = requests.post(
            f"{ZINC_URL}/api/{index}/_search",
            auth=AUTH,
            json={
                "search_type": "querystring",
                "query": {
                    "term": f"+tenant_id:{tenant_id} +vendor_name:{vendor}"
                },
                "max_results": 50,
            },
        )
        hits = r.json().get("hits", {}).get("hits", [])
        return [
            h["_source"]
            for h in hits
            if float(h["_source"].get("amount") or 0) >= min_amount
        ]

    def search_anomalies(
        self,
        index: str,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Return all documents flagged as anomalies.
        
        Args:
            index: Index name
            tenant_id: Tenant identifier
            
        Returns:
            List of anomaly document sources
        """
        r = requests.post(
            f"{ZINC_URL}/api/{index}/_search",
            auth=AUTH,
            json={
                "search_type": "querystring",
                "query": {
                    "term": f"+tenant_id:{tenant_id} +anomaly_flag:true"
                },
                "max_results": 100,
            },
        )
        hits = r.json().get("hits", {}).get("hits", [])
        return [h["_source"] for h in hits]

    def search_by_metadata(
        self,
        index: str,
        tenant_id: str,
        filters: Dict[str, Any],
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search by arbitrary metadata filters.
        
        Args:
            index: Index name
            tenant_id: Tenant identifier
            filters: Dict of field=value pairs for filtering
            max_results: Maximum results to return
            
        Returns:
            List of matching document sources
        """
        filter_parts = [f"+tenant_id:{tenant_id}"]
        for key, value in filters.items():
            filter_parts.append(f"+{key}:{value}")
        
        query_term = " ".join(filter_parts)
        
        r = requests.post(
            f"{ZINC_URL}/api/{index}/_search",
            auth=AUTH,
            json={
                "search_type": "querystring",
                "query": {"term": query_term},
                "max_results": max_results,
            },
        )
        hits = r.json().get("hits", {}).get("hits", [])
        return [h["_source"] for h in hits]

    def delete_index(self, index_name: str) -> Dict[str, Any]:
        """
        Delete an index (for testing/cleanup).
        
        Args:
            index_name: Index name to delete
            
        Returns:
            ZincSearch response dict
        """
        r = requests.delete(
            f"{ZINC_URL}/api/index/{index_name}",
            auth=AUTH,
        )
        return r.json()

    def list_indices(self) -> List[str]:
        """
        List all indices.
        
        Returns:
            List of index names
        """
        r = requests.get(
            f"{ZINC_URL}/api/index",
            auth=AUTH,
        )
        data = r.json()
        return [idx["name"] for idx in data.get("list", [])]
