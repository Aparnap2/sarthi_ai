package events_test

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"iterateswarm-core/internal/events"
)

// TestNormalizerRazorpay tests Razorpay -> EventType mappings
func TestNormalizerRazorpay(t *testing.T) {
	normalizer := events.NewNormalizer()

	tests := []struct {
		name         string
		source       events.EventSource
		rawEventName string
		expected     events.EventType
	}{
		{
			name:         "payment.captured -> PAYMENT_SUCCESS",
			source:       events.SourceRazorpay,
			rawEventName: "payment.captured",
			expected:     events.EventTypePaymentSuccess,
		},
		{
			name:         "subscription.cancelled -> SUBSCRIPTION_CANCELED",
			source:       events.SourceRazorpay,
			rawEventName: "subscription.cancelled",
			expected:     events.EventTypeSubscriptionCanceled,
		},
		{
			name:         "payment.failed -> PAYMENT_FAILED",
			source:       events.SourceRazorpay,
			rawEventName: "payment.failed",
			expected:     events.EventTypePaymentFailed,
		},
		{
			name:         "subscription.activated -> SUBSCRIPTION_ACTIVATED",
			source:       events.SourceRazorpay,
			rawEventName: "subscription.activated",
			expected:     events.EventTypeSubscriptionActive,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := normalizer.Normalize(tt.source, tt.rawEventName)
			require.NoError(t, err, "Normalization should succeed for %s::%s", tt.source, tt.rawEventName)
			assert.Equal(t, tt.expected, result, "EventType should match expected")
		})
	}
}

// TestNormalizerStripe tests Stripe -> EventType mappings
func TestNormalizerStripe(t *testing.T) {
	normalizer := events.NewNormalizer()

	tests := []struct {
		name         string
		source       events.EventSource
		rawEventName string
		expected     events.EventType
	}{
		{
			name:         "invoice.paid -> PAYMENT_SUCCESS",
			source:       "stripe",
			rawEventName: "invoice.paid",
			expected:     events.EventTypePaymentSuccess,
		},
		{
			name:         "payment_intent.succeeded -> PAYMENT_SUCCESS",
			source:       "stripe",
			rawEventName: "payment_intent.succeeded",
			expected:     events.EventTypePaymentSuccess,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := normalizer.Normalize(tt.source, tt.rawEventName)
			require.NoError(t, err)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestNormalizerIntercomCrisp tests Intercom/Crisp -> EventType mappings
func TestNormalizerIntercomCrisp(t *testing.T) {
	normalizer := events.NewNormalizer()

	tests := []struct {
		name         string
		source       events.EventSource
		rawEventName string
		expected     events.EventType
	}{
		{
			name:         "intercom user.created -> USER_SIGNED_UP",
			source:       events.EventSource("intercom"),
			rawEventName: "user.created",
			expected:     events.EventTypeUserSignedUp,
		},
		{
			name:         "intercom conversation.created -> SUPPORT_TICKET_CREATED",
			source:       events.EventSource("intercom"),
			rawEventName: "conversation.created",
			expected:     events.EventTypeSupportTicketCreated,
		},
		{
			name:         "crisp user.created -> USER_SIGNED_UP",
			source:       events.EventSource("crisp"),
			rawEventName: "user.created",
			expected:     events.EventTypeUserSignedUp,
		},
		{
			name:         "crisp conversation.created -> SUPPORT_TICKET_CREATED",
			source:       events.EventSource("crisp"),
			rawEventName: "conversation.created",
			expected:     events.EventTypeSupportTicketCreated,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := normalizer.Normalize(tt.source, tt.rawEventName)
			require.NoError(t, err)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestNormalizerHR tests Keka/Darwinbox -> EventType mappings
func TestNormalizerHR(t *testing.T) {
	normalizer := events.NewNormalizer()

	tests := []struct {
		name         string
		source       events.EventSource
		rawEventName string
		expected     events.EventType
	}{
		{
			name:         "keka employee.created -> EMPLOYEE_CREATED",
			source:       events.EventSource("keka"),
			rawEventName: "employee.created",
			expected:     events.EventTypeEmployeeCreated,
		},
		{
			name:         "keka employee.terminated -> EMPLOYEE_TERMINATED",
			source:       events.EventSource("keka"),
			rawEventName: "employee.terminated",
			expected:     events.EventTypeEmployeeTerminated,
		},
		{
			name:         "darwinbox employee.created -> EMPLOYEE_CREATED",
			source:       events.EventSource("darwinbox"),
			rawEventName: "employee.created",
			expected:     events.EventTypeEmployeeCreated,
		},
		{
			name:         "darwinbox employee.terminated -> EMPLOYEE_TERMINATED",
			source:       events.EventSource("darwinbox"),
			rawEventName: "employee.terminated",
			expected:     events.EventTypeEmployeeTerminated,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := normalizer.Normalize(tt.source, tt.rawEventName)
			require.NoError(t, err)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestNormalizerCron tests Cron -> EventType mappings
func TestNormalizerCron(t *testing.T) {
	normalizer := events.NewNormalizer()

	tests := []struct {
		name         string
		source       events.EventSource
		rawEventName string
		expected     events.EventType
	}{
		{
			name:         "cron.weekly -> TIME_TICK_WEEKLY",
			source:       events.SourceCron,
			rawEventName: "cron.weekly",
			expected:     events.EventTypeTimeTickWeekly,
		},
		{
			name:         "cron.daily -> TIME_TICK_DAILY",
			source:       events.SourceCron,
			rawEventName: "cron.daily",
			expected:     events.EventTypeTimeTickDaily,
		},
		{
			name:         "cron.monthly -> TIME_TICK_MONTHLY",
			source:       events.SourceCron,
			rawEventName: "cron.monthly",
			expected:     events.EventTypeTimeTickMonthly,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := normalizer.Normalize(tt.source, tt.rawEventName)
			require.NoError(t, err)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestNormalizerBank tests Bank webhook -> EventType mappings
func TestNormalizerBank(t *testing.T) {
	normalizer := events.NewNormalizer()

	result, err := normalizer.Normalize(events.EventSource("bank"), "transaction")
	require.NoError(t, err, "Bank transaction should normalize")
	assert.Equal(t, events.EventTypeBankWebhook, result, "Should map to BANK_WEBHOOK")
}

// TestNormalizerUnknownEvent tests handling of unknown events
func TestNormalizerUnknownEvent(t *testing.T) {
	normalizer := events.NewNormalizer()

	// Unknown source/event combination should return error
	_, err := normalizer.Normalize(events.EventSource("unknown"), "unknown.event")
	assert.Error(t, err, "Unknown source/event should return error")
	assert.Contains(t, err.Error(), "no normalization mapping", "Error should mention no mapping")

	// NormalizeOrUnknown should return UNKNOWN for unknown events
	result := normalizer.NormalizeOrUnknown(events.EventSource("unknown"), "unknown.event")
	assert.Equal(t, events.EventType("UNKNOWN"), result, "Should return UNKNOWN type")
}

// TestMappingCount verifies the total number of mappings
func TestMappingCount(t *testing.T) {
	count := events.MappingCount()
	assert.Greater(t, count, 0, "Should have at least some mappings")
	// We have 10+ mappings defined
	assert.GreaterOrEqual(t, count, 10, "Should have at least 10 mappings as per spec")
}
