"""
Full ingestion pipeline:
  Raw document (PDF/invoice/contract)
    → Granite-Docling (structure extraction)
    → LangExtract (metadata extraction)
    → ZincSearch (indexed for vectorless retrieval)
"""
import os
import json
from openai import OpenAI
from apps.ai.src.search.zincsearch_client import (
    ZincSearchClient, ZincDocument, INDICES
)

# Ollama client — Granite-Docling runs locally
ollama = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key="ollama",
)

zinc = ZincSearchClient()

# Schema for invoice extraction
INVOICE_SCHEMA = {
    "vendor_name":   "The company or service provider name",
    "amount":        "Total invoice amount as a number (no currency symbol)",
    "doc_date":      "Invoice or statement date in YYYY-MM-DD format",
    "category":      "One of: infrastructure, payroll, marketing, saas, misc",
    "anomaly_flag":  "true if amount seems unusually high, else false",
}


def parse_document_with_docling(raw_text: str,
                                 doc_hint: str = "invoice") -> str:
    """
    Use granite-docling to extract structured text from
    a raw document string (pre-OCR or PDF text dump).
    Returns structured text with section/table context preserved.
    """
    resp = ollama.chat.completions.create(
        model="ibm/granite-docling:latest",
        messages=[{
            "role": "system",
            "content": (
                "You are a document structure extractor. "
                f"Extract and structure this {doc_hint}. "
                "Preserve: tables (as key:value pairs), "
                "section headers, line items, totals, dates, vendor names. "
                "Return structured plain text. No markdown."
            )
        }, {
            "role": "user",
            "content": raw_text[:4000],   # granite-docling context limit
        }],
        temperature=0.0,
        max_tokens=1000,
    )
    return resp.choices[0].message.content.strip()


def extract_metadata_with_llm(structured_text: str,
                                schema: dict,
                                model: str = "qwen3:0.6b") -> dict:
    """
    LangExtract-style extraction: schema → structured metadata.
    Uses local Ollama model — no external API.
    """
    schema_prompt = "\n".join(
        f'  "{k}": {v}' for k, v in schema.items()
    )
    resp = ollama.chat.completions.create(
        model=model,
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
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {}


def ingest_document(tenant_id: str,
                    raw_text: str,
                    doc_type: str = "invoice",
                    doc_id: str | None = None) -> ZincDocument:
    """
    Full pipeline: raw text → Docling → LangExtract → ZincSearch.
    Returns the indexed ZincDocument.
    """
    # 1. Structure with Granite-Docling
    structured = parse_document_with_docling(raw_text, doc_type)

    # 2. Extract metadata with LangExtract pattern
    metadata = extract_metadata_with_llm(structured, INVOICE_SCHEMA)

    # 3. Build ZincDocument
    doc = ZincDocument(
        tenant_id=tenant_id,
        doc_type=doc_type,
        text=structured,
        vendor_name=metadata.get("vendor_name"),
        amount=float(metadata.get("amount") or 0),
        doc_date=metadata.get("doc_date"),
        category=metadata.get("category", "misc"),
        anomaly_flag=str(metadata.get("anomaly_flag", "false")).lower() == "true",
    )
    if doc_id:
        doc.doc_id = doc_id

    # 4. Index into ZincSearch
    index = INDICES.get(doc_type, "sarthi-invoices")
    zinc.index_document(index, doc)

    return doc
