package web

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"

	"iterateswarm-core/internal/db"
)

// Controller handles web interface requests
type Controller struct {
	repo *db.Repository
}

// NewController creates a new web controller
func NewController(repo *db.Repository) *Controller {
	return &Controller{
		repo: repo,
	}
}

// RegisterRoutes registers web interface routes
func (c *Controller) RegisterRoutes(app *fiber.App) {
	// Public routes
	app.Get("/", c.handleIndex)
	app.Get("/dashboard", c.handleDashboard)

	// Protected routes would go here
	// app.Get("/protected", middleware.RequireAuth, c.handleProtected)
}

// handleIndex handles the home page
func (c *Controller) handleIndex(ctx *fiber.Ctx) error {
	data := map[string]interface{}{
		"Title": "IterateSwarm - Home",
		"Year":  time.Now().Year(),
		"User":  nil, // Will be populated by auth middleware in the future
	}

	return Render(ctx, "base", data)
}

// handleDashboard handles the dashboard page
func (c *Controller) handleDashboard(ctx *fiber.Ctx) error {
	// Get dashboard stats
	stats, err := c.getDashboardStats(ctx.Context())
	if err != nil {
		// Log error but continue with empty stats
		stats = map[string]interface{}{
			"pending_feedback":   0,
			"processed_feedback": 0,
			"draft_issues":       0,
			"published_issues":   0,
		}
	}

	// Get recent feedback
	feedback, err := c.getRecentFeedback(ctx.Context())
	if err != nil {
		// Log error but continue with empty feedback
		feedback = []map[string]interface{}{}
	}

	data := map[string]interface{}{
		"Title":    "IterateSwarm - Dashboard",
		"Year":     time.Now().Year(),
		"User":     nil, // Will be populated by auth middleware in the future
		"Stats":    stats,
		"Feedback": feedback,
	}

	return Render(ctx, "dashboard", data)
}

// getDashboardStats gets dashboard statistics from the database
func (c *Controller) getDashboardStats(ctx context.Context) (map[string]interface{}, error) {
	// This is a simplified version - in a real implementation, we'd have specific queries
	// for getting aggregated statistics

	// Get all feedback to count by status
	feedback, err := c.repo.ListFeedback(ctx, db.ListFeedbackParams{
		Limit:  100, // Reasonable limit for counting
		Offset: 0,
	})
	if err != nil {
		return nil, err
	}

	// Count feedback by status
	pendingCount := 0
	processedCount := 0
	for _, fb := range feedback {
		switch fb.Status {
		case "pending":
			pendingCount++
		case "processed":
			processedCount++
		}
	}

	// Get all issues to count by status
	issues, err := c.repo.ListIssues(ctx, db.ListIssuesParams{
		Limit:  100,
		Offset: 0,
	})
	if err != nil {
		return nil, err
	}

	draftCount := 0
	publishedCount := 0
	for _, issue := range issues {
		switch issue.Status {
		case "draft":
			draftCount++
		case "published":
			publishedCount++
		}
	}

	stats := map[string]interface{}{
		"pending_feedback":   pendingCount,
		"processed_feedback": processedCount,
		"draft_issues":       draftCount,
		"published_issues":   publishedCount,
	}

	return stats, nil
}

// getRecentFeedback gets recent feedback items
func (c *Controller) getRecentFeedback(ctx context.Context) ([]map[string]interface{}, error) {
	feedback, err := c.repo.ListFeedback(ctx, db.ListFeedbackParams{
		Limit:  10, // Get last 10 feedback items
		Offset: 0,
	})
	if err != nil {
		return nil, err
	}

	result := make([]map[string]interface{}, len(feedback))
	for i, fb := range feedback {
		createdAt := fb.CreatedAt.Time.Format(time.RFC3339) // Access the Time field of Timestamptz
		result[i] = map[string]interface{}{
			"id":         fb.ID,
			"title":      extractTitle(fb.Content),
			"source":     fb.Source,
			"status":     fb.Status,
			"created_at": createdAt,
		}
	}

	return result, nil
}

// extractTitle extracts a title from feedback content
func extractTitle(content string) string {
	// For now, just take the first 50 characters and remove newlines
	if len(content) > 50 {
		content = content[:50] + "..."
	}
	return content
}
