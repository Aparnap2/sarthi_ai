// Package main implements the SwarmChat service - a Discord replacement for IterateSwarm OS.
// It provides real-time chat functionality with Human-in-the-Loop (HITL) approval workflows.
//
// Features:
//   - Real-time messaging via Server-Sent Events (SSE)
//   - PostgreSQL LISTEN/NOTIFY for event streaming
//   - HITL approval/rejection for Temporal workflows
//   - HTMX-based UI for lightweight frontend
//
// Usage:
//
//	export POSTGRES_URL=postgres://user:pass@localhost:5432/db?sslmode=disable
//	export TEMPORAL_ADDRESS=localhost:7233
//	go run cmd/server/main.go
package main

import (
	"bufio"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/template/html/v2"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"go.temporal.io/sdk/client"
)

// Message represents a chat message in the system.
type Message struct {
	ID        uuid.UUID              `json:"id"`
	ChannelID uuid.UUID              `json:"channel_id"`
	UserID    string                 `json:"user_id"`
	Content   string                 `json:"content"`
	Source    string                 `json:"source"` // 'user' | 'swarm' | 'system'
	Metadata  map[string]interface{} `json:"metadata"`
	CreatedAt time.Time              `json:"created_at"`
}

var (
	db             *sql.DB
	temporalClient client.Client
)

func main() {
	// Database connection
	pgURL := os.Getenv("POSTGRES_URL")
	if pgURL == "" {
		pgURL = "postgres://iterateswarm:iterateswarm@localhost:5433/iterateswarm?sslmode=disable"
	}

	var err error
	db, err = sql.Open("postgres", pgURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	// Test database connection
	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Connected to PostgreSQL")

	// Temporal connection
	temporalAddr := os.Getenv("TEMPORAL_ADDRESS")
	if temporalAddr == "" {
		temporalAddr = "localhost:7233"
	}

	temporalClient, err = client.Dial(client.Options{
		HostPort: temporalAddr,
	})
	if err != nil {
		log.Printf("Warning: Failed to connect to Temporal: %v (HITL features will be limited)", err)
		// Don't fail - allow running without Temporal for development
	} else {
		defer temporalClient.Close()
		log.Println("Connected to Temporal")
	}

	// Run migrations
	runMigrations()

	// Fiber app with template engine
	engine := html.New(filepath.Join(".", "internal", "templates"), ".html")
	app := fiber.New(fiber.Config{
		Views:     engine,
		AppName:   "SwarmChat/1.0.0",
		BodyLimit: 4 * 1024 * 1024, // 4MB limit
	})

	// Middleware
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,PUT,DELETE,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept,Authorization",
	}))

	// Request logging
	app.Use(func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		log.Printf("[%s] %s %s - %d - %dms",
			c.Method(), c.Path(), c.IP(), c.Response().StatusCode(),
			time.Since(start).Milliseconds(),
		)
		return err
	})

	// Routes
	app.Get("/", handleChatUI)
	app.Get("/channels/:id/stream", handleSSEStream)
	app.Post("/channels/:id/messages", handleCreateMessage)
	app.Get("/channels/:id/messages", handleListMessages)
	app.Post("/hitl/:workflow_id/approve", handleHITLApprove)
	app.Post("/hitl/:workflow_id/reject", handleHITLReject)

	// Health check
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":    "healthy",
			"timestamp": time.Now().Format(time.RFC3339),
			"service":   "swarm-chat",
		})
	})

	log.Println("🐝 SwarmChat starting on port 4000...")
	log.Fatal(app.Listen(":4000"))
}

// runMigrations initializes the database schema.
func runMigrations() {
	migrations := []struct {
		name string
		sql  string
	}{
		{
			name: "create_channels_table",
			sql: `CREATE TABLE IF NOT EXISTS channels (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				name VARCHAR(100) NOT NULL UNIQUE,
				created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
			)`,
		},
		{
			name: "create_messages_table",
			sql: `CREATE TABLE IF NOT EXISTS messages (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
				user_id VARCHAR(100) NOT NULL,
				content TEXT NOT NULL,
				source VARCHAR(50) DEFAULT 'user',
				metadata JSONB DEFAULT '{}',
				created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
			)`,
		},
		{
			name: "create_messages_channel_idx",
			sql: `CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id)`,
		},
		{
			name: "create_messages_created_idx",
			sql: `CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC)`,
		},
		{
			name: "create_notify_function",
			sql: `CREATE OR REPLACE FUNCTION notify_new_message()
			RETURNS TRIGGER AS $$
			BEGIN
				PERFORM pg_notify('chat_events',
					json_build_object(
						'channel_id', NEW.channel_id,
						'message_id', NEW.id,
						'content',    NEW.content,
						'source',     NEW.source,
						'metadata',   NEW.metadata
					)::text);
				RETURN NEW;
			END;
			$$ LANGUAGE plpgsql`,
		},
		{
			name: "create_message_trigger",
			sql: `DROP TRIGGER IF EXISTS message_notify ON messages;
			CREATE TRIGGER message_notify
			AFTER INSERT ON messages
			FOR EACH ROW EXECUTE FUNCTION notify_new_message()`,
		},
	}

	for _, m := range migrations {
		if _, err := db.Exec(m.sql); err != nil {
			log.Printf("Migration warning [%s]: %v", m.name, err)
		} else {
			log.Printf("Migration applied: %s", m.name)
		}
	}

	// Create default channel
	_, err := db.Exec(`INSERT INTO channels (name) VALUES ('feedback') ON CONFLICT (name) DO NOTHING`)
	if err != nil {
		log.Printf("Warning: Could not create default channel: %v", err)
	} else {
		log.Println("Default channel 'feedback' created")
	}
}

// handleChatUI renders the main chat interface.
func handleChatUI(c *fiber.Ctx) error {
	// Get channel ID from query param or use default
	channelID := c.Query("channel", "feedback")
	return c.Render("chat", fiber.Map{
		"ChannelID":   channelID,
		"ChannelName": channelID,
		"Title":       "SwarmChat - " + channelID,
	})
}

// handleSSEStream establishes a Server-Sent Events connection for real-time messaging.
func handleSSEStream(c *fiber.Ctx) error {
	channelIDStr := c.Params("id")
	channelID, err := uuid.Parse(channelIDStr)
	if err != nil {
		// Try to lookup by name
		var id uuid.UUID
		err := db.QueryRow("SELECT id FROM channels WHERE name = $1", channelIDStr).Scan(&id)
		if err != nil {
			return c.Status(404).JSON(fiber.Map{"error": "Channel not found"})
		}
		channelID = id
	}

	// Set SSE headers
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("X-Accel-Buffering", "no")

	listenCtx, cancel := context.WithCancel(c.Context())
	defer cancel()

	log.Printf("Client subscribed to channel %s", channelID)

	// Use SetBodyStreamWriter for proper streaming with flush
	c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
		// Send initial connection event
		sendSSE(w, "connected", fmt.Sprintf(`{"channel_id":"%s"}`, channelID))

		// Load recent messages
		recentMsgs, err := loadRecentMessages(channelID, 50)
		if err == nil && len(recentMsgs) > 0 {
			for _, msg := range recentMsgs {
				data, _ := json.Marshal(msg)
				sendSSE(w, "message", string(data))
			}
		}

		// Listen for new messages with polling
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()

		lastCheck := time.Now()

		for {
			select {
			case <-listenCtx.Done():
				log.Printf("Client disconnected from channel %s", channelID)
				return
			case <-ticker.C:
				// Poll for new messages since last check
				newMsgs, err := loadMessagesSince(channelID, lastCheck)
				if err == nil && len(newMsgs) > 0 {
					for _, msg := range newMsgs {
						data, _ := json.Marshal(msg)
						sendSSE(w, "message", string(data))
					}
					lastCheck = time.Now()
				} else {
					// Send heartbeat
					sendSSE(w, "heartbeat", fmt.Sprintf(`{"ts":"%s"}`, time.Now().Format(time.RFC3339)))
				}
			}
		}
	})

	return nil
}

// sendSSE sends a Server-Sent Event to the client.
func sendSSE(w *bufio.Writer, event string, data string) {
	fmt.Fprintf(w, "event: %s\ndata: %s\n\n", event, data)
	w.Flush()
}

// handleCreateMessage creates a new chat message.
func handleCreateMessage(c *fiber.Ctx) error {
	channelIDStr := c.Params("id")
	channelID, err := uuid.Parse(channelIDStr)
	if err != nil {
		// Try to lookup by name
		err := db.QueryRow("SELECT id FROM channels WHERE name = $1", channelIDStr).Scan(&channelID)
		if err != nil {
			return c.Status(404).JSON(fiber.Map{"error": "Channel not found"})
		}
	}

	var req struct {
		Content  string                 `json:"content"`
		UserID   string                 `json:"user_id"`
		Source   string                 `json:"source"`
		Metadata map[string]interface{} `json:"metadata"`
	}

	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	if req.Content == "" {
		return c.Status(400).JSON(fiber.Map{"error": "Content is required"})
	}

	if req.UserID == "" {
		req.UserID = "anonymous"
	}

	if req.Source == "" {
		req.Source = "user"
	}

	msg := Message{
		ID:        uuid.New(),
		ChannelID: channelID,
		UserID:    req.UserID,
		Content:   req.Content,
		Source:    req.Source,
		Metadata:  req.Metadata,
		CreatedAt: time.Now(),
	}

	if msg.Metadata == nil {
		msg.Metadata = make(map[string]interface{})
	}

	// Convert metadata to JSON for PostgreSQL
	metadataJSON, err := json.Marshal(msg.Metadata)
	if err != nil {
		log.Printf("Failed to marshal metadata: %v", err)
		metadataJSON = []byte("{}")
	}

	// Insert message and get DB-generated timestamp
	err = db.QueryRow(`
		INSERT INTO messages (id, channel_id, user_id, content, source, metadata)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING created_at
	`, msg.ID, msg.ChannelID, msg.UserID, msg.Content, msg.Source, metadataJSON).Scan(&msg.CreatedAt)

	if err != nil {
		log.Printf("Failed to create message: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to create message"})
	}

	log.Printf("Message created: %s in channel %s", msg.ID, channelID)

	return c.JSON(fiber.Map{
		"status":     "created",
		"message_id": msg.ID,
		"message":    msg,
	})
}

// handleListMessages returns recent messages for a channel.
func handleListMessages(c *fiber.Ctx) error {
	channelIDStr := c.Params("id")
	channelID, err := uuid.Parse(channelIDStr)
	if err != nil {
		// Try to lookup by name
		err := db.QueryRow("SELECT id FROM channels WHERE name = $1", channelIDStr).Scan(&channelID)
		if err != nil {
			return c.Status(404).JSON(fiber.Map{"error": "Channel not found"})
		}
	}

	limit := c.QueryInt("limit", 50)
	messages, err := loadRecentMessages(channelID, limit)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "Failed to load messages"})
	}

	return c.JSON(messages)
}

// loadRecentMessages fetches recent messages for a channel.
func loadRecentMessages(channelID uuid.UUID, limit int) ([]Message, error) {
	rows, err := db.Query(`
		SELECT id, channel_id, user_id, content, source, metadata, created_at
		FROM messages
		WHERE channel_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`, channelID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []Message
	for rows.Next() {
		var msg Message
		var metadataJSON []byte
		if err := rows.Scan(&msg.ID, &msg.ChannelID, &msg.UserID, &msg.Content, &msg.Source, &metadataJSON, &msg.CreatedAt); err != nil {
			log.Printf("Failed to scan message: %v", err)
			continue
		}
		if len(metadataJSON) > 0 {
			json.Unmarshal(metadataJSON, &msg.Metadata)
		}
		messages = append(messages, msg)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	// Reverse to get chronological order
	for i, j := 0, len(messages)-1; i < j; i, j = i+1, j-1 {
		messages[i], messages[j] = messages[j], messages[i]
	}

	return messages, nil
}

// loadMessagesSince fetches messages created after a given time.
func loadMessagesSince(channelID uuid.UUID, since time.Time) ([]Message, error) {
	rows, err := db.Query(`
		SELECT id, channel_id, user_id, content, source, metadata, created_at
		FROM messages
		WHERE channel_id = $1 AND created_at > $2
		ORDER BY created_at ASC
	`, channelID, since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []Message
	for rows.Next() {
		var msg Message
		var metadataJSON []byte
		if err := rows.Scan(&msg.ID, &msg.ChannelID, &msg.UserID, &msg.Content, &msg.Source, &metadataJSON, &msg.CreatedAt); err != nil {
			log.Printf("Failed to scan message: %v", err)
			continue
		}
		if len(metadataJSON) > 0 {
			json.Unmarshal(metadataJSON, &msg.Metadata)
		}
		messages = append(messages, msg)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return messages, nil
}

// handleHITLApprove handles Human-in-the-Loop approval for a workflow.
func handleHITLApprove(c *fiber.Ctx) error {
	workflowID := c.Params("workflow_id")

	if temporalClient == nil {
		return c.Status(503).JSON(fiber.Map{"error": "Temporal client not available"})
	}

	// Signal the workflow to approve
	err := temporalClient.SignalWorkflow(c.Context(), workflowID, "", "user-action", "approve")
	if err != nil {
		log.Printf("Failed to signal workflow approval: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to signal workflow"})
	}

	// Update message metadata to show approved
	_, err = db.Exec(`
		UPDATE messages 
		SET metadata = metadata || '{"action": "approved", "approved_at": $1}'::jsonb
		WHERE metadata->>'workflow_id' = $2
	`, time.Now().Format(time.RFC3339), workflowID)
	if err != nil {
		log.Printf("Failed to update message metadata: %v", err)
	}

	log.Printf("Workflow %s approved", workflowID)

	return c.JSON(fiber.Map{
		"status":      "approved",
		"workflow_id": workflowID,
		"timestamp":   time.Now().Format(time.RFC3339),
	})
}

// handleHITLReject handles Human-in-the-Loop rejection for a workflow.
func handleHITLReject(c *fiber.Ctx) error {
	workflowID := c.Params("workflow_id")

	if temporalClient == nil {
		return c.Status(503).JSON(fiber.Map{"error": "Temporal client not available"})
	}

	// Signal the workflow to reject
	err := temporalClient.SignalWorkflow(c.Context(), workflowID, "", "user-action", "reject")
	if err != nil {
		log.Printf("Failed to signal workflow rejection: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to signal workflow"})
	}

	// Update message metadata to show rejected
	_, err = db.Exec(`
		UPDATE messages 
		SET metadata = metadata || '{"action": "rejected", "rejected_at": $1}'::jsonb
		WHERE metadata->>'workflow_id' = $2
	`, time.Now().Format(time.RFC3339), workflowID)
	if err != nil {
		log.Printf("Failed to update message metadata: %v", err)
	}

	log.Printf("Workflow %s rejected", workflowID)

	return c.JSON(fiber.Map{
		"status":      "rejected",
		"workflow_id": workflowID,
		"timestamp":   time.Now().Format(time.RFC3339),
	})
}
