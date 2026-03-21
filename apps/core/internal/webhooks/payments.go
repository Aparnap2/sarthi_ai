package webhooks

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"iterateswarm-core/internal/events"
	"iterateswarm-core/internal/logging"
	"iterateswarm-core/internal/redpanda"
)

// PaymentsHandler handles payment webhooks (Razorpay, Stripe)
type PaymentsHandler struct {
	redpandaClient *redpanda.Client
	db             *sql.DB
	repo           *webhookRepository
	logger         *logging.Logger

	// HMAC secrets (configured per source)
	razorpaySecret string
	stripeSecret   string
}

// NewPaymentsHandler creates a new PaymentsHandler
func NewPaymentsHandler(
	redpandaClient *redpanda.Client,
	db *sql.DB,
	repo *webhookRepository,
	razorpaySecret string,
	stripeSecret string,
) *PaymentsHandler {
	return &PaymentsHandler{
		redpandaClient: redpandaClient,
		db:             db,
		repo:           repo,
		logger:         logging.NewLogger("webhooks.payments"),
		razorpaySecret: razorpaySecret,
		stripeSecret:   stripeSecret,
	}
}

// HandleRazorpayWebhook processes Razorpay webhook events
func (h *PaymentsHandler) HandleRazorpayWebhook(c *fiber.Ctx) error {
	startTime := time.Now()
	source := events.SourceRazorpay

	// Verify HMAC signature
	signature := c.Get("X-Razorpay-Signature")
	if h.razorpaySecret != "" && signature != "" {
		if !h.verifyRazorpayHMAC(c.Body(), signature) {
			h.logger.Warn("invalid razorpay signature")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid signature",
			})
		}
	}

	// Parse the webhook payload
	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse razorpay payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid JSON payload",
		})
	}

	// Extract event type from payload
	eventTypeRaw, ok := payload["event"].(string)
	if !ok {
		h.logger.Warn("missing event type in razorpay payload")
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Missing event type",
		})
	}

	// Build idempotency key from payload
	idempotencyKey := h.buildIdempotencyKey(string(source), eventTypeRaw, payload)

	// Process the webhook
	result := h.processWebhook(c.Context(), source, eventTypeRaw, payload, idempotencyKey)

	h.logger.Info("razorpay webhook processed",
		"event", eventTypeRaw,
		"status", result.status,
		"duration_ms", time.Since(startTime).Milliseconds(),
	)

	return c.Status(result.statusCode).JSON(result.response)
}

// HandleStripeWebhook processes Stripe webhook events
func (h *PaymentsHandler) HandleStripeWebhook(c *fiber.Ctx) error {
	startTime := time.Now()
	source := "stripe"

	// Verify Stripe signature
	signature := c.Get("Stripe-Signature")
	if h.stripeSecret != "" && signature != "" {
		timestamp := c.Get("Stripe-Timestamp")
		if !h.verifyStripeHMAC(c.Body(), signature, timestamp) {
			h.logger.Warn("invalid stripe signature")
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Invalid signature",
			})
		}
	}

	// Parse the webhook payload
	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse stripe payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid JSON payload",
		})
	}

	// Extract event type from Stripe's type field
	eventTypeRaw, ok := payload["type"].(string)
	if !ok {
		h.logger.Warn("missing event type in stripe payload")
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Missing event type",
		})
	}

	// Build idempotency key using Stripe event ID
	eventID, _ := payload["id"].(string)
	idempotencyKey := fmt.Sprintf("stripe:%s:%s", eventID, eventTypeRaw)

	// Process the webhook
	result := h.processWebhook(c.Context(), events.EventSource(source), eventTypeRaw, payload, idempotencyKey)

	h.logger.Info("stripe webhook processed",
		"event", eventTypeRaw,
		"status", result.status,
		"duration_ms", time.Since(startTime).Milliseconds(),
	)

	return c.Status(result.statusCode).JSON(result.response)
}

// processWebhook handles the common webhook processing flow
func (h *PaymentsHandler) processWebhook(
	ctx context.Context,
	source events.EventSource,
	rawEventName string,
	payload map[string]interface{},
	idempotencyKey string,
) webhookResult {

	// Check idempotency - skip if already processed
	if h.db != nil && idempotencyKey != "" {
		ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
		defer cancel()

		isNew, err := h.repo.SetIdempotencyKey(ctx, idempotencyKey, string(source), 24*time.Hour)
		if err != nil {
			h.logger.Warn("failed to check idempotency", "error", err.Error())
			// Continue anyway - don't block on DB failure
		} else if !isNew {
			h.logger.Info("duplicate webhook skipped", "idempotency_key", idempotencyKey)
			return webhookResult{
				statusCode: fiber.StatusOK,
				status:     "already_processed",
				response:   fiber.Map{"status": "already_processed"},
			}
		}
	}

	// Generate IDs
	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event in PostgreSQL (into raw_events table)
	if h.db != nil {
		ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
		defer cancel()

		err := h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         string(source),
			EventType:      rawEventName,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
		if err != nil {
			h.logger.Error("failed to store raw event", err, "event_id", eventID)
			// Continue anyway - don't fail the webhook
		}
	}

	// Normalize the event type
	normalizer := events.NewNormalizer()
	eventType, err := normalizer.Normalize(source, rawEventName)
	if err != nil {
		// Fallback to raw event name if normalization fails
		eventType = events.EventType(rawEventName)
		h.logger.Warn("event normalization failed, using raw name", "raw_event", rawEventName, "error", err)
	}

	// Build EventEnvelope
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      eventType.String(),
		Source:         source,
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	// Publish to Redpanda
	if h.redpandaClient != nil {
		envelopeBytes, err := json.Marshal(envelope)
		if err != nil {
			h.logger.Error("failed to marshal envelope", err)
		} else {
			err = h.redpandaClient.Publish(envelopeBytes)
			if err != nil {
				h.logger.Error("failed to publish to redpanda", err)
				// Continue - webhook is still successful
			}
		}
	}

	return webhookResult{
		statusCode: fiber.StatusOK,
		status:     "accepted",
		response: fiber.Map{
			"status":      "accepted",
			"event_id":    eventID,
			"event_type":  eventType.String(),
			"idempotency": idempotencyKey,
		},
	}
}

// verifyRazorpayHMAC verifies Razorpay webhook signature
func (h *PaymentsHandler) verifyRazorpayHMAC(body []byte, signature string) bool {
	mac := hmac.New(sha256.New, []byte(h.razorpaySecret))
	mac.Write(body)
	expectedSig := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(expectedSig), []byte(signature))
}

// verifyStripeHMAC verifies Stripe webhook signature
func (h *PaymentsHandler) verifyStripeHMAC(body []byte, signature, timestamp string) bool {
	// Stripe signature format: t=timestamp,v1=signature
	// For simplicity, we'll do a basic check here
	// In production, implement full Stripe signature verification
	mac := hmac.New(sha256.New, []byte(h.stripeSecret))
	mac.Write(body)
	expectedSig := hex.EncodeToString(mac.Sum(nil))
	return hmac.Equal([]byte(expectedSig), []byte(signature))
}

// buildIdempotencyKey builds a unique key from payload
func (h *PaymentsHandler) buildIdempotencyKey(source, eventType string, payload map[string]interface{}) string {
	// Try to get payment ID from various sources
	var paymentID string
	if id, ok := payload["payment_id"].(string); ok {
		paymentID = id
	} else if id, ok := payload["id"].(string); ok {
		paymentID = id
	}
	return fmt.Sprintf("%s:%s:%s:v1", source, eventType, paymentID)
}

// extractTenantID extracts tenant ID from payload
func (h *PaymentsHandler) extractTenantID(payload map[string]interface{}) string {
	// In production, extract from webhook payload or headers
	// For now, use a default
	if tenantID, ok := payload["tenant_id"].(string); ok {
		return tenantID
	}
	return "default"
}

// computePayloadHash computes SHA-256 hash of payload
func (h *PaymentsHandler) computePayloadHash(payload map[string]interface{}) string {
	data, _ := json.Marshal(payload)
	hash := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(hash[:])
}

// webhookResult holds the result of webhook processing
type webhookResult struct {
	statusCode int
	status     string
	response   fiber.Map
}
