"""
LangExtract Schemas for Sarthi Financial Documents.

Defines extraction schemas for:
- Invoices (vendor, amount, date, category)
- Bank Statements (transactions with debit/credit)
- Board Decks (quarterly metrics, commitments)

Uses schema-enforced metadata extraction with source span tracing
for audit-compliant document processing.

Example:
    >>> from langextract_schema import (
    ...     INVOICE_SCHEMA,
    ...     create_invoice_examples,
    ...     extract_from_document,
    ... )
    >>> 
    >>> text = "Invoice #INV-2026-001\\nFrom: Amazon Web Services\\nAmount: ₹42,000"
    >>> examples = create_invoice_examples()
    >>> result = extract_from_document(text, INVOICE_SCHEMA, examples)
    >>> 
    >>> for extraction in result.extractions:
    ...     print(f"{extraction.extraction_class}: {extraction.extraction_text}")
    ...     print(f"  Source: chars {extraction.char_interval.start_pos}-{extraction.char_interval.end_pos}")
"""
import langextract as lx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Definitions
# =============================================================================

INVOICE_SCHEMA: Dict[str, Any] = {
    "vendor_name": "string (exact company name as it appears on invoice)",
    "invoice_amount": "float (in INR, without currency symbol, e.g., 42000 not ₹42,000)",
    "invoice_date": "date (YYYY-MM-DD format)",
    "invoice_number": "string (invoice ID, e.g., INV-2026-001)",
    "category": "enum[infrastructure, payroll, marketing, office, misc]",
    "anomaly_flag": "boolean (true if amount > 2x average for this vendor)",
}
"""
Schema for invoice extraction.

Fields:
    vendor_name: Exact company name as it appears on invoice
    invoice_amount: Numeric amount in INR (no currency symbol)
    invoice_date: Date in YYYY-MM-DD format
    invoice_number: Invoice identifier
    category: Expense category from predefined enum
    anomaly_flag: Whether amount exceeds 2x vendor average

Example:
    >>> INVOICE_SCHEMA["vendor_name"]
    'string (exact company name as it appears on invoice)'
"""


BANK_STATEMENT_SCHEMA: Dict[str, Any] = {
    "transactions": [
        {
            "date": "date (YYYY-MM-DD)",
            "description": "string (transaction description from bank statement)",
            "debit": "float (amount debited, 0 if credit)",
            "credit": "float (amount credited, 0 if debit)",
            "balance": "float (running balance after transaction)",
            "category": "enum[revenue, infrastructure, payroll, marketing, office, misc]",
        }
    ],
}
"""
Schema for bank statement transaction extraction.

Fields:
    transactions: List of transaction objects
    transactions[].date: Transaction date in YYYY-MM-DD format
    transactions[].description: Bank transaction description
    transactions[].debit: Amount debited (0 for credits)
    transactions[].credit: Amount credited (0 for debits)
    transactions[].balance: Running balance
    transactions[].category: Transaction category from predefined enum

Example:
    >>> BANK_STATEMENT_SCHEMA["transactions"][0]["debit"]
    'float (amount debited, 0 if credit)'
"""


BOARD_DECK_SCHEMA: Dict[str, Any] = {
    "quarter": "string (e.g., Q1_2026, Q2_2026)",
    "revenue": "float (quarterly revenue in INR)",
    "burn_rate": "float (monthly burn rate in INR)",
    "runway_months": "float (runway in months based on current cash)",
    "key_metrics": [
        {
            "metric_name": "string (e.g., MRR, ARR, CAC, LTV)",
            "value": "float (metric value)",
            "change_from_previous": "float (percentage change, e.g., 15.5 for 15.5%)",
        }
    ],
    "commitments_made": [
        {
            "commitment": "string (description of commitment)",
            "owner": "string (person responsible)",
            "deadline": "date (YYYY-MM-DD)",
            "status": "enum[done, in_progress, at_risk, not_started]",
        }
    ],
}
"""
Schema for board deck extraction.

Fields:
    quarter: Quarter identifier (e.g., Q1_2026)
    revenue: Quarterly revenue in INR
    burn_rate: Monthly burn rate in INR
    runway_months: Runway in months
    key_metrics: List of key performance metrics
    key_metrics[].metric_name: Metric name (MRR, ARR, CAC, LTV, etc.)
    key_metrics[].value: Metric value
    key_metrics[].change_from_previous: Percentage change from previous period
    commitments_made: List of commitments made during quarter
    commitments[].commitment: Commitment description
    commitments[].owner: Person responsible
    commitments[].deadline: Deadline date
    commitments[].status: Status from predefined enum

Example:
    >>> BOARD_DECK_SCHEMA["quarter"]
    'string (e.g., Q1_2026, Q2_2026)'
"""


# =============================================================================
# Few-Shot Examples
# =============================================================================

def create_invoice_examples() -> List[lx.data.ExampleData]:
    """
    Create few-shot examples for invoice extraction.
    
    Returns:
        List of ExampleData objects with text and expected extractions
        
    Example:
        >>> examples = create_invoice_examples()
        >>> len(examples)
        3
        >>> examples[0].text
        'Invoice #INV-2026-001...'
    """
    return [
        lx.data.ExampleData(
            text=(
                "Invoice #INV-2026-001\n"
                "From: Amazon Web Services India Pvt Ltd\n"
                "Amount: ₹42,000\n"
                "Date: March 15, 2026\n"
                "Category: Infrastructure"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="vendor_name",
                    extraction_text="Amazon Web Services India Pvt Ltd",
                ),
                lx.data.Extraction(
                    extraction_class="invoice_amount",
                    extraction_text="42000",
                    attributes={"currency": "INR"},
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="2026-03-15",
                ),
                lx.data.Extraction(
                    extraction_class="category",
                    extraction_text="Infrastructure",
                ),
            ],
        ),
        lx.data.ExampleData(
            text=(
                "Invoice #INV-2026-042\n"
                "From: Microsoft Azure India\n"
                "Amount: ₹28,500\n"
                "Date: February 28, 2026\n"
                "Category: Infrastructure"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="vendor_name",
                    extraction_text="Microsoft Azure India",
                ),
                lx.data.Extraction(
                    extraction_class="invoice_amount",
                    extraction_text="28500",
                    attributes={"currency": "INR"},
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="2026-02-28",
                ),
                lx.data.Extraction(
                    extraction_class="category",
                    extraction_text="Infrastructure",
                ),
            ],
        ),
        lx.data.ExampleData(
            text=(
                "Invoice #INV-2026-108\n"
                "From: LinkedIn India Pvt Ltd\n"
                "Amount: ₹15,000\n"
                "Date: January 20, 2026\n"
                "Category: Marketing"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="vendor_name",
                    extraction_text="LinkedIn India Pvt Ltd",
                ),
                lx.data.Extraction(
                    extraction_class="invoice_amount",
                    extraction_text="15000",
                    attributes={"currency": "INR"},
                ),
                lx.data.Extraction(
                    extraction_class="invoice_date",
                    extraction_text="2026-01-20",
                ),
                lx.data.Extraction(
                    extraction_class="category",
                    extraction_text="Marketing",
                ),
            ],
        ),
    ]


def create_bank_statement_examples() -> List[lx.data.ExampleData]:
    """
    Create few-shot examples for bank statement extraction.
    
    Returns:
        List of ExampleData objects with text and expected extractions
        
    Example:
        >>> examples = create_bank_statement_examples()
        >>> len(examples)
        2
    """
    return [
        lx.data.ExampleData(
            text=(
                "Transaction Date: 2026-03-01\n"
                "Description: Razorpay Payment Settlement\n"
                "Debit: 0\n"
                "Credit: 125000\n"
                "Balance: 450000\n"
                "Category: Revenue\n\n"
                "Transaction Date: 2026-03-05\n"
                "Description: AWS India Debit\n"
                "Debit: 42000\n"
                "Credit: 0\n"
                "Balance: 408000\n"
                "Category: Infrastructure"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="transactions",
                    extraction_text=(
                        "2026-03-01, Razorpay Payment Settlement, Credit: 125000, Revenue"
                    ),
                    attributes={
                        "date": "2026-03-01",
                        "description": "Razorpay Payment Settlement",
                        "credit": "125000",
                        "category": "Revenue",
                    },
                ),
                lx.data.Extraction(
                    extraction_class="transactions",
                    extraction_text=(
                        "2026-03-05, AWS India Debit, Debit: 42000, Infrastructure"
                    ),
                    attributes={
                        "date": "2026-03-05",
                        "description": "AWS India Debit",
                        "debit": "42000",
                        "category": "Infrastructure",
                    },
                ),
            ],
        ),
    ]


def create_board_deck_examples() -> List[lx.data.ExampleData]:
    """
    Create few-shot examples for board deck extraction.
    
    Returns:
        List of ExampleData objects with text and expected extractions
        
    Example:
        >>> examples = create_board_deck_examples()
        >>> len(examples)
        1
    """
    return [
        lx.data.ExampleData(
            text=(
                "Quarter: Q1_2026\n"
                "Revenue: ₹4,50,000\n"
                "Burn Rate: ₹1,20,000/month\n"
                "Runway: 18 months\n\n"
                "Key Metrics:\n"
                "- MRR: ₹1,50,000 (↑25% from Q4_2025)\n"
                "- CAC: ₹8,500 (↓10% from Q4_2025)\n\n"
                "Commitments:\n"
                "- Launch enterprise tier by March 31, 2026 (Owner: Rajesh, Status: in_progress)\n"
                "- Close Series A by June 30, 2026 (Owner: Priya, Status: at_risk)"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="quarter",
                    extraction_text="Q1_2026",
                ),
                lx.data.Extraction(
                    extraction_class="revenue",
                    extraction_text="450000",
                ),
                lx.data.Extraction(
                    extraction_class="burn_rate",
                    extraction_text="120000",
                ),
                lx.data.Extraction(
                    extraction_class="runway_months",
                    extraction_text="18",
                ),
                lx.data.Extraction(
                    extraction_class="commitments_made",
                    extraction_text=(
                        "Launch enterprise tier by March 31, 2026 (Owner: Rajesh, Status: in_progress)"
                    ),
                    attributes={
                        "commitment": "Launch enterprise tier",
                        "deadline": "2026-03-31",
                        "owner": "Rajesh",
                        "status": "in_progress",
                    },
                ),
            ],
        ),
    ]


# =============================================================================
# Extraction Functions
# =============================================================================

@dataclass
class ExtractionConfig:
    """Configuration for LangExtract extraction."""

    model_id: str = "qwen3:0.6b"
    """Ollama model ID for extraction."""
    
    base_url: str = "http://localhost:11434"
    """Ollama base URL."""
    
    max_char_buffer: int = 500
    """Maximum characters per chunk."""
    
    batch_length: int = 1000
    """Batch size for API calls."""
    
    max_workers: int = 4
    """Number of parallel workers."""
    
    timeout_seconds: int = 300
    """Timeout for extraction requests."""


def extract_from_document(
    text: str,
    schema: Dict[str, Any],
    examples: List[lx.data.ExampleData],
    config: Optional[ExtractionConfig] = None,
) -> lx.ExtractionResult:
    """
    Extract structured data from document text using LangExtract.
    
    Uses schema-enforced extraction with few-shot examples and
    character-level source span tracing for audit compliance.
    
    Args:
        text: Document text (from Docling output)
        schema: Extraction schema (e.g., INVOICE_SCHEMA)
        examples: Few-shot examples for guidance
        config: Extraction configuration (optional, uses defaults if None)
        
    Returns:
        ExtractionResult with extractions and source spans
        
    Raises:
        ValueError: If text is empty or schema is invalid
        
    Example:
        >>> from langextract_schema import (
        ...     INVOICE_SCHEMA,
        ...     create_invoice_examples,
        ...     extract_from_document,
        ... )
        >>> 
        >>> text = "Invoice #INV-2026-001\\nFrom: Amazon Web Services\\nAmount: ₹42,000"
        >>> examples = create_invoice_examples()
        >>> result = extract_from_document(text, INVOICE_SCHEMA, examples)
        >>> 
        >>> for extraction in result.extractions:
        ...     print(f"{extraction.extraction_class}: {extraction.extraction_text}")
        ...     print(f"  Source: chars {extraction.char_interval.start_pos}-{extraction.char_interval.end_pos}")
    """
    if config is None:
        config = ExtractionConfig()
    
    if not text.strip():
        raise ValueError("Input text cannot be empty")
    
    prompt = f"""
    Extract structured data from the document text according to the schema.
    
    Schema: {schema}
    
    Instructions:
    1. Use exact text from input for extraction_text
    2. Trace each extraction to its source character span
    3. Convert amounts to numeric format (remove currency symbols, commas)
    4. Convert dates to YYYY-MM-DD format
    5. Use enum values exactly as specified in schema
    
    Document text:
    {text}
    """
    
    logger.info(
        "Starting extraction with model=%s, max_workers=%d, max_char_buffer=%d",
        config.model_id,
        config.max_workers,
        config.max_char_buffer,
    )
    
    try:
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples,
            model_id=config.model_id,
            max_char_buffer=config.max_char_buffer,
            batch_length=config.batch_length,
            max_workers=config.max_workers,
            language_model_params={
                "ollama": True,
                "base_url": config.base_url,
            },
        )
        
        logger.info(
            "Extraction complete: %d extractions found",
            len(result.extractions) if hasattr(result, "extractions") else 0,
        )
        
        return result
        
    except Exception as err:
        logger.error("Extraction failed: %s", err)
        raise


def extract_invoice_metadata(
    text: str,
    config: Optional[ExtractionConfig] = None,
) -> lx.ExtractionResult:
    """
    Extract metadata from invoice text.
    
    Convenience wrapper around extract_from_document for invoices.
    
    Args:
        text: Invoice text (from Docling output)
        config: Extraction configuration
        
    Returns:
        ExtractionResult with invoice metadata extractions
        
    Example:
        >>> text = "Invoice #INV-2026-001\\nFrom: Amazon Web Services\\nAmount: ₹42,000"
        >>> result = extract_invoice_metadata(text)
        >>> print(f"Vendor: {result.extractions[0].extraction_text}")
    """
    examples = create_invoice_examples()
    return extract_from_document(text, INVOICE_SCHEMA, examples, config)


def extract_bank_transactions(
    text: str,
    config: Optional[ExtractionConfig] = None,
) -> lx.ExtractionResult:
    """
    Extract transactions from bank statement text.
    
    Convenience wrapper around extract_from_document for bank statements.
    
    Args:
        text: Bank statement text (from Docling output)
        config: Extraction configuration
        
    Returns:
        ExtractionResult with transaction extractions
        
    Example:
        >>> text = "2026-03-01, Razorpay Settlement, Credit: 125000"
        >>> result = extract_bank_transactions(text)
    """
    examples = create_bank_statement_examples()
    return extract_from_document(text, BANK_STATEMENT_SCHEMA, examples, config)


def extract_board_deck_metrics(
    text: str,
    config: Optional[ExtractionConfig] = None,
) -> lx.ExtractionResult:
    """
    Extract metrics and commitments from board deck text.
    
    Convenience wrapper around extract_from_document for board decks.
    
    Args:
        text: Board deck text (from Docling output)
        config: Extraction configuration
        
    Returns:
        ExtractionResult with metrics and commitments
        
    Example:
        >>> text = "Q1_2026, Revenue: ₹4,50,000, Burn: ₹1,20,000"
        >>> result = extract_board_deck_metrics(text)
    """
    examples = create_board_deck_examples()
    return extract_from_document(text, BOARD_DECK_SCHEMA, examples, config)


# =============================================================================
# Utility Functions
# =============================================================================

def format_extraction_result(result: lx.ExtractionResult) -> Dict[str, Any]:
    """
    Format extraction result as dictionary for indexing.
    
    Args:
        result: ExtractionResult from LangExtract
        
    Returns:
        Dict with extractions grouped by class and source spans
        
    Example:
        >>> result = extract_invoice_metadata(text)
        >>> formatted = format_extraction_result(result)
        >>> print(formatted["vendor_name"])
        'Amazon Web Services India Pvt Ltd'
    """
    formatted: Dict[str, Any] = {
        "extractions": [],
        "by_class": {},
    }
    
    if not hasattr(result, "extractions"):
        return formatted
    
    for extraction in result.extractions:
        extraction_data = {
            "class": extraction.extraction_class,
            "text": extraction.extraction_text,
            "start_pos": extraction.char_interval.start_pos if hasattr(extraction, "char_interval") else None,
            "end_pos": extraction.char_interval.end_pos if hasattr(extraction, "char_interval") else None,
            "attributes": extraction.attributes if hasattr(extraction, "attributes") else None,
        }
        formatted["extractions"].append(extraction_data)
        
        # Group by class
        if extraction.extraction_class not in formatted["by_class"]:
            formatted["by_class"][extraction.extraction_class] = []
        formatted["by_class"][extraction.extraction_class].append(extraction_data)
    
    return formatted


def validate_extraction(
    result: lx.ExtractionResult,
    required_classes: List[str],
) -> bool:
    """
    Validate that extraction contains all required classes.
    
    Args:
        result: ExtractionResult from LangExtract
        required_classes: List of required extraction classes
        
    Returns:
        True if all required classes are present
        
    Example:
        >>> result = extract_invoice_metadata(text)
        >>> is_valid = validate_extraction(result, ["vendor_name", "invoice_amount", "invoice_date"])
        >>> print(f"Valid: {is_valid}")
    """
    if not hasattr(result, "extractions"):
        return False
    
    extracted_classes = {e.extraction_class for e in result.extractions}
    missing = set(required_classes) - extracted_classes
    
    if missing:
        logger.warning("Missing required extraction classes: %s", missing)
        return False
    
    return True
