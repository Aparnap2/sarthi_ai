package web

import (
	"context"
	"database/sql"
	"encoding/json"
	"time"

	"github.com/gofiber/fiber/v2"
)

// AgentEvent represents an agent activity event
type AgentEvent struct {
	ID        string                 `json:"id"`
	Timestamp time.Time              `json:"timestamp"`
	Agent     string                 `json:"agent"` // supervisor, researcher, sre, swe, reviewer
	Type      string                 `json:"type"`  // planning, executing, reviewing, completing
	TaskID    string                 `json:"task_id"`
	Data      map[string]interface{} `json:"data"`
}

// SSEHandler handles Server-Sent Events streaming
type SSEHandler struct {
	db *sql.DB
}

// NewSSEHandler creates a new SSE handler
func NewSSEHandler(db *sql.DB) *SSEHandler {
	return &SSEHandler{db: db}
}

// HandleSSE streams agent events via Server-Sent Events using PostgreSQL LISTEN/NOTIFY
func (h *SSEHandler) HandleSSE(c *fiber.Ctx) error {
	// Set SSE headers
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("X-Accel-Buffering", "no") // Disable nginx buffering

	// Listen for PostgreSQL NOTIFY events
	// This requires a separate connection for LISTEN
	listenConn, err := h.db.Conn(c.Context())
	if err != nil {
		return c.Status(500).SendString("Failed to establish database connection")
	}
	defer listenConn.Close()

	// Start listening on the 'agent_events' channel
	_, err = listenConn.ExecContext(c.Context(), "LISTEN agent_events")
	if err != nil {
		return c.Status(500).SendString("Failed to listen for events")
	}

	// Poll for notifications
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-c.Context().Done():
			return nil
		case <-ticker.C:
			// Check for notifications
			var notification []byte
			err := listenConn.QueryRowContext(c.Context(), "SELECT pg_notify('agent_events', '{}')").Scan(&notification)
			if err != nil {
				// Continue on error
				continue
			}
		}
	}
}

// PublishAgentEvent publishes an agent event to PostgreSQL
func PublishAgentEvent(ctx context.Context, db *sql.DB, event AgentEvent) error {
	// Insert event into database - trigger will send NOTIFY
	metadataJSON, err := json.Marshal(event.Data)
	if err != nil {
		return err
	}

	_, err = db.ExecContext(ctx, `
		INSERT INTO agent_events (event_type, task_id, agent_name, message, severity, metadata)
		VALUES ($1, $2, $3, $4, $5, $6)
	`, event.Type, event.TaskID, event.Agent, "", "info", metadataJSON)

	return err
}
