# Week 4 Implementation Plan - React Admin Panel

**Date:** 2026-02-26  
**Status:** Week 3 Complete (50 tests passing)  
**Next:** Week 4 - React Admin Panel (6 panels, ~20 tests)

---

## Overview

Build a React admin panel to visualize agent activity and enable human-in-the-loop approvals.

**Tech Stack:**
- React 18 + TypeScript
- Vite (build tool)
- shadcn/ui (components)
- Tailwind CSS (styling)
- React Query (data fetching)
- SSE (Server-Sent Events for live feed)

---

## Panel Priority

| Panel | Priority | Tests | Time | Dependencies |
|-------|----------|-------|------|--------------|
| **Live Feed** | CRITICAL | 4 | 1 day | Go SSE handler |
| **HITL Queue** | HIGH | 4 | 1 day | Live Feed |
| **Agent Map** | MEDIUM | 3 | 1 day | ReactFlow |
| **Task Board** | LOW | 4 | 1 day | dnd-kit |
| **Config Panel** | LOW | 3 | 0.5 day | - |
| **Telemetry Panel** | LOW | 2 | 0.5 day | - |

**Total:** 20 tests, 4-5 days

---

## Panel 1: Live Feed (CRITICAL)

**Purpose:** Real-time streaming of agent events via SSE

### Backend (Go)

**File:** `apps/core/internal/web/sse.go`

```go
package web

import (
    "encoding/json"
    "net/http"
    "time"
    
    "github.com/gofiber/fiber/v2"
    "github.com/redis/go-redis/v9"
)

type AgentEvent struct {
    ID        string                 `json:"id"`
    Timestamp time.Time              `json:"timestamp"`
    Agent     string                 `json:"agent"`  // supervisor, researcher, sre, swe, reviewer
    Type      string                 `json:"type"`   // planning, executing, reviewing, completing
    TaskID    string                 `json:"task_id"`
    Data      map[string]interface{} `json:"data"`
}

type SSEHandler struct {
    redis *redis.Client
}

func NewSSEHandler(redis *redis.Client) *SSEHandler {
    return &SSEHandler{redis: redis}
}

// HandleSSE streams agent events via Server-Sent Events
func (h *SSEHandler) HandleSSE(c *fiber.Ctx) error {
    // Set SSE headers
    c.Set("Content-Type", "text/event-stream")
    c.Set("Cache-Control", "no-cache")
    c.Set("Connection", "keep-alive")
    c.Set("X-Accel-Buffering", "no") // Disable nginx buffering
    
    // Subscribe to Redis pub/sub
    pubsub := h.redis.Subscribe(c.Context(), "agent-events")
    defer pubsub.Close()
    
    channel := pubsub.Channel()
    
    // Stream events
    for {
        select {
        case msg := <-channel:
            var event AgentEvent
            if err := json.Unmarshal([]byte(msg.Payload), &event); err != nil {
                continue
            }
            
            // Format: data: {"id":"...", "agent":"swe", ...}
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

### Frontend (React)

**File:** `apps/web/src/components/LiveFeed.tsx`

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

interface AgentEvent {
  id: string
  timestamp: string
  agent: 'supervisor' | 'researcher' | 'sre' | 'swe' | 'reviewer'
  type: 'planning' | 'executing' | 'reviewing' | 'completing'
  task_id: string
  data: Record<string, unknown>
}

const agentColors = {
  supervisor: 'bg-purple-500',
  researcher: 'bg-blue-500',
  sre: 'bg-red-500',
  swe: 'bg-green-500',
  reviewer: 'bg-yellow-500',
}

export function LiveFeed() {
  const [events, setEvents] = useState<AgentEvent[]>([])
  
  useEffect(() => {
    const eventSource = new EventSource('/api/stream/events')
    
    eventSource.onmessage = (event) => {
      const newEvent = JSON.parse(event.data) as AgentEvent
      setEvents(prev => [newEvent, ...prev].slice(0, 200)) // Keep last 200
    }
    
    eventSource.onerror = (error) => {
      console.error('SSE connection failed:', error)
      eventSource.close()
      // Reconnect after 5 seconds
      setTimeout(() => window.location.reload(), 5000)
    }
    
    return () => eventSource.close()
  }, [])
  
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Live Agent Feed</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px]">
          <div className="space-y-2 font-mono text-sm">
            {events.map(event => (
              <div
                key={event.id}
                className="flex items-center gap-2 p-2 bg-muted rounded"
              >
                <Badge className={agentColors[event.agent]}>
                  {event.agent}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
                <span className="font-semibold">{event.type}</span>
                <span className="text-muted-foreground">
                  Task: {event.task_id}
                </span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
```

### Tests (4 tests)

**File:** `apps/web/tests/LiveFeed.test.tsx`

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { LiveFeed } from '@/components/LiveFeed'

// Mock EventSource
class MockEventSource {
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  
  constructor() {
    setTimeout(() => {
      this.onmessage?.({
        data: JSON.stringify({
          id: 'test-1',
          timestamp: new Date().toISOString(),
          agent: 'swe',
          type: 'executing',
          task_id: 'task-123',
          data: {}
        })
      })
    }, 100)
  }
  
  close() {}
}

global.EventSource = MockEventSource as any

describe('LiveFeed', () => {
  it('renders empty state initially', () => {
    render(<LiveFeed />)
    expect(screen.getByText('Live Agent Feed')).toBeInTheDocument()
  })
  
  it('displays incoming SSE events', async () => {
    render(<LiveFeed />)
    
    await waitFor(() => {
      expect(screen.getByText('swe')).toBeInTheDocument()
      expect(screen.getByText('task-123')).toBeInTheDocument()
    })
  })
  
  it('reconnects on error', async () => {
    render(<LiveFeed />)
    // Test reconnection logic
  })
  
  it('limits to 200 events', async () => {
    render(<LiveFeed />)
    // Test event limit
  })
})
```

---

## Panel 2: HITL Queue (HIGH)

**Purpose:** Human-in-the-loop approval queue for PRs

### Files

**Component:** `apps/web/src/components/HITLQueue.tsx`

```tsx
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface PendingApproval {
  id: string
  task_id: string
  pr_url: string
  pr_number: number
  agent: 'swe'
  reasoning: string
  confidence: number
  created_at: string
}

export function HITLQueue() {
  const [pending, setPending] = useState<PendingApproval[]>([])
  
  const handleApprove = async (id: string) => {
    await fetch(`/api/approvals/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'approve' })
    })
    setPending(prev => prev.filter(p => p.id !== id))
  }
  
  const handleReject = async (id: string) => {
    await fetch(`/api/approvals/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reject' })
    })
    setPending(prev => prev.filter(p => p.id !== id))
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>HITL Approval Queue</CardTitle>
      </CardHeader>
      <CardContent>
        {pending.length === 0 ? (
          <p className="text-muted-foreground">No pending approvals</p>
        ) : (
          <div className="space-y-4">
            {pending.map(approval => (
              <Card key={approval.id}>
                <CardContent className="pt-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold">
                        PR #{approval.pr_number}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {approval.reasoning}
                      </p>
                      <Badge>
                        Confidence: {(approval.confidence * 100).toFixed(0)}%
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleApprove(approval.id)}
                        variant="default"
                      >
                        Approve
                      </Button>
                      <Button
                        onClick={() => handleReject(approval.id)}
                        variant="destructive"
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

**Tests:** 4 tests in `apps/web/tests/HITLQueue.test.tsx`

---

## Panel 3: Agent Map (MEDIUM)

**Purpose:** Visual representation of agent topology

### Files

**Component:** `apps/web/src/components/AgentMap.tsx`

```tsx
import ReactFlow, { Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'

const initialNodes: Node[] = [
  { id: 'supervisor', position: { x: 400, y: 50 }, data: { label: 'Supervisor' } },
  { id: 'researcher', position: { x: 100, y: 200 }, data: { label: 'Researcher' } },
  { id: 'sre', position: { x: 300, y: 200 }, data: { label: 'SRE' } },
  { id: 'swe', position: { x: 500, y: 200 }, data: { label: 'SWE' } },
  { id: 'reviewer', position: { x: 700, y: 200 }, data: { label: 'Reviewer' } },
]

const initialEdges: Edge[] = [
  { id: 'sup-researcher', source: 'supervisor', target: 'researcher' },
  { id: 'sup-sre', source: 'supervisor', target: 'sre' },
  { id: 'sup-swe', source: 'supervisor', target: 'swe' },
  { id: 'sup-reviewer', source: 'supervisor', target: 'reviewer' },
  { id: 'swe-reviewer', source: 'swe', target: 'reviewer' },
]

export function AgentMap() {
  return (
    <div style={{ height: '600px' }}>
      <ReactFlow nodes={initialNodes} edges={initialEdges} fitView />
    </div>
  )
}
```

**Tests:** 3 tests in `apps/web/tests/AgentMap.test.tsx`

---

## Remaining Panels (LOW Priority)

### Panel 4: Task Board
- Kanban board with drag-and-drop
- Use `@dnd-kit/core`
- 4 tests

### Panel 5: Config Panel
- Form for agent configuration
- Hot-reload settings
- 3 tests

### Panel 6: Telemetry Panel
- Embed SigNoz and HyperDX dashboards
- Iframe components
- 2 tests

---

## Implementation Order

1. **Day 1:** Set up React app + Live Feed panel
2. **Day 2:** HITL Queue panel
3. **Day 3:** Agent Map panel
4. **Day 4:** Task Board + Config + Telemetry
5. **Day 5:** Polish, test, document

---

## Testing Protocol

For each panel:
1. Write test FIRST (TDD)
2. Implement component
3. Run test
4. Fix until passing
5. Commit
6. Next test

**Test Command:**
```bash
cd apps/web
npm test -- --watch
```

---

## Git Safety

```bash
# NEVER use git add .
# ALWAYS use explicit files:
git add apps/web/src/components/LiveFeed.tsx
git commit -m "feat: LiveFeed panel with SSE streaming"
git push
```

---

**Ready for delegation to nextjs-expert subagent**
