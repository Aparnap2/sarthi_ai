package events

import "time"

// EventSource represents all event sources in Sarthi.
type EventSource string

const (
	SourceRazorpay        EventSource = "razorpay"
	SourceZohoBooks       EventSource = "zoho_books"
	SourceGoogleWorkspace EventSource = "google_workspace"
	SourceESign           EventSource = "esign"
	SourceTelegram        EventSource = "telegram"
	SourceCron            EventSource = "cron"
	SourceAWSCost         EventSource = "aws_cost"
	SourceEmailForward    EventSource = "email_forward"
)

// EventEnvelope is the ONLY shape that flows through Redpanda and Temporal.
// PayloadRef points to raw_events table — NEVER contains raw JSON.
type EventEnvelope struct {
	// EventID is a unique event identifier (UUID)
	EventID string `json:"event_id"`

	// FounderID is the founder who owns this event (UUID)
	FounderID string `json:"founder_id"`

	// Source is the event source (razorpay, zoho_books, etc.)
	Source EventSource `json:"source"`

	// EventName is the event name from source (e.g., "payment.captured")
	EventName string `json:"event_name"`

	// Topic is the Redpanda topic to publish to
	Topic string `json:"topic"`

	// SOPName is the SOP to execute (e.g., "SOP_REVENUE_RECEIVED")
	SOPName string `json:"sop_name"`

	// PayloadRef is a storage reference ("raw_events:<uuid>" or "files:<path>")
	// NEVER contains raw JSON — store in PostgreSQL first
	PayloadRef string `json:"payload_ref"`

	// PayloadHash is the SHA-256 hash of raw payload
	PayloadHash string `json:"payload_hash"`

	// OccurredAt is when the event occurred (from source)
	OccurredAt time.Time `json:"occurred_at"`

	// ReceivedAt is when Sarthi received the event
	ReceivedAt time.Time `json:"received_at"`

	// TraceID is the distributed tracing ID (for Langfuse)
	TraceID string `json:"trace_id"`

	// IdempotencyKey is the deduplication key (e.g., "razorpay:pay_abc:v1")
	IdempotencyKey string `json:"idempotency_key"`

	// Version is the envelope schema version (default "v1")
	Version string `json:"version"`
}
