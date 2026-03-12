# HTMX Admin Panel Implementation Plan

**Date:** 2026-02-26  
**Status:** Week 0-4 Complete (146 tests)  
**Pivot:** React → HTMX (lighter, simpler, server-side rendered)

---

## Why HTMX Over React?

| Aspect | React | HTMX | Winner |
|--------|-------|------|--------|
| **Bundle Size** | ~130KB (React + dependencies) | ~14KB (htmx.js) | ✅ HTMX |
| **Complexity** | High (state management, hooks, etc.) | Low (HTML attributes) | ✅ HTMX |
| **Real-time** | Complex (EventSource + state) | Simple (`hx-sse` attribute) | ✅ HTMX |
| **Backend Integration** | API layer needed | Direct Go templates | ✅ HTMX |
| **Development Speed** | Slow (build, hot reload) | Fast (edit template, refresh) | ✅ HTMX |
| **Existing Code** | New implementation | Already exists! | ✅ HTMX |

---

## Existing HTMX Infrastructure

### Files Already Present

```
apps/core/internal/web/
├── handler.go              # Go web handlers
├── sse.go                  # SSE handler (already implemented!)
└── templates/
    ├── base.html           # Base template
    ├── index.html          # Dashboard (16KB!)
    ├── dashboard.html      # Dashboard content
    └── result.html         # Result display
```

### Current Features (Already Working!)

From `index.html` (16KB template):
- ✅ HTMX-powered feedback submission
- ✅ Real-time result display
- ✅ SSE integration ready
- ✅ Go template rendering
- ✅ Tailwind CSS styling

---

## Week 4 HTMX Implementation (Revised)

### Panel 1: Live Feed (SSE Streaming)

**File:** `apps/core/internal/web/templates/live_feed.html`

```html
<!-- Embed in dashboard.html -->
<div class="card">
    <div class="card-header">
        <h3>📡 Live Agent Feed</h3>
    </div>
    <div class="card-content"
         hx-ext="sse"
         sse-connect="/api/stream/events"
         sse-swap="message">
        <!-- Events will be streamed here in real-time -->
        <div id="event-stream">
            <!-- SSE events will append here -->
        </div>
    </div>
</div>
```

**Go SSE Handler** (already exists in `sse.go`):
```go
func (h *SSEHandler) HandleSSE(c *fiber.Ctx) error {
    c.Set("Content-Type", "text/event-stream")
    c.Set("Cache-Control", "no-cache")
    c.Set("Connection", "keep-alive")
    
    pubsub := h.redis.Subscribe(c.Context(), "agent-events")
    channel := pubsub.Channel()
    
    for {
        select {
        case msg := <-channel:
            // Send SSE event
            c.Write([]byte("event: message\n"))
            c.Write([]byte("data: " + msg.Payload + "\n\n"))
            c.Flush()
        case <-c.Context().Done():
            return nil
        }
    }
}
```

**Route Registration:**
```go
// In apps/core/internal/web/handler.go
app.Get("/api/stream/events", sseHandler.HandleSSE)
```

---

### Panel 2: HITL Queue (HTMX Polling)

**File:** `apps/core/internal/web/templates/hitl_queue.html`

```html
<div class="card">
    <div class="card-header">
        <h3>✅ HITL Approval Queue</h3>
    </div>
    <div class="card-content"
         hx-get="/api/approvals/pending"
         hx-trigger="every 5s"
         id="hitl-queue">
        <!-- Pending approvals loaded via polling -->
        {{range .Approvals}}
        <div class="approval-item">
            <h4>PR #{{.PRNumber}}: {{.Title}}</h4>
            <p>{{.Reasoning}}</p>
            <div class="confidence">
                Confidence: {{.Confidence}}%
            </div>
            <div class="actions">
                <button class="btn-approve"
                        hx-post="/api/approvals/{{.ID}}/approve"
                        hx-target="#hitl-queue">
                    Approve
                </button>
                <button class="btn-reject"
                        hx-post="/api/approvals/{{.ID}}/reject"
                        hx-target="#hitl-queue">
                    Reject
                </button>
            </div>
        </div>
        {{else}}
        <p class="empty-state">No pending approvals</p>
        {{end}}
    </div>
</div>
```

**Go Handler:**
```go
func (h *Handler) GetPendingApprovals(c *fiber.Ctx) error {
    approvals := h.engine.GetPendingApprovals()
    return Render(c, "hitl_queue", fiber.Map{
        "Approvals": approvals,
    })
}

func (h *Handler) ApprovePR(c *fiber.Ctx) error {
    id := c.Params("id")
    h.engine.Approve(id, true)
    // Return updated list
    return h.GetPendingApprovals(c)
}

func (h *Handler) RejectPR(c *fiber.Ctx) error {
    id := c.Params("id")
    h.engine.Approve(id, false)
    return h.GetPendingApprovals(c)
}
```

---

### Panel 3: Agent Map (Static Visualization)

**File:** `apps/core/internal/web/templates/agent_map.html`

```html
<div class="card">
    <div class="card-header">
        <h3>🗺️ Agent Topology</h3>
    </div>
    <div class="card-content">
        <svg viewBox="0 0 800 400" class="agent-map">
            <!-- Supervisor (center) -->
            <g class="agent-node supervisor"
               hx-get="/api/agents/supervisor/status"
               hx-trigger="every 3s">
                <circle cx="400" cy="200" r="50" fill="#8B5CF6"/>
                <text x="400" y="205" text-anchor="middle" fill="white">
                    Supervisor
                </text>
            </g>
            
            <!-- Researcher -->
            <g class="agent-node researcher"
               hx-get="/api/agents/researcher/status"
               hx-trigger="every 3s">
                <circle cx="200" cy="100" r="40" fill="#3B82F6"/>
                <text x="200" y="105" text-anchor="middle" fill="white">
                    Researcher
                </text>
            </g>
            
            <!-- SRE -->
            <g class="agent-node sre"
               hx-get="/api/agents/sre/status"
               hx-trigger="every 3s">
                <circle cx="600" cy="100" r="40" fill="#EF4444"/>
                <text x="600" y="105" text-anchor="middle" fill="white">
                    SRE
                </text>
            </g>
            
            <!-- SWE -->
            <g class="agent-node swe"
               hx-get="/api/agents/swe/status"
               hx-trigger="every 3s">
                <circle cx="200" cy="300" r="40" fill="#10B981"/>
                <text x="200" y="305" text-anchor="middle" fill="white">
                    SWE
                </text>
            </g>
            
            <!-- Reviewer -->
            <g class="agent-node reviewer"
               hx-get="/api/agents/reviewer/status"
               hx-trigger="every 3s">
                <circle cx="600" cy="300" r="40" fill="#F59E0B"/>
                <text x="600" y="305" text-anchor="middle" fill="white">
                    Reviewer
                </text>
            </g>
            
            <!-- Connections -->
            <line x1="400" y1="200" x2="200" y2="100" stroke="#ccc" stroke-width="2"/>
            <line x1="400" y1="200" x2="600" y2="100" stroke="#ccc" stroke-width="2"/>
            <line x1="400" y1="200" x2="200" y2="300" stroke="#ccc" stroke-width="2"/>
            <line x1="400" y1="200" x2="600" y2="300" stroke="#ccc" stroke-width="2"/>
        </svg>
    </div>
</div>
```

---

### Panel 4: Task Board (Kanban)

**File:** `apps/core/internal/web/templates/task_board.html`

```html
<div class="card">
    <div class="card-header">
        <h3>📋 Task Board</h3>
    </div>
    <div class="card-content">
        <div class="kanban-board">
            <!-- Queued Column -->
            <div class="kanban-column">
                <h4>Queued</h4>
                <div class="kanban-items"
                     hx-get="/api/tasks/queued"
                     hx-trigger="every 10s">
                    {{range .Queued}}
                    <div class="kanban-item">{{.TaskID}}</div>
                    {{end}}
                </div>
            </div>
            
            <!-- Analyzing Column -->
            <div class="kanban-column">
                <h4>Analyzing</h4>
                <div class="kanban-items"
                     hx-get="/api/tasks/analyzing"
                     hx-trigger="every 10s">
                    {{range .Analyzing}}
                    <div class="kanban-item">{{.TaskID}}</div>
                    {{end}}
                </div>
            </div>
            
            <!-- Awaiting HITL Column -->
            <div class="kanban-column">
                <h4>Awaiting HITL</h4>
                <div class="kanban-items"
                     hx-get="/api/tasks/awaiting-hitl"
                     hx-trigger="every 10s">
                    {{range .AwaitingHITL}}
                    <div class="kanban-item">{{.TaskID}}</div>
                    {{end}}
                </div>
            </div>
            
            <!-- Completed Column -->
            <div class="kanban-column">
                <h4>Completed</h4>
                <div class="kanban-items"
                     hx-get="/api/tasks/completed"
                     hx-trigger="every 10s">
                    {{range .Completed}}
                    <div class="kanban-item">{{.TaskID}}</div>
                    {{end}}
                </div>
            </div>
        </div>
    </div>
</div>
```

---

### Panel 5: Config Panel

**File:** `apps/core/internal/web/templates/config_panel.html`

```html
<div class="card">
    <div class="card-header">
        <h3>⚙️ Configuration</h3>
    </div>
    <div class="card-content">
        <form hx-post="/api/config/save"
              hx-target="#config-status"
              class="config-form">
            <div class="form-group">
                <label>Token Budget (max tokens per task)</label>
                <input type="number"
                       name="max_tokens_per_task"
                       value="{{.Config.MaxTokensPerTask}}"/>
            </div>
            
            <div class="form-group">
                <label>Max Concurrent Tasks</label>
                <input type="number"
                       name="max_concurrent_tasks"
                       value="{{.Config.MaxConcurrentTasks}}"/>
            </div>
            
            <div class="form-group">
                <label>Context Window (max tokens)</label>
                <input type="number"
                       name="context_window_max_tokens"
                       value="{{.Config.ContextWindowMaxTokens}}"/>
            </div>
            
            <button type="submit" class="btn-primary">
                Save Configuration
            </button>
        </form>
        
        <div id="config-status"></div>
    </div>
</div>
```

---

### Panel 6: Telemetry Panel

**File:** `apps/core/internal/web/templates/telemetry_panel.html`

```html
<div class="card">
    <div class="card-header">
        <h3>📊 Telemetry</h3>
    </div>
    <div class="card-content">
        <div class="tabs">
            <button class="tab-btn active"
                    hx-get="/api/telemetry/signoz"
                    hx-target="#telemetry-content">
                SigNoz
            </button>
            <button class="tab-btn"
                    hx-get="/api/telemetry/hyperdx"
                    hx-target="#telemetry-content">
                HyperDX
            </button>
            <button class="tab-btn"
                    hx-get="/api/telemetry/metrics"
                    hx-target="#telemetry-content">
                Metrics
            </button>
        </div>
        
        <div id="telemetry-content"
             hx-get="/api/telemetry/signoz"
             hx-trigger="load">
            <!-- Telemetry data loaded here -->
        </div>
    </div>
</div>
```

---

## Go Handlers to Implement

**File:** `apps/core/internal/web/handler.go`

```go
// Add these handlers to existing Handler struct

// Live Feed (SSE already exists)
func (h *Handler) GetLiveFeed(c *fiber.Ctx) error {
    return Render(c, "live_feed", nil)
}

// HITL Queue
func (h *Handler) GetPendingApprovals(c *fiber.Ctx) error {
    approvals := h.engine.GetPendingApprovals()
    return Render(c, "hitl_queue", fiber.Map{
        "Approvals": approvals,
    })
}

func (h *Handler) ApprovePR(c *fiber.Ctx) error {
    id := c.Params("id")
    h.engine.Approve(id, true)
    return h.GetPendingApprovals(c)
}

func (h *Handler) RejectPR(c *fiber.Ctx) error {
    id := c.Params("id")
    h.engine.Approve(id, false)
    return h.GetPendingApprovals(c)
}

// Agent Status
func (h *Handler) GetAgentStatus(c *fiber.Ctx) error {
    agent := c.Params("agent")
    status := h.engine.GetAgentStatus(agent)
    return c.JSON(status)
}

// Task Board
func (h *Handler) GetTasksByStatus(c *fiber.Ctx) error {
    status := c.Params("status")
    tasks := h.engine.GetTasksByStatus(status)
    return Render(c, "task_items", fiber.Map{
        "Tasks": tasks,
    })
}

// Config
func (h *Handler) GetConfig(c *fiber.Ctx) error {
    config := h.engine.GetConfig()
    return Render(c, "config_panel", fiber.Map{
        "Config": config,
    })
}

func (h *Handler) SaveConfig(c *fiber.Ctx) error {
    var config Config
    if err := c.BodyParser(&config); err != nil {
        return c.Status(400).SendString("Invalid config")
    }
    h.engine.SaveConfig(config)
    return c.String("Configuration saved!")
}

// Telemetry
func (h *Handler) GetSigNoz(c *fiber.Ctx) error {
    // Embed or proxy SigNoz dashboard
    return Render(c, "telemetry_signoz", nil)
}

func (h *Handler) GetHyperDX(c *fiber.Ctx) error {
    // Embed or proxy HyperDX dashboard
    return Render(c, "telemetry_hyperdx", nil)
}

func (h *Handler) GetMetrics(c *fiber.Ctx) error {
    metrics := h.engine.GetMetrics()
    return Render(c, "telemetry_metrics", fiber.Map{
        "Metrics": metrics,
    })
}
```

---

## Route Registration

**File:** `apps/core/internal/web/handler.go`

```go
func (h *Handler) RegisterRoutes(app *fiber.App) {
    // Existing routes
    app.Get("/", h.Dashboard)
    app.Post("/feedback", h.HandleFeedback)
    
    // New Panel Routes
    app.Get("/api/stream/events", h.HandleSSE)
    app.Get("/api/approvals/pending", h.GetPendingApprovals)
    app.Post("/api/approvals/:id/approve", h.ApprovePR)
    app.Post("/api/approvals/:id/reject", h.RejectPR)
    app.Get("/api/agents/:agent/status", h.GetAgentStatus)
    app.Get("/api/tasks/:status", h.GetTasksByStatus)
    app.Get("/api/config", h.GetConfig)
    app.Post("/api/config/save", h.SaveConfig)
    app.Get("/api/telemetry/signoz", h.GetSigNoz)
    app.Get("/api/telemetry/hyperdx", h.GetHyperDX)
    app.Get("/api/telemetry/metrics", h.GetMetrics)
}
```

---

## Testing (HTMX Approach)

Instead of React component tests, we test:

1. **Go Handlers** (unit tests)
2. **Template Rendering** (integration tests)
3. **SSE Streaming** (integration tests)
4. **E2E Flow** (Playwright tests)

### Example Test

**File:** `apps/core/internal/web/handler_test.go`

```go
func TestHandler_GetPendingApprovals(t *testing.T) {
    app := fiber.New()
    handler := NewHandler(mockEngine)
    handler.RegisterRoutes(app)
    
    resp, err := app.Test(httptest.NewRequest("GET", "/api/approvals/pending", nil))
    
    assert.NoError(t, err)
    assert.Equal(t, 200, resp.StatusCode)
    assert.Contains(t, resp.Header.Get("Content-Type"), "text/html")
}

func TestHandler_SSE_Stream(t *testing.T) {
    app := fiber.New()
    handler := NewHandler(mockEngine)
    handler.RegisterRoutes(app)
    
    req := httptest.NewRequest("GET", "/api/stream/events", nil)
    resp, err := app.Test(req)
    
    assert.NoError(t, err)
    assert.Equal(t, "text/event-stream", resp.Header.Get("Content-Type"))
}
```

---

## Implementation Order

1. **Day 1:** Live Feed (SSE) - Already have `sse.go`, just embed in template
2. **Day 2:** HITL Queue - Add approval handlers
3. **Day 3:** Agent Map - Add status endpoints
4. **Day 4:** Task Board + Config + Telemetry

**Total:** 4 days (vs 5 days for React)

---

## Benefits of HTMX Approach

| Benefit | Description |
|---------|-------------|
| **No Build Step** | Edit template → refresh browser |
| **Smaller Bundle** | 14KB htmx.js vs 130KB React |
| **Server-Side State** | No complex state management |
| **Go Templates** | Type-safe, compiled |
| **Existing Code** | Build on 16KB existing template |
| **Faster Dev** | No npm install, webpack, etc. |

---

## Next Steps

1. **Verify existing SSE handler works**
2. **Add HTMX extension to templates**
3. **Implement remaining Go handlers**
4. **Test with real infrastructure**
5. **Commit and push**

**Ready to implement?**
