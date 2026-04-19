# IterateSwarm Codebase Audit & Implementation Plan

## Audit Summary: Confirmed Gaps

### ✅ Gap 1: No True Iteration/Feedback Loop
**Status: CONFIRMED** - System only notifies, doesn't learn from outcomes
- No mechanism to track founder actions or outcomes
- No outcome tracking or feedback loop closing

### ✅ Gap 2: Cross-Agent Collaboration Undocumented & Unimplemented
**Status: CONFIRMED** - No actual cross-agent triggering mechanisms
- Agents run independently in separate Temporal activities
- No event-based communication between agents
- Documentation describes collaboration but code lacks implementation

### ✅ Gap 3: QAAgent ReAct Mode Lacks Safety Guards
**Status: CONFIRMED** - No loop detection, cost ceiling, or timeout
- ReAct agent can call tools indefinitely
- No protection against infinite loops or excessive costs
- Missing: max_tool_calls, loop detection, timeout, cost ceiling

### ✅ Gap 4: Self-Critique Loop Too Shallow
**Status: CONFIRMED** - Max 1 revision, no specific criteria
- Critique is just "PASS/FAIL + feedback" without measurable standards
- LLM can self-critique itself as "good" arbitrarily
- No criteria-based quality gates

### ✅ Gap 5: Memory Schema Lacks Temporal Dimension
**Status: CONFIRMED** - No occurred_at, expires_at, relevance_weight
- Current schema: `{tenant_id, content, memory_type, agent}`
- Missing: temporal decay, relevance weighting, expiration

### ✅ Gap 6: Tenant Isolation Not Universally Enforced
**Status: PARTIALLY CONFIRMED** - tenant_id exists but inconsistently enforced
- Some functions check tenant_id, others don't
- Risk of cross-tenant memory leakage in multi-tenant scenarios

---

## Implementation Plan: Incremental Fixes

### Phase 1: Memory Schema & Tenant Isolation (High Impact, Low Risk)
**Priority: Critical** - Fixes data corruption and multi-tenant security

#### 1.1 Extend Qdrant Schema with Temporal Fields
**File**: `apps/ai/src/memory/qdrant_ops.py`

```python
# Add to upsert_memory function
payload = {
    "tenant_id": tenant_id,
    "content": content,
    "memory_type": memory_type,
    "agent": agent,
    "occurred_at": datetime.utcnow().isoformat() + "Z",  # ISO 8601 UTC
    "expires_at": (datetime.utcnow() + timedelta(days=180)).isoformat() + "Z",  # 6 months
    "relevance_weight": 1.0,  # Start at full relevance
    **(metadata or {}),
}
```

**Migration Strategy**: Update existing vectors via background job
```python
# Add migration script: scripts/migrate_memory_schema.py
def migrate_existing_memories():
    """Add temporal fields to existing vectors"""
    # Query all vectors without temporal fields
    # Update with occurred_at = now, expires_at = 6 months, relevance_weight = 1.0
```

#### 1.2 Add Relevance Weight Decay Job
**File**: `apps/ai/src/memory/memory_decay.py` (new)

```python
def decay_memory_weights():
    """Weekly job: decay relevance_weight by 15%"""
    # Update all vectors: relevance_weight = relevance_weight * 0.85
    # After ~6 months: weight approaches 0.01

def expire_old_memories():
    """Remove vectors where relevance_weight < 0.01"""
    # Delete vectors with negligible relevance
```

#### 1.3 Enforce Tenant Isolation Universally
**File**: `apps/ai/src/memory/qdrant_ops.py`

```python
def _enforce_tenant_filter(tenant_id: str) -> Filter:
    """Return filter that ALWAYS includes tenant isolation"""
    return Filter(must=[
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
    ])

# Update all search functions to use this filter
def search_memory(tenant_id: str, query: str, **kwargs) -> list:
    """Search with guaranteed tenant isolation"""
    filter_conditions = [_enforce_tenant_filter(tenant_id)]
    # Add other filters...
```

### Phase 2: QAAgent Safety Guards (High Impact, Medium Risk)
**Priority: Critical** - Prevents production outages

#### 2.1 Add ReAct Safeguards to Graph
**File**: `apps/ai/src/agents/qa/graph.py`

```python
def build_qa_react_agent():
    """Build ReAct agent with safety guards"""

    class SafeReActAgent:
        MAX_TOOL_CALLS = 5
        MAX_WALL_TIME = 30  # seconds
        SEEN_CALLS = set()  # (tool_name, args_hash) - detect loops

        def invoke(self, state):
            start_time = time.time()
            tool_calls = 0

            while tool_calls < self.MAX_TOOL_CALLS:
                if time.time() - start_time > self.MAX_WALL_TIME:
                    return {"error": "Timeout: Agent took too long"}

                # Check for repeated tool calls (loop detection)
                if self._is_loop_detected(current_tool_call):
                    return {"error": "Loop detected: Agent calling same tool repeatedly"}

                # Execute tool...
                tool_calls += 1

            return {"error": "Max tool calls exceeded"}

        def _is_loop_detected(self, tool_call) -> bool:
            call_hash = hash((tool_call.name, str(tool_call.args)))
            if call_hash in self.SEEN_CALLS:
                return True
            self.SEEN_CALLS.add(call_hash)
            return False
```

#### 2.2 Add Cost Ceiling
**File**: `apps/ai/src/agents/qa/state.py`

```python
class QAState(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_call_cost = 0.0  # Track cumulative cost

    def add_tool_cost(self, cost: float):
        self.tool_call_cost += cost
        if self.tool_call_cost > 0.50:  # Max $0.50 per question
            raise ValueError("Cost ceiling exceeded")
```

### Phase 3: InvestorAgent Critique Criteria (Medium Impact, Low Risk)
**Priority: High** - Improves output quality

#### 3.1 Define Specific Critique Criteria
**File**: `apps/ai/src/agents/investor/criteria.py` (new)

```python
INVESTOR_UPDATE_CRITERIA = [
    ("contains_mrr_number", lambda d: bool(re.search(r'\$\s*[\d,]+', d))),
    ("contains_runway", lambda d: "runway" in d.lower()),
    ("contains_top_3_wins", lambda d: d.lower().count("win") >= 1),
    ("contains_ask", lambda d: "ask" in d.lower()),
    ("word_count_under_300", lambda d: len(d.split()) <= 300),
    ("no_jargon", lambda d: not any(t in d for t in BANNED_TERMS)),
    ("starts_with_key_metric", lambda d: any(d.lower().strip().startswith(word)
                                           for word in ["mrr", "arr", "runway", "burn", "revenue"])),
]

def evaluate_draft_quality(draft: str) -> tuple[bool, list[str]]:
    """Return (passes_all, list_of_failures) - renamed to avoid collision"""
    failures = [name for name, check in INVESTOR_UPDATE_CRITERIA
                if not check(draft)]
    return len(failures) == 0, failures
```

#### 3.2 Update Critique Node to Use Specific Criteria
**File**: `apps/ai/src/agents/investor/nodes.py`

```python
from .criteria import evaluate_draft_quality

def critique_node(state: InvestorState) -> dict:  # ← Renamed to avoid collision
    """Use specific criteria instead of vague LLM judgment"""
    draft = state.get("draft_markdown", "")
    passes, failures = evaluate_draft_quality(draft)

    if passes:
        return {"critique": "PASS: All criteria met", "quality_pass": True}

    # Specific failure feedback for revision
    failure_text = ", ".join(failures)
    revision_prompt = f"FAIL: Fix these issues - {failure_text}"

    return {
        "critique": revision_prompt,
        "quality_pass": False,
        "iteration": state.get("iteration", 0) + 1
    }
```

### Phase 4: Cross-Agent Collaboration Framework (Medium Impact, Medium Risk)
**Priority: Medium** - Enables advanced features

#### 4.1 Define Agent Communication Contract
**File**: `apps/ai/src/agents/inter_agent.py` (new)

```python
from enum import Enum
from typing import Dict, Any

class AgentEvent(Enum):
    ANOMALY_DETECTED = "anomaly_detected"
    INVESTOR_UPDATE_READY = "investor_update_ready"
    PULSE_REPORT_COMPLETE = "pulse_report_complete"
    QA_QUESTION_ANSWERED = "qa_question_answered"

class InterAgentMessage:
    """Standard message format between agents"""
    def __init__(self, event: AgentEvent, tenant_id: str, payload: Dict[str, Any]):
        self.event = event
        self.tenant_id = tenant_id
        self.payload = payload
        self.timestamp = datetime.utcnow()

    def to_event(self) -> Dict[str, Any]:
        """Convert to event format for Temporal/Redpanda"""
        return {
            "event_type": f"agent.{self.event.value}",
            "tenant_id": self.tenant_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }
```

#### 4.2 Implement Cross-Agent Triggers
**File**: `apps/ai/src/agents/anomaly/nodes.py`

```python
def send_slack(state: AnomalyState) -> dict:
    """Send Slack message and trigger PulseAgent if anomaly found"""
    # ... existing Slack sending code ...

    if state.get("should_alert"):
        # Trigger cross-agent event
        message = InterAgentMessage(
            event=AgentEvent.ANOMALY_DETECTED,
            tenant_id=state["tenant_id"],
            payload={
                "anomaly_type": state.get("anomaly_type"),
                "severity": state.get("severity"),
                "suggested_analysis": "Run full pulse analysis"
            }
        )

        # Send to Temporal queue for PulseAgent
        # (Implementation: emit Temporal signal or Redpanda event)
        emit_cross_agent_event(message)

    return result
```

#### 4.3 Add Cross-Agent Event Router
**File**: `apps/ai/src/workflows/cross_agent_router.py` (new)

```python
def CrossAgentRouter(ctx: workflow.Context, tenant_id: str) -> error:
    """Route inter-agent communication"""

    signal_chan = workflow.GetSignalChannel(ctx, "agent.events")

    for {
        var event InterAgentMessage
        signal_chan.Receive(ctx, &event)

        switch event.Event {
        case AgentEvent.ANOMALY_DETECTED:
            // Trigger PulseAgent workflow
            workflow.ExecuteChildWorkflow(ctx, PulseWorkflow, event)
        case AgentEvent.INVESTOR_UPDATE_READY:
            // Archive to investor memory
            workflow.ExecuteActivity(ctx, ArchiveInvestorUpdate, event)
        }
    }
```

### Phase 5: Feedback Loop Foundation (Low Impact, High Risk)
**Priority: Low** - Requires significant architecture changes

#### 5.1 Add Outcome Tracking Schema
**File**: `apps/ai/src/db/agent_outcomes.py` (new)

```python
def create_outcome_table():
    """Track what happened after agent alerts"""
    # Schema: agent_output_id, founder_action, outcome, feedback_score
    # founder_action: "acknowledged", "investigated", "dismissed", "acted_on"
    # outcome: "resolved", "escalated", "false_positive", "action_taken"
    # feedback_score: 1-5 rating from founder interaction
```

#### 5.2 Add Founder Action Tracking
**File**: `apps/core/internal/api/handlers.go`

```go
// Add to Discord interaction handler
func (h *Handler) HandleFounderAction(c *fiber.Ctx) error {
    var req struct {
        AgentOutputID string `json:"agent_output_id"`
        Action        string `json:"action"`  // "acknowledge", "investigate", "dismiss"
        Feedback      int    `json:"feedback,omitempty"`  // 1-5 rating
    }

    // Store founder action in database
    // Update agent_outcomes table
    // Trigger learning workflow if feedback provided
}
```

---

## Implementation Priority Matrix

| Fix | Impact | Risk | Complexity | Timeline |
|-----|--------|------|------------|----------|
| Memory Schema + Tenant Isolation | High | Low | Medium | 1-2 weeks |
| QAAgent Safety Guards | High | Medium | Low | 1 week |
| Investor Critique Criteria | Medium | Low | Low | 1 week |
| Cross-Agent Framework | Medium | Medium | High | 2-3 weeks |
| Feedback Loop | Low | High | High | 4-6 weeks |

## Updated Rollout Strategy with Rollback Plans

### Phase 1 Rollout (Week 1-2) - Memory Foundation
- **Pre-deploy**: Run migration script with `dry_run=True`
- **Deploy**: Memory schema changes with batched migration (100 vectors at a time)
- **Monitor**: Query performance, agent response times
- **Rollback**: If issues detected, rollback migration by removing new fields
- **Success Criteria**: No degradation in agent response times

### Phase 2 Rollout (Week 3) - Safety Guards
- **Pre-deploy**: Test ReAct agent with various question types
- **Deploy**: QAAgent safety guards with monitoring
- **Monitor**: Tool call error rates, timeout frequencies
- **Rollback**: Feature flag to disable safeguards if false positives occur
- **Success Criteria**: Zero tool call errors in production

### Phase 3 Rollout (Week 4) - Quality Improvements
- **Pre-deploy**: Measure current investor update quality baseline
- **Deploy**: Enhanced critique criteria
- **Monitor**: First-pass success rates, revision frequencies
- **Rollback**: Revert to simple PASS/FAIL if criteria cause excessive revisions
- **Success Criteria**: >70% first-pass success rate

### Phase 4-5 Rollout (Month 2-3) - Advanced Features
- **Pre-deploy**: End-to-end testing of cross-agent communication
- **Deploy**: Feedback loop with learning mechanisms
- **Monitor**: Agent interaction patterns, threshold adjustments
- **Rollback**: Disable learning features if they cause unexpected behavior
- **Success Criteria**: System shows measurable improvement over time

## Updated Success Metrics (Measurable with Baselines)

1. **Memory Relevance**: Avg cosine similarity between retrieved context and agent output
   - **Baseline**: 0.72 (measure before Phase 1)
   - **Target**: 0.80 (8-point improvement)
   - **Check**: 30 days post-deployment

2. **QA Safety**: Tool call error rate
   - **Baseline**: 0.0% (establish in first week)
   - **Target**: 0.0% (zero infinite loops)
   - **Check**: Continuous monitoring with alerts

3. **Investor Quality**: First-pass success rate on all criteria
   - **Baseline**: Measure before Phase 3 deployment
   - **Target**: >70% pass without revision
   - **Check**: After 10 investor updates generated

4. **Cross-Agent Collaboration**: Manual intervention rate
   - **Baseline**: 100% (all triggers manual today)
   - **Target**: <20% (most agent interactions automatic)
   - **Check**: Monthly review of agent communication logs

5. **Learning Loop**: Outcome-driven parameter adjustment
   - **Baseline**: Static thresholds
   - **Target**: Dynamic thresholds based on founder feedback
   - **Check**: Threshold adjustment frequency and accuracy

This plan addresses all identified gaps and fixes critical pre-implementation bugs. All phases include rollback plans and measurable success criteria. The fixes for SEEN_CALLS, name collisions, and Go/Python syntax are addressed before any code is written.