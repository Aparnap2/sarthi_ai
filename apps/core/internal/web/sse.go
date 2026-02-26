package web

import (
	"context"
	"encoding/json"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
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
	redis *redis.Client
}

// NewSSEHandler creates a new SSE handler
func NewSSEHandler(redisClient *redis.Client) *SSEHandler {
	return &SSEHandler{redis: redisClient}
}

// HandleSSE streams agent events via Server-Sent Events
func (h *SSEHandler) HandleSSE(c *fiber.Ctx) error {
	// Set SSE headers
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")
	c.Set("X-Accel-Buffering", "no") // Disable nginx buffering

	ctx := c.Context()

	// Subscribe to Redis pub/sub
	pubsub := h.redis.Subscribe(ctx, "agent-events")
	defer pubsub.Close()

	channel := pubsub.Channel()

	// Stream events
	for {
		select {
		case msg := <-channel:
			// Validate JSON before forwarding
			var event AgentEvent
			if err := json.Unmarshal([]byte(msg.Payload), &event); err != nil {
				continue
			}

			// Format: data: {"id":"...", "agent":"swe", ...}
			c.SendString("data: " + msg.Payload + "\n\n")

		case <-ctx.Done():
			return nil
		}
	}
}

// PublishAgentEvent publishes an agent event to Redis pub/sub
func PublishAgentEvent(ctx context.Context, redisClient *redis.Client, event AgentEvent) error {
	data, err := json.Marshal(event)
	if err != nil {
		return err
	}

	return redisClient.Publish(ctx, "agent-events", string(data)).Err()
}
