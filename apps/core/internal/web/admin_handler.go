package web

import (
	"bufio"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
)

// AdminDashboard serves the main admin dashboard
func (h *Handler) AdminDashboard(c *fiber.Ctx) error {
	return Render(c, "admin-dashboard", fiber.Map{
		"Title":       "Admin Dashboard",
		"ActivePanel": "dashboard",
	})
}

// AdminLiveFeed serves the live feed panel
func (h *Handler) AdminLiveFeed(c *fiber.Ctx) error {
	return Render(c, "admin-live-feed", fiber.Map{
		"Title":       "Live Feed",
		"ActivePanel": "live-feed",
	})
}

// AdminTaskBoard serves the task board panel
func (h *Handler) AdminTaskBoard(c *fiber.Ctx) error {
	return Render(c, "admin-task-board", fiber.Map{
		"Title":       "Task Board",
		"ActivePanel": "task-board",
	})
}

// AdminAgentMap serves the agent map panel
func (h *Handler) AdminAgentMap(c *fiber.Ctx) error {
	return Render(c, "admin-agent-map", fiber.Map{
		"Title":       "Agent Map",
		"ActivePanel": "agent-map",
	})
}

// AdminHITLQueue serves the HITL queue panel
func (h *Handler) AdminHITLQueue(c *fiber.Ctx) error {
	return Render(c, "admin-hitl-queue", fiber.Map{
		"Title":       "HITL Queue",
		"ActivePanel": "hitl-queue",
	})
}

// AdminConfig serves the config panel
func (h *Handler) AdminConfig(c *fiber.Ctx) error {
	return Render(c, "admin-config", fiber.Map{
		"Title":       "Configuration",
		"ActivePanel": "config",
	})
}

// AdminTelemetry serves the telemetry panel
func (h *Handler) AdminTelemetry(c *fiber.Ctx) error {
	return Render(c, "admin-telemetry", fiber.Map{
		"Title":       "Telemetry",
		"ActivePanel": "telemetry",
	})
}

// API: Get active tasks count
func (h *Handler) APIActiveTasks(c *fiber.Ctx) error {
	// TODO: Get from Redis/Temporal
	return c.SendString("0")
}

// API: Get pending HITL count
func (h *Handler) APIPendingHITL(c *fiber.Ctx) error {
	// TODO: Get from Redis
	return c.SendString("0")
}

// API: Get completed tasks count
func (h *Handler) APICompletedTasks(c *fiber.Ctx) error {
	// TODO: Get from database
	return c.SendString("0")
}

// API: Get token usage
func (h *Handler) APITokenUsage(c *fiber.Ctx) error {
	// TODO: Get from TokenBudgetManager
	return c.SendString("0 / 100K")
}

// API: Get recent activity
func (h *Handler) APIRecentActivity(c *fiber.Ctx) error {
	// Return HTML for recent activity
	html := `<div class="p-4 text-center text-gray-500">No recent activity</div>`
	return c.SendString(html)
}

// API: SSE events endpoint
func (h *Handler) APIEvents(c *fiber.Ctx) error {
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")

	c.Context().SetBodyStreamWriter(func(w *bufio.Writer) {
		// Send initial connection message
		fmt.Fprintf(w, "event: connected\ndata: {\"status\":\"connected\"}\n\n")
		w.Flush()

		// Keep connection alive with heartbeat
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				fmt.Fprintf(w, "event: heartbeat\ndata: {}\n\n")
				w.Flush()
			case <-c.Context().Done():
				return
			}
		}
	})

	return nil
}

// API: Get tasks for task board
func (h *Handler) APITasks(c *fiber.Ctx) error {
	// Return HTML for task columns
	html := `
		<div class="space-y-3">
			<div class="bg-white p-3 rounded shadow cursor-pointer hover:shadow-md" onclick="showTaskDetail('task-1')">
				<p class="font-medium text-sm">Sample Task</p>
				<p class="text-xs text-gray-500 mt-1">Waiting for processing...</p>
			</div>
		</div>
	`
	return c.SendString(html)
}

// API: Get agent status
func (h *Handler) APIAgentStatus(c *fiber.Ctx) error {
	agents := []struct {
		Name         string
		Status       string
		StatusColor  string
		CurrentTask  string
		LastActivity string
	}{
		{"Supervisor", "idle", "bg-green-100 text-green-800", "-", "2m ago"},
		{"Researcher", "idle", "bg-gray-100 text-gray-800", "-", "5m ago"},
		{"SRE", "idle", "bg-gray-100 text-gray-800", "-", "10m ago"},
		{"SWE", "idle", "bg-gray-100 text-gray-800", "-", "15m ago"},
		{"Reviewer", "idle", "bg-gray-100 text-gray-800", "-", "20m ago"},
	}

	html := ""
	for _, agent := range agents {
		html += fmt.Sprintf(`
			<tr>
				<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">%s</td>
				<td class="px-6 py-4 whitespace-nowrap"><span class="px-2 py-1 text-xs rounded-full %s">%s</span></td>
				<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">%s</td>
				<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">%s</td>
				<td class="px-6 py-4 whitespace-nowrap text-sm">
					<button onclick="showAgentDetails('%s')" class="text-indigo-600 hover:text-indigo-900">Details</button>
				</td>
			</tr>
		`, agent.Name, agent.StatusColor, agent.Status, agent.CurrentTask, agent.LastActivity, agent.Name)
	}

	return c.SendString(html)
}

// API: Get HITL queue
func (h *Handler) APIHITLQueue(c *fiber.Ctx) error {
	html := `<div class="p-8 text-center text-gray-500">No items awaiting approval</div>`
	return c.SendString(html)
}

// API: Approve HITL item
func (h *Handler) APIHITLApprove(c *fiber.Ctx) error {
	taskID := c.Params("id")
	// TODO: Process approval
	return c.SendString(fmt.Sprintf(`<div class="p-4 bg-green-50 text-green-800">Approved %s</div>`, taskID))
}

// API: Reject HITL item
func (h *Handler) APIHITLReject(c *fiber.Ctx) error {
	taskID := c.Params("id")
	// TODO: Process rejection
	return c.SendString(fmt.Sprintf(`<div class="p-4 bg-red-50 text-red-800">Rejected %s</div>`, taskID))
}

// API: Save agent config
func (h *Handler) APIConfigAgents(c *fiber.Ctx) error {
	return c.SendString(`<div class="p-3 bg-green-50 text-green-800 rounded">Agent settings saved</div>`)
}

// API: Save budget config
func (h *Handler) APIConfigBudget(c *fiber.Ctx) error {
	return c.SendString(`<div class="p-3 bg-green-50 text-green-800 rounded">Budget settings saved</div>`)
}

// API: Get telemetry stats
func (h *Handler) APITelemetryStats(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"error_rate":    "0.1%",
		"avg_response":  "245ms",
		"traces_min":    "120",
		"log_volume":    "5.2K/min",
	})
}

// RegisterAdminRoutes registers all admin routes
func (h *Handler) RegisterAdminRoutes(app *fiber.App) {
	// Admin pages
	app.Get("/admin", h.AdminDashboard)
	app.Get("/admin/live-feed", h.AdminLiveFeed)
	app.Get("/admin/task-board", h.AdminTaskBoard)
	app.Get("/admin/agent-map", h.AdminAgentMap)
	app.Get("/admin/hitl-queue", h.AdminHITLQueue)
	app.Get("/admin/config", h.AdminConfig)
	app.Get("/admin/telemetry", h.AdminTelemetry)

	// API endpoints
	api := app.Group("/api/admin")

	// Dashboard stats
	api.Get("/stats/active-tasks", h.APIActiveTasks)
	api.Get("/stats/pending-hitl", h.APIPendingHITL)
	api.Get("/stats/completed", h.APICompletedTasks)
	api.Get("/stats/tokens", h.APITokenUsage)
	api.Get("/recent-activity", h.APIRecentActivity)

	// Live feed
	api.Get("/events", h.APIEvents)
	api.Get("/event-stats", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"supervisor": 0,
			"researcher": 0,
			"sre":        0,
			"swe":        0,
			"reviewer":   0,
		})
	})

	// Task board
	api.Get("/tasks", h.APITasks)
	api.Get("/tasks/:id", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-4">Task details for ` + c.Params("id") + `</div>`)
	})

	// Agent map
	api.Get("/agent-status", h.APIAgentStatus)
	api.Get("/agent-topology", func(c *fiber.Ctx) error {
		return c.SendString("") // SVG updated via HTMX
	})
	api.Get("/agents/:agent/details", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-4">Details for ` + c.Params("agent") + `</div>`)
	})

	// HITL queue
	api.Get("/hitl/count", h.APIPendingHITL)
	api.Get("/hitl/queue", h.APIHITLQueue)
	api.Get("/hitl/history", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-4 text-center text-gray-500">No history</div>`)
	})
	api.Get("/hitl/:id/details", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-4">Details for ` + c.Params("id") + `</div>`)
	})
	api.Post("/hitl/:id/approve", h.APIHITLApprove)
	api.Post("/hitl/:id/reject", h.APIHITLReject)
	api.Post("/hitl/approve-all", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-4 bg-green-50 text-green-800">All items approved</div>`)
	})

	// Config
	api.Post("/config/agents", h.APIConfigAgents)
	api.Post("/config/budget", h.APIConfigBudget)
	api.Post("/config/reload", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-3 bg-green-50 text-green-800 rounded">Configuration reloaded</div>`)
	})
	api.Get("/config/llm-status", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"calls":   42,
			"tokens":  "15.2K",
			"latency": "180ms",
		})
	})

	// Telemetry
	api.Get("/telemetry/stats", h.APITelemetryStats)
	api.Get("/telemetry/signoz-summary", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"services": 5,
			"errors":   2,
			"p99":      "320ms",
		})
	})
	api.Get("/telemetry/hyperdx-summary", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="p-3 bg-gray-50 rounded text-sm font-mono">No recent logs</div>`)
	})
	api.Get("/telemetry/agent-chart", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="text-gray-400">Chart data loading...</div>`)
	})
	api.Get("/telemetry/token-usage", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="text-gray-400">Loading token usage...</div>`)
	})
	api.Get("/telemetry/task-distribution", func(c *fiber.Ctx) error {
		return c.SendString(`<div class="text-gray-400">Loading distribution...</div>`)
	})
}