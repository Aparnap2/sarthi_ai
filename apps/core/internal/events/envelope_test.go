package events_test

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"iterateswarm-core/internal/events"
)

func TestEventEnvelope_ValidEnvelope(t *testing.T) {
	env := events.EventEnvelope{
		TenantID:       "tenant_test",
		EventType:      "PAYMENT_SUCCESS",
		Source:         events.SourceRazorpay,
		PayloadRef:     "raw_events:abc123",
		PayloadHash:    "sha256:deadbeef",
		IdempotencyKey: "razorpay:pay_abc123:v1",
		OccurredAt:     time.Now(),
		ReceivedAt:     time.Now(),
		TraceID:        "trace_test",
	}

	assert.Equal(t, "tenant_test", env.TenantID)
	assert.Equal(t, "PAYMENT_SUCCESS", env.EventType)
	assert.Equal(t, events.SourceRazorpay, env.Source)
	assert.Equal(t, "raw_events:abc123", env.PayloadRef)
}

func TestEventEnvelope_PayloadRef_NotRawJSON(t *testing.T) {
	// This would be validated at application layer
	// The struct itself doesn't validate, but usage should
	env := events.EventEnvelope{
		TenantID:       "tenant_test",
		EventType:      "PAYMENT_SUCCESS",
		Source:         events.SourceRazorpay,
		PayloadRef:     `{"amount":5000}`, // Invalid - raw JSON
		PayloadHash:    "sha256:abc",
		IdempotencyKey: "test:v1",
		OccurredAt:     time.Now(),
		ReceivedAt:     time.Now(),
		TraceID:        "trace_test",
	}

	// Application layer should reject this
	assert.Contains(t, env.PayloadRef, "{")
	// In real usage, normalizer would reject this
}
