"""
SOP: Bank Statement Ingest — HDFC/ICICI/SBI/Axis bank statement parser.

Triggered when founder uploads bank statement via Telegram.
Categorizes transactions, updates CFO forecast, checks runway.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
from src.sops.base import BaseSOP, SOPResult
from src.sops.registry import register


# Runway alert threshold (days)
RUNWAY_ALERT_THRESHOLD_DAYS = 90

# Category keywords for rule-based classification
CATEGORY_KEYWORDS = {
    "Revenue": ["payment from", "received from", "upi payment", "neft credit", "rtgs credit", "imps credit"],
    "Infrastructure": ["aws", "azure", "gcp", "google cloud", "digitalocean", "heroku", "vercel", "cloudflare"],
    "Payroll": ["salary", "payroll", "pf", "esic", "tds", "professional tax"],
    "Vendor": ["vendor", "supplier", "invoice", "purchase order"],
    "Travel": ["uber", "ola", "flight", "hotel", "irctc", "makemytrip", "goibibo", "booking.com"],
    "Food": ["swiggy", "zomato", "restaurant", "food", "cafe", "starbucks"],
    "Transfer": ["transfer", "imps", "upi", "neft", "rtgs"],
    "Bank Charges": ["bank charges", "gst", "penalty", "fine", "interest", "service tax"],
    "Software": ["github", "gitlab", "jira", "confluence", "slack", "notion", "figma", "adobe"],
    "Office": ["rent", "electricity", "water", "internet", "phone", "office supplies"],
}


class BankStatementIngestSOP(BaseSOP):
    """
    SOP for ingesting bank statements.

    Triggers:
    - Telegram PDF/CSV upload (bank statement)
    - Bank API sync (future)

    Behavior:
    - Extracts transactions from CSV/PDF
    - Deduplicates against existing transactions
    - Categorizes each transaction (LLM + rules)
    - Writes to PostgreSQL
    - Updates CFO forecast
    - Checks runway (< 90 days = fire alert)
    - Logs to Qdrant memory
    """
    sop_name = "SOP_BANK_STATEMENT_INGEST"

    async def execute(self, payload_ref: str, founder_id: str) -> SOPResult:
        """
        Execute SOP_BANK_STATEMENT_INGEST.

        Args:
            payload_ref: Reference to raw_events table
            founder_id: Founder who owns this event

        Returns:
            SOPResult with execution outcome
        """
        # 1. Fetch payload from PostgreSQL
        raw = self.fetch_payload(payload_ref)
        
        # 2. Extract transactions based on file type
        file_type = raw.get("file_type", "csv")
        transactions = self._extract_transactions(raw)
        
        # 3. Process each transaction
        ingested = 0
        skipped = 0
        flagged = []
        
        for txn in transactions:
            # Deduplication check
            if self._is_duplicate(founder_id, txn):
                skipped += 1
                continue
            
            # Categorization
            category, confidence = self._categorize_transaction(txn)
            
            # Flag low-confidence for review
            needs_review = confidence < 0.7
            if needs_review:
                flagged.append(txn)
            
            # Write to PostgreSQL
            self._write_transaction(
                founder_id=founder_id,
                txn=txn,
                category=category,
                confidence=confidence,
                needs_review=needs_review,
                raw_event_id=self._extract_raw_event_id(payload_ref),
            )
            
            # Upsert to Qdrant for semantic search
            await self._upsert_qdrant(founder_id, txn, category)
            
            ingested += 1
        
        # 4. Update CFO state + get runway
        runway_days = await self._update_cfo_state(founder_id)
        
        # 5. Determine if we should fire alert
        fire_alert = runway_days < RUNWAY_ALERT_THRESHOLD_DAYS
        
        # 6. Calculate burn rate
        burn = self._calculate_burn(transactions)
        
        # 7. Log to memory
        bank_name = raw.get("bank_name", "Unknown")
        self._log_to_memory(
            founder_id=founder_id,
            content=f"{bank_name} statement processed: ₹{self._total_credit(transactions):,.0f} in, ₹{self._total_debit(transactions):,.0f} out, {ingested} transactions",
            memory_type="bank_statement",
            source="telegram",
        )
        
        # 8. Compose headline (jargon-free)
        headline = ""
        do_this = ""
        
        if fire_alert:
            months = round(runway_days / 30, 1)
            headline = f"Runway dropped to {runway_days} days — less than {months} months. Burn jumped."
            do_this = "Review the breakdown."
        else:
            months = round(runway_days / 30, 1)
            headline = f"Got your {bank_name} statement. Runway: {months} months."
            if flagged:
                do_this = f"{len(flagged)} transactions need a category — tap to review."
        
        return SOPResult(
            sop_name=self.sop_name,
            founder_id=founder_id,
            success=True,
            fire_alert=fire_alert,
            hitl_risk="high" if fire_alert else "low",
            headline=headline,
            do_this=do_this,
            is_good_news=not fire_alert,
            output={
                "transactions_ingested": ingested,
                "transactions_skipped": skipped,
                "transactions_flagged": len(flagged),
                "runway_days": runway_days,
                "burn_this_month": burn,
                "fire_alert": fire_alert,
            },
        )

    def _extract_transactions(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract transactions from raw payload.

        Args:
            raw: Raw payload from fetch_payload()

        Returns:
            List of transaction dicts
        """
        # If transactions already extracted (by parser), return them
        if "transactions" in raw:
            return raw["transactions"]
        
        # Otherwise, return empty list (parser should have run first)
        return []

    def _is_duplicate(self, founder_id: str, txn: Dict[str, Any]) -> bool:
        """
        Check if transaction already exists.

        Args:
            founder_id: Founder ID
            txn: Transaction dict

        Returns:
            True if duplicate, False otherwise
        """
        from src.db.transactions import transaction_exists
        
        return transaction_exists(
            founder_id=founder_id,
            date=txn.get("date"),
            amount=txn.get("debit", 0) or txn.get("credit", 0),
            description=txn.get("description"),
        )

    def _categorize_transaction(self, txn: Dict[str, Any]) -> Tuple[str, float]:
        """
        Categorize transaction using rule-based + LLM.

        Args:
            txn: Transaction dict

        Returns:
            (category, confidence) tuple
        """
        description = txn.get("description", "").lower()
        
        # Rule-based classification first
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in description:
                    return category, 0.95
        
        # Fallback to LLM categorization (future)
        return "Uncategorized", 0.5

    def _write_transaction(
        self,
        founder_id: str,
        txn: Dict[str, Any],
        category: str,
        confidence: float,
        needs_review: bool,
        raw_event_id: Optional[str] = None,
    ) -> None:
        """
        Write transaction to PostgreSQL.

        Args:
            founder_id: Founder ID
            txn: Transaction dict
            category: Transaction category
            confidence: Categorization confidence
            needs_review: Whether transaction needs manual review
            raw_event_id: Reference to raw_events table
        """
        from src.db.transactions import insert_transaction
        
        insert_transaction(
            founder_id=founder_id,
            txn_date=txn.get("date"),
            description=txn.get("description", ""),
            debit=txn.get("debit", 0),
            credit=txn.get("credit", 0),
            category=category,
            category_confidence=confidence,
            source="bank_statement",
            external_id=f"bank_{txn.get('date', '')}_{txn.get('description', '')[:20]}",
            needs_review=needs_review,
            raw_event_id=raw_event_id,
        )

    async def _upsert_qdrant(
        self,
        founder_id: str,
        txn: Dict[str, Any],
        category: str,
    ) -> None:
        """
        Upsert transaction to Qdrant for semantic search.

        Args:
            founder_id: Founder ID
            txn: Transaction dict
            category: Transaction category
        """
        from src.memory.qdrant_ops import upsert_memory
        
        content = f"{category}: {txn.get('description', '')} - ₹{txn.get('debit', 0) or txn.get('credit', 0)}"
        
        upsert_memory(
            founder_id=founder_id,
            content=content,
            memory_type="transaction",
            source="bank_statement",
        )

    async def _update_cfo_state(self, founder_id: str) -> int:
        """
        Update CFO forecast with new transactions.

        Args:
            founder_id: Founder ID

        Returns:
            Runway in days
        """
        from src.db.forecast import update_forecast, get_runway_days
        
        # Trigger forecast update
        await update_forecast(founder_id)
        
        # Get updated runway
        return await get_runway_days(founder_id)

    def _calculate_burn(self, transactions: List[Dict[str, Any]]) -> float:
        """
        Calculate monthly burn rate from transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            Total debit amount (burn)
        """
        total_debit = sum(txn.get("debit", 0) for txn in transactions)
        return total_debit

    def _total_credit(self, transactions: List[Dict[str, Any]]) -> float:
        """
        Calculate total credit from transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            Total credit amount
        """
        return sum(txn.get("credit", 0) for txn in transactions)

    def _total_debit(self, transactions: List[Dict[str, Any]]) -> float:
        """
        Calculate total debit from transactions.

        Args:
            transactions: List of transaction dicts

        Returns:
            Total debit amount
        """
        return sum(txn.get("debit", 0) for txn in transactions)

    def _extract_raw_event_id(self, payload_ref: str) -> str:
        """
        Extract UUID from payload_ref.

        Args:
            payload_ref: Reference string (e.g., "raw_events:uuid-123")

        Returns:
            UUID string
        """
        if ":" in payload_ref:
            return payload_ref.split(":", 1)[1]
        return payload_ref

    def _log_to_memory(
        self,
        founder_id: str,
        content: str,
        memory_type: str,
        source: str,
    ) -> None:
        """
        Log event to Qdrant memory.

        Args:
            founder_id: Founder ID
            content: Memory content
            memory_type: Type of memory
            source: Source system
        """
        from src.memory.qdrant_ops import upsert_memory
        
        upsert_memory(
            founder_id=founder_id,
            content=content,
            memory_type=memory_type,
            source=source,
        )


# Self-register on module import
register(BankStatementIngestSOP())
