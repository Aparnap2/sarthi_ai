package webhooks

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"
)

// webhookRepository provides database operations for webhooks
type webhookRepository struct {
	db *sql.DB
}

// NewWebhookRepository creates a new webhook repository
func NewWebhookRepository(db *sql.DB) *webhookRepository {
	return &webhookRepository{db: db}
}

// RawEventParams holds parameters for inserting a raw event
type RawEventParams struct {
	TenantID       string
	Source         string
	EventType      string
	PayloadBody    map[string]interface{}
	IdempotencyKey string
}

// InsertRawEvent stores a raw event in the database
func (r *webhookRepository) InsertRawEvent(ctx context.Context, params RawEventParams) error {
	payloadJSON, err := json.Marshal(params.PayloadBody)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	payloadHash := computeJSONHash(payloadJSON)

	_, err = r.db.ExecContext(ctx, `
		INSERT INTO raw_events
			(tenant_id, source, event_type, payload_hash, payload_body, idempotency_key, received_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (idempotency_key) DO NOTHING
	`,
		params.TenantID,
		params.Source,
		params.EventType,
		payloadHash,
		payloadJSON,
		params.IdempotencyKey,
		time.Now().UTC(),
	)

	if err != nil {
		return fmt.Errorf("failed to insert raw event: %w", err)
	}

	return nil
}

// SetIdempotencyKey sets an idempotency key with expiration
func (r *webhookRepository) SetIdempotencyKey(ctx context.Context, key, source string, ttl time.Duration) (bool, error) {
	// The idempotency_key column in raw_events has a unique constraint
	// We try to insert a dummy row to check if the key exists
	// If insert succeeds, it's new. If it fails due to unique constraint, it's a duplicate.

	var exists bool
	err := r.db.QueryRowContext(ctx, `
		SELECT EXISTS(
			SELECT 1 FROM raw_events WHERE idempotency_key = $1
		)
	`, key).Scan(&exists)

	if err != nil {
		return false, fmt.Errorf("failed to check idempotency: %w", err)
	}

	if exists {
		return false, nil
	}

	// Insert a placeholder event with the idempotency key
	_, err = r.db.ExecContext(ctx, `
		INSERT INTO raw_events
			(tenant_id, source, event_type, payload_hash, payload_body, idempotency_key, received_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (idempotency_key) DO NOTHING
	`,
		"webhook-check",
		source,
		"idempotency_check",
		"sha256:placeholder",
		json.RawMessage(`{}`),
		key,
		time.Now().UTC(),
	)

	if err != nil {
		return false, fmt.Errorf("failed to set idempotency key: %w", err)
	}

	// Check again if it was actually inserted
	err = r.db.QueryRowContext(ctx, `
		SELECT EXISTS(
			SELECT 1 FROM raw_events WHERE idempotency_key = $1
		)
	`, key).Scan(&exists)

	return exists, err
}

// InsertDeadLetterEvent inserts an event into the dead letter queue
func (r *webhookRepository) InsertDeadLetterEvent(ctx context.Context, params DeadLetterParams) error {
	_, err := r.db.ExecContext(ctx, `
		INSERT INTO dead_letter_events
			(founder_id, source, event_name, failure_reason, raw_payload, retry_count, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
	`,
		params.FounderID,
		params.Source,
		params.EventName,
		params.FailureReason,
		params.RawPayload,
		params.RetryCount,
		time.Now().UTC(),
	)

	if err != nil {
		return fmt.Errorf("failed to insert dead letter event: %w", err)
	}

	return nil
}

// DeadLetterParams holds parameters for dead letter events
type DeadLetterParams struct {
	FounderID     string
	Source        string
	EventName     string
	FailureReason string
	RawPayload    []byte
	RetryCount    int
}

// computeJSONHash computes a simple hash of JSON data
func computeJSONHash(data []byte) string {
	hash := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", hash)
}
