package web_test

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"iterateswarm-core/internal/db"
	"iterateswarm-core/internal/web"
)

// setupTelegramTestApp creates a test Fiber app with Telegram handler
func setupTelegramTestApp(t *testing.T) (*fiber.App, func()) {
	t.Helper()

	pool, poolTeardown := setupTestDB(t)
	repo := db.NewRepositoryFromPool(pool)

	// Always use mock producer for tests to avoid Kafka dependency
	producerInterface := &mockProducer{}

	handler := web.NewTelegramHandler(repo, producerInterface)

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		},
	})

	// Register the Telegram webhook route
	app.Post("/webhooks/telegram", handler.Handle)

	teardown := func() {
		poolTeardown()
	}

	return app, teardown
}

// TestTelegramDocumentMessageClassified tests that PDF bank statements are properly classified
func TestTelegramDocumentMessageClassified(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	// Simulate Telegram document message (PDF bank statement)
	timestamp := time.Now().Format("20060102150405")
	update := map[string]interface{}{
		"update_id": 123456,
		"message": map[string]interface{}{
			"message_id": 789000 + time.Now().UnixNano()%10000, // Unique message ID
			"from": map[string]interface{}{
				"id":         123456789,
				"first_name": "Test User",
			},
			"chat": map[string]interface{}{
				"id":   123456789,
				"type": "private",
			},
			"document": map[string]interface{}{
				"file_name": "hdfc_statement_march_" + timestamp + ".pdf",
				"mime_type": "application/pdf",
				"file_id":   "BQACAgQAAxkBAAIB",
			},
		},
	}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode, "Document message should be accepted")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "accepted", respBody["status"])
}

// TestTelegramPhotoMessageClassified tests that photo messages are properly classified
func TestTelegramPhotoMessageClassified(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	timestamp := time.Now().Format("20060102150405")
	update := map[string]interface{}{
		"update_id": 123457,
		"message": map[string]interface{}{
			"message_id": 790000 + time.Now().UnixNano()%10000,
			"from":       map[string]interface{}{"id": 123456789},
			"chat":       map[string]interface{}{"id": 123456789, "type": "private"},
			"photo": []interface{}{
				map[string]interface{}{
					"file_id":   "AgACAgQAAxkBAAIB",
					"file_size": 12345,
				},
			},
			"caption": "receipt for office supplies " + timestamp,
		},
	}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode, "Photo message should be accepted")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "accepted", respBody["status"])
}

// TestTelegramTextMessageClassified tests that text messages are properly classified
func TestTelegramTextMessageClassified(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	timestamp := time.Now().Format("20060102150405")
	update := map[string]interface{}{
		"update_id": 123458,
		"message": map[string]interface{}{
			"message_id": 791000 + time.Now().UnixNano()%10000,
			"from":       map[string]interface{}{"id": 123456789},
			"chat":       map[string]interface{}{"id": 123456789, "type": "private"},
			"text":       "What's my runway? " + timestamp,
		},
	}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode, "Text message should be accepted")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "accepted", respBody["status"])
}

// TestTelegramInvalidUpdateRejected tests that invalid updates are rejected with 400
func TestTelegramInvalidUpdateRejected(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	// Missing required fields (no message)
	update := map[string]interface{}{"update_id": 123459}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 400, resp.StatusCode, "Invalid update should be rejected")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "invalid_update", respBody["error"])
}

// TestTelegramDecisionMessageClassified tests that decision messages are properly classified
func TestTelegramDecisionMessageClassified(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	timestamp := time.Now().Format("20060102150405")
	update := map[string]interface{}{
		"update_id": 123460,
		"message": map[string]interface{}{
			"message_id": 792000 + time.Now().UnixNano()%10000,
			"from":       map[string]interface{}{"id": 123456789},
			"chat":       map[string]interface{}{"id": 123456789, "type": "private"},
			"text":       "We're going with Option A for the pricing strategy " + timestamp,
		},
	}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode, "Decision message should be accepted")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "accepted", respBody["status"])
}

// TestTelegramInvoiceDocumentClassified tests that invoice documents are properly classified
func TestTelegramInvoiceDocumentClassified(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	timestamp := time.Now().Format("20060102150405")
	update := map[string]interface{}{
		"update_id": 123461,
		"message": map[string]interface{}{
			"message_id": 793000 + time.Now().UnixNano()%10000,
			"from":       map[string]interface{}{"id": 123456789},
			"chat":       map[string]interface{}{"id": 123456789, "type": "private"},
			"document": map[string]interface{}{
				"file_name": "vendor_invoice_2024_" + timestamp + ".pdf",
				"mime_type": "application/pdf",
				"file_id":   "BQACAgQAAxkBAAIC",
			},
		},
	}
	body, _ := json.Marshal(update)

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode, "Invoice document should be accepted")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "accepted", respBody["status"])
}

// TestTelegramInvalidJSONRejected tests that invalid JSON is rejected with 400
func TestTelegramInvalidJSONRejected(t *testing.T) {
	app, teardown := setupTelegramTestApp(t)
	defer teardown()

	req := httptest.NewRequest("POST", "/webhooks/telegram", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")

	resp, err := app.Test(req)
	require.NoError(t, err)
	assert.Equal(t, 400, resp.StatusCode, "Invalid JSON should be rejected")

	// Verify response body
	var respBody map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&respBody)
	require.NoError(t, err)
	assert.Equal(t, "invalid_json", respBody["error"])
}
