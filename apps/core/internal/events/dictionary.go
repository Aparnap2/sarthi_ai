package events

import "fmt"

// DictionaryEntry represents a single event mapping.
type DictionaryEntry struct {
	Source    EventSource
	EventName string
	Topic     string
	SOPName   string
	Employees []string
}

// EventDictionary provides event resolution functionality
type EventDictionary struct{}

// NewEventDictionary creates a new EventDictionary
func NewEventDictionary() *EventDictionary {
	return &EventDictionary{}
}

// Resolve looks up an event by source and name.
func (d *EventDictionary) Resolve(source EventSource, eventName string) (DictionaryEntry, error) {
	return Resolve(source, eventName)
}

// Registry of all events from the design doc.
var registry = []DictionaryEntry{
	// RAZORPAY (11)
	{SourceRazorpay, "payment.captured", "finance.revenue.captured", "SOP_REVENUE_RECEIVED", []string{"Bookkeeper", "CFO"}},
	{SourceRazorpay, "payment.failed", "finance.revenue.failed", "SOP_PAYMENT_FAILURE", []string{"AR/AP Clerk"}},
	{SourceRazorpay, "subscription.activated", "finance.subscription.new", "SOP_NEW_SUBSCRIPTION", []string{"Bookkeeper", "CFO"}},
	{SourceRazorpay, "subscription.halted", "finance.subscription.halted", "SOP_SUBSCRIPTION_HALTED", []string{"AR/AP Clerk", "CFO"}},
	{SourceRazorpay, "subscription.cancelled", "finance.subscription.cancelled", "SOP_CHURN_DETECTED", []string{"CFO", "BI Analyst"}},
	{SourceRazorpay, "invoice.paid", "finance.invoice.paid", "SOP_INVOICE_SETTLED", []string{"AR/AP Clerk"}},
	{SourceRazorpay, "invoice.expired", "finance.invoice.expired", "SOP_INVOICE_OVERDUE", []string{"AR/AP Clerk"}},
	{SourceRazorpay, "payout.processed", "finance.payout.processed", "SOP_PAYOUT_RECORDED", []string{"Bookkeeper"}},
	{SourceRazorpay, "payout.failed", "finance.payout.failed", "SOP_PAYOUT_FAILURE", []string{"Bookkeeper", "EA"}},
	{SourceRazorpay, "transaction.created", "finance.transaction.new", "SOP_TRANSACTION_INGESTED", []string{"Bookkeeper"}},
	{SourceRazorpay, "refund.created", "finance.refund.created", "SOP_REFUND_RECORDED", []string{"Bookkeeper", "CFO"}},

	// ZOHO BOOKS (7)
	{SourceZohoBooks, "invoice.created", "finance.ap.invoice_created", "SOP_VENDOR_INVOICE_RECEIVED", []string{"AR/AP Clerk"}},
	{SourceZohoBooks, "invoice.overdue", "finance.ap.overdue", "SOP_INVOICE_OVERDUE_AP", []string{"AR/AP Clerk", "CFO"}},
	{SourceZohoBooks, "invoice.payment_made", "finance.ap.paid", "SOP_PAYMENT_RECORDED", []string{"Bookkeeper"}},
	{SourceZohoBooks, "expense.created", "finance.expense.new", "SOP_EXPENSE_INGESTED", []string{"Bookkeeper"}},
	{SourceZohoBooks, "bill.created", "finance.bill.new", "SOP_BILL_RECEIVED", []string{"AR/AP Clerk"}},
	{SourceZohoBooks, "contact.created", "ops.vendor.new", "SOP_NEW_VENDOR_ONBOARD", []string{"Procurement", "Legal"}},
	{SourceZohoBooks, "journal.created", "finance.journal.new", "SOP_JOURNAL_RECORDED", []string{"Bookkeeper"}},

	// GOOGLE WORKSPACE (5)
	{SourceGoogleWorkspace, "calendar.new_event", "ops.calendar.new_event", "SOP_MEETING_PREP", []string{"Virtual EA"}},
	{SourceGoogleWorkspace, "calendar.upcoming", "ops.calendar.upcoming", "SOP_MEETING_BRIEF", []string{"Virtual EA"}},
	{SourceGoogleWorkspace, "team.new_member", "people.team.new_member", "SOP_EMPLOYEE_ONBOARD", []string{"HR Coordinator"}},
	{SourceGoogleWorkspace, "team.offboard", "people.team.offboard", "SOP_EMPLOYEE_OFFBOARD", []string{"HR", "IT Admin"}},
	{SourceGoogleWorkspace, "drive.contract_new", "legal.contract.new", "SOP_CONTRACT_INGESTED", []string{"Contracts Coordinator"}},

	// ESIGN (5)
	{SourceESign, "document.sent", "legal.esign.sent", "SOP_ESIGN_TRACKING_START", []string{"Contracts Coordinator"}},
	{SourceESign, "document.viewed", "legal.esign.viewed", "SOP_ESIGN_VIEWED", []string{"Contracts Coordinator"}},
	{SourceESign, "document.signed", "legal.esign.completed", "SOP_CONTRACT_EXECUTED", []string{"Contracts Coordinator", "Knowledge Manager"}},
	{SourceESign, "document.declined", "legal.esign.declined", "SOP_ESIGN_DECLINED", []string{"Contracts Coordinator", "EA"}},
	{SourceESign, "document.expired", "legal.esign.expired", "SOP_ESIGN_EXPIRED", []string{"Contracts Coordinator"}},

	// TELEGRAM (8)
	{SourceTelegram, "file.csv", "ingestion.file.csv", "SOP_FILE_INGESTION", []string{"Bookkeeper"}},
	{SourceTelegram, "pdf.bank_statement", "ingestion.pdf.bank_statement", "SOP_BANK_STATEMENT_INGEST", []string{"Bookkeeper", "CFO"}},
	{SourceTelegram, "pdf.invoice", "ingestion.pdf.invoice", "SOP_VENDOR_INVOICE_RECEIVED", []string{"AR/AP Clerk"}},
	{SourceTelegram, "pdf.contract", "ingestion.pdf.contract", "SOP_CONTRACT_INGESTED", []string{"Contracts Coordinator"}},
	{SourceTelegram, "pdf.tax_notice", "ingestion.pdf.tax_notice", "SOP_TAX_NOTICE_RECEIVED", []string{"Compliance Tracker"}},
	{SourceTelegram, "image.receipt", "ingestion.image.receipt", "SOP_RECEIPT_INGESTED", []string{"Bookkeeper"}},
	{SourceTelegram, "query.inbound", "ops.query.inbound", "SOP_FOUNDER_QUERY", []string{"Chief of Staff"}},
	{SourceTelegram, "decision.logged", "ops.decision.logged", "SOP_DECISION_LOGGED", []string{"Knowledge Manager"}},

	// CRON (9)
	{SourceCron, "ops.cron.weekly", "ops.cron.weekly", "SOP_WEEKLY_BRIEFING", []string{"Chief of Staff"}},
	{SourceCron, "compliance.cron.daily", "compliance.cron.daily", "SOP_COMPLIANCE_CHECK", []string{"Compliance Tracker"}},
	{SourceCron, "infra.cron.cost", "infra.cron.cost", "SOP_CLOUD_COST_REVIEW", []string{"IT Admin"}},
	{SourceCron, "finance.cron.ar_aging", "finance.cron.ar_aging", "SOP_AR_AGING_CHECK", []string{"AR/AP Clerk"}},
	{SourceCron, "legal.cron.expiry", "legal.cron.expiry", "SOP_CONTRACT_EXPIRY_CHECK", []string{"Contracts Coordinator"}},
	{SourceCron, "intel.cron.policy", "intel.cron.policy", "SOP_POLICY_CRAWL", []string{"Policy Watcher"}},
	{SourceCron, "infra.cron.saas_audit", "infra.cron.saas_audit", "SOP_SAAS_AUDIT", []string{"IT Admin"}},
	{SourceCron, "people.cron.payroll", "people.cron.payroll", "SOP_PAYROLL_PREP", []string{"Payroll Clerk"}},
	{SourceCron, "finance.cron.monthend", "finance.cron.monthend", "SOP_MONTH_END_CLOSE", []string{"Bookkeeper", "CFO"}},

	// AWS COST (4)
	{SourceAWSCost, "cloud.daily_cost", "infra.cloud.daily_cost", "SOP_CLOUD_COST_REVIEW", []string{"IT Admin"}},
	{SourceAWSCost, "cloud.spike", "infra.cloud.spike", "SOP_CLOUD_COST_ALERT", []string{"IT Admin", "CFO"}},
	{SourceAWSCost, "cloud.new_service", "infra.cloud.new_service", "SOP_NEW_SERVICE_DETECTED", []string{"IT Admin"}},
	{SourceAWSCost, "cloud.waste", "infra.cloud.waste", "SOP_RESOURCE_WASTE", []string{"IT Admin"}},

	// EMAIL FORWARD (1)
	{SourceEmailForward, "email.inbound", "ingestion.email.inbound", "SOP_FILE_INGESTION", []string{"Bookkeeper"}},
}

// Index for fast lookup.
var index map[string]DictionaryEntry

func init() {
	index = make(map[string]DictionaryEntry)
	for _, e := range registry {
		key := fmt.Sprintf("%s::%s", e.Source, e.EventName)
		index[key] = e
	}
}

// Resolve looks up an event by source and name.
func Resolve(source EventSource, eventName string) (DictionaryEntry, error) {
	key := fmt.Sprintf("%s::%s", source, eventName)
	e, ok := index[key]
	if !ok {
		return DictionaryEntry{}, fmt.Errorf("no mapping for source=%q event_name=%q", source, eventName)
	}
	return e, nil
}

// Count returns the total number of registered events.
func Count() int {
	return len(registry)
}
