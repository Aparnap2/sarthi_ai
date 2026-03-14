"""
Event Dictionary for Sarthi SOP Runtime.

Maps every (source, event_name) pair to exactly one topic and one SOP.
Enforced in code — unknown events raise UnknownEventError.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class DictionaryEntry:
    """Single event mapping entry."""
    source:     str
    event_name: str
    topic:      str
    sop:        str
    employees:  List[str] = field(default_factory=list)


class UnknownEventError(KeyError):
    """Raised when event is not in dictionary."""
    pass


# Registry of all 48 events from the design doc
_REGISTRY: List[DictionaryEntry] = [
    # ── RAZORPAY (11) ──────────────────────────────────────────────
    DictionaryEntry("razorpay", "payment.captured",       "finance.revenue.captured",       "SOP_REVENUE_RECEIVED",        ["Bookkeeper", "CFO"]),
    DictionaryEntry("razorpay", "payment.failed",         "finance.revenue.failed",         "SOP_PAYMENT_FAILURE",         ["AR/AP Clerk"]),
    DictionaryEntry("razorpay", "subscription.activated", "finance.subscription.new",       "SOP_NEW_SUBSCRIPTION",        ["Bookkeeper", "CFO"]),
    DictionaryEntry("razorpay", "subscription.halted",    "finance.subscription.halted",    "SOP_SUBSCRIPTION_HALTED",     ["AR/AP Clerk", "CFO"]),
    DictionaryEntry("razorpay", "subscription.cancelled", "finance.subscription.cancelled", "SOP_CHURN_DETECTED",          ["CFO", "BI Analyst"]),
    DictionaryEntry("razorpay", "invoice.paid",           "finance.invoice.paid",           "SOP_INVOICE_SETTLED",         ["AR/AP Clerk"]),
    DictionaryEntry("razorpay", "invoice.expired",        "finance.invoice.expired",        "SOP_INVOICE_OVERDUE",         ["AR/AP Clerk"]),
    DictionaryEntry("razorpay", "payout.processed",       "finance.payout.processed",       "SOP_PAYOUT_RECORDED",         ["Bookkeeper"]),
    DictionaryEntry("razorpay", "payout.failed",          "finance.payout.failed",          "SOP_PAYOUT_FAILURE",          ["Bookkeeper", "EA"]),
    DictionaryEntry("razorpay", "transaction.created",    "finance.transaction.new",        "SOP_TRANSACTION_INGESTED",    ["Bookkeeper"]),
    DictionaryEntry("razorpay", "refund.created",         "finance.refund.created",         "SOP_REFUND_RECORDED",         ["Bookkeeper", "CFO"]),

    # ── ZOHO BOOKS (7) ────────────────────────────────────────────
    DictionaryEntry("zoho_books", "invoice.created",      "finance.ap.invoice_created",     "SOP_VENDOR_INVOICE_RECEIVED", ["AR/AP Clerk"]),
    DictionaryEntry("zoho_books", "invoice.overdue",      "finance.ap.overdue",             "SOP_INVOICE_OVERDUE_AP",      ["AR/AP Clerk", "CFO"]),
    DictionaryEntry("zoho_books", "invoice.payment_made", "finance.ap.paid",                "SOP_PAYMENT_RECORDED",        ["Bookkeeper"]),
    DictionaryEntry("zoho_books", "expense.created",      "finance.expense.new",            "SOP_EXPENSE_INGESTED",        ["Bookkeeper"]),
    DictionaryEntry("zoho_books", "bill.created",         "finance.bill.new",               "SOP_BILL_RECEIVED",           ["AR/AP Clerk"]),
    DictionaryEntry("zoho_books", "contact.created",      "ops.vendor.new",                 "SOP_NEW_VENDOR_ONBOARD",      ["Procurement", "Legal"]),
    DictionaryEntry("zoho_books", "journal.created",      "finance.journal.new",            "SOP_JOURNAL_RECORDED",        ["Bookkeeper"]),

    # ── GOOGLE WORKSPACE (5) ──────────────────────────────────────
    DictionaryEntry("google_workspace", "calendar.new_event",  "ops.calendar.new_event",  "SOP_MEETING_PREP",        ["Virtual EA"]),
    DictionaryEntry("google_workspace", "calendar.upcoming",   "ops.calendar.upcoming",   "SOP_MEETING_BRIEF",       ["Virtual EA"]),
    DictionaryEntry("google_workspace", "team.new_member",     "people.team.new_member",  "SOP_EMPLOYEE_ONBOARD",    ["HR Coordinator"]),
    DictionaryEntry("google_workspace", "team.offboard",       "people.team.offboard",    "SOP_EMPLOYEE_OFFBOARD",   ["HR", "IT Admin"]),
    DictionaryEntry("google_workspace", "drive.contract_new",  "legal.contract.new",      "SOP_CONTRACT_INGESTED",   ["Contracts Coordinator"]),

    # ── ESIGN (5) ─────────────────────────────────────────────────
    DictionaryEntry("esign", "document.sent",     "legal.esign.sent",      "SOP_ESIGN_TRACKING_START", ["Contracts Coordinator"]),
    DictionaryEntry("esign", "document.viewed",   "legal.esign.viewed",    "SOP_ESIGN_VIEWED",         ["Contracts Coordinator"]),
    DictionaryEntry("esign", "document.signed",   "legal.esign.completed", "SOP_CONTRACT_EXECUTED",    ["Contracts Coordinator", "Knowledge Manager"]),
    DictionaryEntry("esign", "document.declined", "legal.esign.declined",  "SOP_ESIGN_DECLINED",       ["Contracts Coordinator", "EA"]),
    DictionaryEntry("esign", "document.expired",  "legal.esign.expired",   "SOP_ESIGN_EXPIRED",        ["Contracts Coordinator"]),

    # ── TELEGRAM (8) ──────────────────────────────────────────────
    DictionaryEntry("telegram", "file.csv",           "ingestion.file.csv",           "SOP_FILE_INGESTION",         ["Bookkeeper"]),
    DictionaryEntry("telegram", "pdf.bank_statement", "ingestion.pdf.bank_statement", "SOP_BANK_STATEMENT_INGEST",  ["Bookkeeper", "CFO"]),
    DictionaryEntry("telegram", "pdf.invoice",        "ingestion.pdf.invoice",        "SOP_VENDOR_INVOICE_RECEIVED",["AR/AP Clerk"]),
    DictionaryEntry("telegram", "pdf.contract",       "ingestion.pdf.contract",       "SOP_CONTRACT_INGESTED",      ["Contracts Coordinator"]),
    DictionaryEntry("telegram", "pdf.tax_notice",     "ingestion.pdf.tax_notice",     "SOP_TAX_NOTICE_RECEIVED",    ["Compliance Tracker"]),
    DictionaryEntry("telegram", "image.receipt",      "ingestion.image.receipt",      "SOP_RECEIPT_INGESTED",       ["Bookkeeper"]),
    DictionaryEntry("telegram", "query.inbound",      "ops.query.inbound",            "SOP_FOUNDER_QUERY",          ["Chief of Staff"]),
    DictionaryEntry("telegram", "decision.logged",    "ops.decision.logged",          "SOP_DECISION_LOGGED",        ["Knowledge Manager"]),

    # ── CRON (9) ──────────────────────────────────────────────────
    DictionaryEntry("cron", "ops.cron.weekly",       "ops.cron.weekly",       "SOP_WEEKLY_BRIEFING",       ["Chief of Staff"]),
    DictionaryEntry("cron", "compliance.cron.daily", "compliance.cron.daily", "SOP_COMPLIANCE_CHECK",      ["Compliance Tracker"]),
    DictionaryEntry("cron", "infra.cron.cost",       "infra.cron.cost",       "SOP_CLOUD_COST_REVIEW",     ["IT Admin"]),
    DictionaryEntry("cron", "finance.cron.ar_aging", "finance.cron.ar_aging", "SOP_AR_AGING_CHECK",        ["AR/AP Clerk"]),
    DictionaryEntry("cron", "legal.cron.expiry",     "legal.cron.expiry",     "SOP_CONTRACT_EXPIRY_CHECK", ["Contracts Coordinator"]),
    DictionaryEntry("cron", "intel.cron.policy",     "intel.cron.policy",     "SOP_POLICY_CRAWL",          ["Policy Watcher"]),
    DictionaryEntry("cron", "infra.cron.saas_audit", "infra.cron.saas_audit", "SOP_SAAS_AUDIT",            ["IT Admin"]),
    DictionaryEntry("cron", "people.cron.payroll",   "people.cron.payroll",   "SOP_PAYROLL_PREP",          ["Payroll Clerk"]),
    DictionaryEntry("cron", "finance.cron.monthend", "finance.cron.monthend", "SOP_MONTH_END_CLOSE",       ["Bookkeeper", "CFO"]),

    # ── AWS COST (4) ──────────────────────────────────────────────
    DictionaryEntry("aws_cost", "cloud.daily_cost",  "infra.cloud.daily_cost", "SOP_CLOUD_COST_REVIEW",    ["IT Admin"]),
    DictionaryEntry("aws_cost", "cloud.spike",       "infra.cloud.spike",      "SOP_CLOUD_COST_ALERT",     ["IT Admin", "CFO"]),
    DictionaryEntry("aws_cost", "cloud.new_service", "infra.cloud.new_service","SOP_NEW_SERVICE_DETECTED", ["IT Admin"]),
    DictionaryEntry("aws_cost", "cloud.waste",       "infra.cloud.waste",      "SOP_RESOURCE_WASTE",       ["IT Admin"]),

    # ── EMAIL FORWARD (1) ─────────────────────────────────────────
    DictionaryEntry("email_forward", "email.inbound", "ingestion.email.inbound", "SOP_FILE_INGESTION", ["Bookkeeper"]),
]


class EventDictionary:
    """
    Event dictionary for Sarthi SOP Runtime.

    Resolves (source, event_name) pairs to their corresponding
    topic, SOP, and responsible employees.

    Usage:
        d = EventDictionary()
        entry = d.resolve("razorpay", "payment.captured")
        print(entry.topic)  # "finance.revenue.captured"
        print(entry.sop)    # "SOP_REVENUE_RECEIVED"
    """

    def __init__(self):
        self._index = {(e.source, e.event_name): e for e in _REGISTRY}

    def resolve(self, source: str, event_name: str) -> DictionaryEntry:
        """
        Resolve (source, event_name) to DictionaryEntry.

        Args:
            source: Event source (e.g., "razorpay", "zoho_books")
            event_name: Event name (e.g., "payment.captured")

        Returns:
            DictionaryEntry with topic, sop, and employees

        Raises:
            UnknownEventError: If (source, event_name) not in dictionary
        """
        key = (source, event_name)
        if key not in self._index:
            raise UnknownEventError(
                f"No mapping for source='{source}' event_name='{event_name}'. "
                f"Add it to event_dictionary.py before handling."
            )
        return self._index[key]

    def all_entries(self) -> List[DictionaryEntry]:
        """Return all dictionary entries."""
        return list(self._index.values())

    def count(self) -> int:
        """Return total number of registered events."""
        return len(self._index)
