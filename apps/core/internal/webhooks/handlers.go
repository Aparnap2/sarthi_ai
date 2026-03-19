package webhooks

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"iterateswarm-core/internal/events"
	"iterateswarm-core/internal/logging"
	"iterateswarm-core/internal/redpanda"
)

// =============================================================================
// CRM Handler (Pipeline Deals)
// =============================================================================

// CRMHandler handles CRM webhook events (deals, contacts)
type CRMHandler struct {
	redpandaClient *redpanda.Client
	db             *sql.DB
	repo           *webhookRepository
	logger         *logging.Logger
}

// NewCRMHandler creates a new CRMHandler
func NewCRMHandler(redpandaClient *redpanda.Client, db *sql.DB, repo *webhookRepository) *CRMHandler {
	return &CRMHandler{
		redpandaClient: redpandaClient,
		db:             db,
		repo:           repo,
		logger:         logging.NewLogger("webhooks.crm"),
	}
}

// HandleZohoBooksWebhook processes Zoho Books CRM webhooks
func (h *CRMHandler) HandleZohoBooksWebhook(c *fiber.Ctx) error {
	return h.processGenericWebhook(c, "zoho_books")
}

// HandleGenericCRMWebhook processes generic CRM webhook events
func (h *CRMHandler) HandleGenericCRMWebhook(c *fiber.Ctx) error {
	source := c.Query("source", "crm")
	return h.processGenericWebhook(c, source)
}

func (h *CRMHandler) processGenericWebhook(c *fiber.Ctx, source string) error {
	startTime := time.Now()

	// Parse payload
	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse crm payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid JSON payload",
		})
	}

	// Extract event type - varies by CRM provider
	eventTypeRaw := h.extractCRMEventType(payload)

	// Build idempotency key
	idempotencyKey := fmt.Sprintf("crm:%s:%v", source, payload["id"])

	// Check idempotency
	if h.db != nil && idempotencyKey != "" {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()

		isNew, err := h.repo.SetIdempotencyKey(ctx, idempotencyKey, source, 24*time.Hour)
		if err != nil {
			h.logger.Warn("failed to check idempotency", "error", err.Error())
		} else if !isNew {
			h.logger.Info("duplicate crm webhook skipped", "idempotency_key", idempotencyKey)
			return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "already_processed"})
		}
	}

	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event
	if h.db != nil {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         source,
			EventType:      eventTypeRaw,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
	}

	// Normalize event type
	normalizer := events.NewNormalizer()
	eventType, _ := normalizer.Normalize(events.EventSource(source), eventTypeRaw)
	if eventType == "" {
		eventType = events.EventType(eventTypeRaw)
	}

	// Build and publish envelope
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      eventType.String(),
		Source:         events.EventSource(source),
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	if h.redpandaClient != nil {
		envelopeBytes, _ := json.Marshal(envelope)
		h.redpandaClient.Publish(envelopeBytes)
	}

	h.logger.Info("crm webhook processed",
		"source", source,
		"event", eventTypeRaw,
		"duration_ms", time.Since(startTime).Milliseconds(),
	)

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":     "accepted",
		"event_id":   eventID,
		"event_type": eventType.String(),
	})
}

func (h *CRMHandler) extractCRMEventType(payload map[string]interface{}) string {
	// Try various common CRM event type fields
	if event, ok := payload["event"].(string); ok {
		return event
	}
	if event, ok := payload["event_type"].(string); ok {
		return event
	}
	if event, ok := payload["type"].(string); ok {
		return event
	}
	return "unknown"
}

func (h *CRMHandler) extractTenantID(payload map[string]interface{}) string {
	if tenantID, ok := payload["tenant_id"].(string); ok {
		return tenantID
	}
	if tenantID, ok := payload["organization_id"].(string); ok {
		return tenantID
	}
	return "default"
}

func (h *CRMHandler) computePayloadHash(payload map[string]interface{}) string {
	data, _ := json.Marshal(payload)
	hash := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", hash)
}

// =============================================================================
// Support Handler (Intercom, Crisp)
// =============================================================================

// SupportHandler handles support platform webhooks (Intercom, Crisp)
type SupportHandler struct {
	redpandaClient *redpanda.Client
	db             *sql.DB
	repo           *webhookRepository
	logger         *logging.Logger
}

// NewSupportHandler creates a new SupportHandler
func NewSupportHandler(redpandaClient *redpanda.Client, db *sql.DB, repo *webhookRepository) *SupportHandler {
	return &SupportHandler{
		redpandaClient: redpandaClient,
		db:             db,
		repo:           repo,
		logger:         logging.NewLogger("webhooks.support"),
	}
}

// HandleIntercomWebhook processes Intercom webhooks
func (h *SupportHandler) HandleIntercomWebhook(c *fiber.Ctx) error {
	return h.processSupportWebhook(c, "intercom")
}

// HandleCrispWebhook processes Crisp webhooks
func (h *SupportHandler) HandleCrispWebhook(c *fiber.Ctx) error {
	return h.processSupportWebhook(c, "crisp")
}

func (h *SupportHandler) processSupportWebhook(c *fiber.Ctx, source string) error {
	startTime := time.Now()

	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse support payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid JSON"})
	}

	// Extract event type
	eventTypeRaw := h.extractSupportEventType(payload, source)
	idempotencyKey := fmt.Sprintf("%s:%v", source, payload["id"])

	// Check idempotency
	if h.db != nil && idempotencyKey != "" {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		isNew, _ := h.repo.SetIdempotencyKey(ctx, idempotencyKey, source, 24*time.Hour)
		if !isNew {
			return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "already_processed"})
		}
	}

	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event
	if h.db != nil {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         source,
			EventType:      eventTypeRaw,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
	}

	// Normalize
	normalizer := events.NewNormalizer()
	eventType, _ := normalizer.Normalize(events.EventSource(source), eventTypeRaw)
	if eventType == "" {
		eventType = events.EventType(eventTypeRaw)
	}

	// Publish
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      eventType.String(),
		Source:         events.EventSource(source),
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	if h.redpandaClient != nil {
		envelopeBytes, _ := json.Marshal(envelope)
		h.redpandaClient.Publish(envelopeBytes)
	}

	h.logger.Info("support webhook processed", "source", source, "event", eventTypeRaw, "duration_ms", time.Since(startTime).Milliseconds())

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":     "accepted",
		"event_id":   eventID,
		"event_type": eventType.String(),
	})
}

func (h *SupportHandler) extractSupportEventType(payload map[string]interface{}, source string) string {
	if source == "intercom" {
		if topic, ok := payload["topic"].(string); ok {
			return topic
		}
	}
	if event, ok := payload["event"].(string); ok {
		return event
	}
	return "unknown"
}

func (h *SupportHandler) extractTenantID(payload map[string]interface{}) string {
	if id, ok := payload["tenant_id"].(string); ok {
		return id
	}
	return "default"
}

func (h *SupportHandler) computePayloadHash(payload map[string]interface{}) string {
	data, _ := json.Marshal(payload)
	hash := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", hash)
}

// =============================================================================
// HR Handler (Keka, Darwinbox)
// =============================================================================

// HRHandler handles HR platform webhooks (Keka, Darwinbox)
type HRHandler struct {
	redpandaClient *redpanda.Client
	db             *sql.DB
	repo           *webhookRepository
	logger         *logging.Logger
}

// NewHRHandler creates a new HRHandler
func NewHRHandler(redpandaClient *redpanda.Client, db *sql.DB, repo *webhookRepository) *HRHandler {
	return &HRHandler{
		redpandaClient: redpandaClient,
		db:             db,
		repo:           repo,
		logger:         logging.NewLogger("webhooks.hr"),
	}
}

// HandleKekaWebhook processes Keka HR webhooks
func (h *HRHandler) HandleKekaWebhook(c *fiber.Ctx) error {
	return h.processHRWebhook(c, "keka")
}

// HandleDarwinboxWebhook processes Darwinbox HR webhooks
func (h *HRHandler) HandleDarwinboxWebhook(c *fiber.Ctx) error {
	return h.processHRWebhook(c, "darwinbox")
}

func (h *HRHandler) processHRWebhook(c *fiber.Ctx, source string) error {
	startTime := time.Now()

	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse hr payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid JSON"})
	}

	// Extract event type
	eventTypeRaw := h.extractHREventType(payload)
	idempotencyKey := fmt.Sprintf("%s:%v", source, payload["employee_id"])

	// Check idempotency
	if h.db != nil && idempotencyKey != "" {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		isNew, _ := h.repo.SetIdempotencyKey(ctx, idempotencyKey, source, 24*time.Hour)
		if !isNew {
			return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "already_processed"})
		}
	}

	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event
	if h.db != nil {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         source,
			EventType:      eventTypeRaw,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
	}

	// Normalize
	normalizer := events.NewNormalizer()
	eventType, _ := normalizer.Normalize(events.EventSource(source), eventTypeRaw)
	if eventType == "" {
		eventType = events.EventType(eventTypeRaw)
	}

	// Publish
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      eventType.String(),
		Source:         events.EventSource(source),
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	if h.redpandaClient != nil {
		envelopeBytes, _ := json.Marshal(envelope)
		h.redpandaClient.Publish(envelopeBytes)
	}

	h.logger.Info("hr webhook processed", "source", source, "event", eventTypeRaw, "duration_ms", time.Since(startTime).Milliseconds())

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":     "accepted",
		"event_id":   eventID,
		"event_type": eventType.String(),
	})
}

func (h *HRHandler) extractHREventType(payload map[string]interface{}) string {
	if event, ok := payload["event"].(string); ok {
		return event
	}
	if event, ok := payload["event_type"].(string); ok {
		return event
	}
	if event, ok := payload["type"].(string); ok {
		return event
	}
	return "unknown"
}

func (h *HRHandler) extractTenantID(payload map[string]interface{}) string {
	if id, ok := payload["tenant_id"].(string); ok {
		return id
	}
	return "default"
}

func (h *HRHandler) computePayloadHash(payload map[string]interface{}) string {
	data, _ := json.Marshal(payload)
	hash := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", hash)
}

// =============================================================================
// Bank Handler
// =============================================================================

// BankHandler handles bank webhook events
type BankHandler struct {
	redpandaClient *redpanda.Client
	db             *sql.DB
	repo           *webhookRepository
	logger         *logging.Logger
}

// NewBankHandler creates a new BankHandler
func NewBankHandler(redpandaClient *redpanda.Client, db *sql.DB, repo *webhookRepository) *BankHandler {
	return &BankHandler{
		redpandaClient: redpandaClient,
		db:             db,
		repo:           repo,
		logger:         logging.NewLogger("webhooks.bank"),
	}
}

// HandleBankWebhook processes bank webhook events
func (h *BankHandler) HandleBankWebhook(c *fiber.Ctx) error {
	startTime := time.Now()

	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		h.logger.Error("failed to parse bank payload", err)
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid JSON"})
	}

	source := "bank"
	eventTypeRaw := "bank.transaction"
	idempotencyKey := fmt.Sprintf("bank:%v:%v", payload["transaction_id"], payload["timestamp"])

	// Check idempotency
	if h.db != nil && idempotencyKey != "" {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		isNew, _ := h.repo.SetIdempotencyKey(ctx, idempotencyKey, source, 24*time.Hour)
		if !isNew {
			return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "already_processed"})
		}
	}

	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event
	if h.db != nil {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         source,
			EventType:      eventTypeRaw,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
	}

	// Normalize
	normalizer := events.NewNormalizer()
	eventType, _ := normalizer.Normalize(events.EventSource(source), eventTypeRaw)
	if eventType == "" {
		eventType = events.EventTypeBankWebhook
	}

	// Publish
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      eventType.String(),
		Source:         events.EventSource(source),
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	if h.redpandaClient != nil {
		envelopeBytes, _ := json.Marshal(envelope)
		h.redpandaClient.Publish(envelopeBytes)
	}

	h.logger.Info("bank webhook processed", "duration_ms", time.Since(startTime).Milliseconds())

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":     "accepted",
		"event_id":   eventID,
		"event_type": eventType.String(),
	})
}

func (h *BankHandler) extractTenantID(payload map[string]interface{}) string {
	if id, ok := payload["tenant_id"].(string); ok {
		return id
	}
	return "default"
}

func (h *BankHandler) computePayloadHash(payload map[string]interface{}) string {
	data, _ := json.Marshal(payload)
	hash := sha256.Sum256(data)
	return fmt.Sprintf("sha256:%x", hash)
}

// HandleCronBank processes bank data from cron (gws CLI)
func (h *BankHandler) HandleCronBank(c *fiber.Ctx) error {
	startTime := time.Now()

	var payload map[string]interface{}
	if err := json.Unmarshal(c.Body(), &payload); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid JSON"})
	}

	source := "cron"
	eventTypeRaw := "bank.transaction"

	// Generate idempotency key based on date
	date := time.Now().Format("2006-01-02")
	idempotencyKey := fmt.Sprintf("cron:bank:%s", date)

	tenantID := h.extractTenantID(payload)
	eventID := uuid.New().String()

	// Store raw event
	if h.db != nil {
		ctx, cancel := context.WithTimeout(c.Context(), 5*time.Second)
		defer cancel()
		h.repo.InsertRawEvent(ctx, RawEventParams{
			TenantID:       tenantID,
			Source:         source,
			EventType:      eventTypeRaw,
			PayloadBody:    payload,
			IdempotencyKey: idempotencyKey,
		})
	}

	// Publish
	envelope := events.EventEnvelope{
		TenantID:       tenantID,
		EventType:      events.EventTypeBankWebhook.String(),
		Source:         events.SourceCron,
		PayloadRef:     fmt.Sprintf("raw_events:%s", eventID),
		PayloadHash:    h.computePayloadHash(payload),
		IdempotencyKey: idempotencyKey,
		OccurredAt:     time.Now().UTC(),
		ReceivedAt:     time.Now().UTC(),
		TraceID:        uuid.New().String(),
	}

	if h.redpandaClient != nil {
		envelopeBytes, _ := json.Marshal(envelope)
		h.redpandaClient.Publish(envelopeBytes)
	}

	h.logger.Info("cron bank processed", "duration_ms", time.Since(startTime).Milliseconds())

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":   "accepted",
		"event_id": eventID,
	})
}
