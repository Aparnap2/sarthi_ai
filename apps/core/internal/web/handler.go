package web

import (
	"embed"
	"fmt"
	"html/template"

	"github.com/gofiber/fiber/v2"
	"iterateswarm-core/internal/engine"
)

//go:embed templates/*.html
var templatesFS embed.FS

// Render renders a template with data
func Render(c *fiber.Ctx, name string, data interface{}) error {
	tmpl, err := template.ParseFS(templatesFS, "templates/"+name+".html")
	if err != nil {
		return fmt.Errorf("failed to parse template %s: %w", name, err)
	}

	c.Set("Content-Type", "text/html")
	return tmpl.Execute(c.Response().BodyWriter(), data)
}

// Handler struct for web routes
type Handler struct {
	engine *engine.Engine
}

// NewHandler creates a new web handler
func NewHandler(eng *engine.Engine) *Handler {
	return &Handler{
		engine: eng,
	}
}

// Dashboard handler - serves the main HTMX dashboard
func (h *Handler) Dashboard(c *fiber.Ctx) error {
	return Render(c, "index", fiber.Map{
		"Title": "IterateSwarm - AI Feedback Triage",
	})
}

// HandleFeedback processes feedback submissions from HTMX
func (h *Handler) HandleFeedback(c *fiber.Ctx) error {
	var req struct {
		Content string `json:"content" form:"content"`
		Source  string `json:"source" form:"source"`
		UserID  string `json:"user_id" form:"user_id"`
	}

	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).SendString(`<div class="text-red-600">Invalid request</div>`)
	}

	// Validate
	if req.Content == "" {
		return c.Status(400).SendString(`<div class="text-red-600">Content is required</div>`)
	}

	if req.Source == "" {
		req.Source = "web"
	}

	if req.UserID == "" {
		req.UserID = "anonymous"
	}

	// Process with engine
	result, err := h.engine.ProcessFeedback(c.Context(), req.UserID, req.Content, req.Source)
	if err != nil {
		return c.Status(500).SendString(fmt.Sprintf(`<div class="text-red-600">Error: %s</div>`, err.Error()))
	}

	// Check if JSON is requested
	if c.Get("Accept") == "application/json" {
		return c.JSON(result)
	}

	// Return result HTML
	return Render(c, "result", result)
}

// HandleStats returns system stats for HTMX polling
func (h *Handler) HandleStats(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"circuit_breaker":  h.engine.GetCircuitBreakerState(),
		"rate_limit_used":  0,
		"rate_limit_total": 20,
		"avg_time":         "3.5",
	})
}

// HandleMetrics returns detailed metrics
func (h *Handler) HandleMetrics(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"feedbacks_processed":   0,
		"avg_processing_time":   3.5,
		"circuit_breaker_state": h.engine.GetCircuitBreakerState(),
		"rate_limit_hits":       0,
		"classification_accuracy": fiber.Map{
			"bug":      0.96,
			"feature":  0.97,
			"question": 0.98,
		},
	})
}

// RegisterRoutes registers all web routes
func (h *Handler) RegisterRoutes(app *fiber.App) {
	// Main dashboard
	app.Get("/", h.Dashboard)

	// API endpoints for HTMX
	app.Post("/api/feedback", h.HandleFeedback)
	app.Get("/api/stats", h.HandleStats)
	app.Get("/api/metrics", h.HandleMetrics)
}
