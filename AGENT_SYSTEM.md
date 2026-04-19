# IterateSwarm Agent System

## Overview
Polyglot AI agent system where specialized agents collaborate through:
- Centralized Qdrant memory
- Temporal workflow orchestration
- Standardized communication patterns


```
+---------------------------------+     +---------------------------------+
|          Data Sources           |     |           Core System           |
+---------------------------------+     +---------------------------------+
|                                 |     |                                 |
|  +-------+      +------------+  |     |  +------------+     +--------+  |
|  |Stripe |----->|            |  |     |  |            |<----|Anomaly |  |
|  +-------+      |            |  |     |  |            |     | Agent  |  |
|                 |  Temporal  |<-------|->|  Qdrant    |     +--------+  |
|  +----------+   |  Workflows |  |     |  |  Memory    |     +--------+  |
|  |Quickbooks|-->|            |  |     |  |            |<----|Investor|  |
|  +----------+   |            |  |     |  |            |     | Agent  |  |
|                 +------------+  |     |  |            |     +--------+  |
|  +-----------+     ^            |     |  |            |     +--------+  |
|  |Product DB |-----|            |     |  |            |<----| Pulse  |  |
|  +-----------+     |            |     |  |            |     | Agent  |  |
|                    |            |     |  |            |     +--------+  |
+---------------------------------+     |  |            |     +--------+  |
                                        |  |            |<----| QA     |  |
                                        |  |            |     | Agent  |  |
                                        |  +------------+     +--------+  |
                                        |                                 |
                                        |  +------------+     +---------+ |
                                        |  | Alerts     |<----| All     | |
                                        |  | (Slack/    |     | Agents  | |
                                        |  |  Telegram) |     +---------+ |
                                        |  +------------+                 |
                                        +---------------------------------+
                                                 ^              |
                                                 |              v
                                        +---------------------------------+
                                        |       Human Interaction         |
                                        +---------------------------------+
                                        |                                 |
                                        |  +-------+     +------------+   |
                                        |  |Founder|---->| Questions  |   |
                                        |  +-------+     +------------+   |
                                        |        |                        |
                                        |        |  +-----------------+   |
                                        |        |->| Actions (Signal)|   |
                                        |           +-----------------+   |
                                        +---------------------------------+
```

## Individual Agents

### 1. AnomalyAgent
**Purpose**: Detect unusual patterns in financial/revenue data

**AnomalyAgent Workflow**:
1. Detect anomalies in data
2. If anomaly found:
   - Retrieve related memories from Qdrant
   - Generate explanation of anomaly
   - Generate recommended action
   - Build Slack message
   - Send alert
3. If no anomaly, end workflow

**Key Components**:
- `detect_anomaly_node`: Statistical analysis to identify deviations
- `retrieve_anomaly_memory`: Checks historical patterns in Qdrant
- `generate_explanation`: AI-generated root cause analysis

### 2. InvestorAgent
**Purpose**: Create investor reports with self-critique mechanism

**InvestorAgent Workflow**:
1. Fetch financial metrics
2. Retrieve relevant memories from Qdrant
3. Generate report draft
4. Critique draft quality:
   - If passes: build Slack message and send report
   - If fails: revise draft (max 1 revision)

**Innovative Feature**: Self-critique loop ensures quality before sending (max 1 revision)

### 3. PulseAgent
**Purpose**: Weekly business health reports with data validation

**PulseAgent Workflow**:
1. Fetch required data
2. Check data completeness:
   - If complete: compute metrics → generate narrative
   - If incomplete: use fallback message
3. Build Slack message
4. Send report
5. Persist snapshot to Qdrant

**Data Resilience**: Graceful degradation when data is missing

### 4. QAAgent
**Purpose**: Answer founder questions using multiple strategies

**Operational Modes**:
1. **Sequential QA**: Simple question → answer pipeline
2. **ReAct Agent**: Autonomous tool use with reasoning:
   - Tools: `search_pulse_memory`, `query_stripe_metrics`, `query_product_db`
   - System prompt: "Think step-by-step before using tools"

## System Integration

### Shared Components
- **AgentResult Standard Format**:
  ```python
  {
      "headline": "Plain English summary",
      "do_this": "Actionable next step",
      "urgency": "critical|high|medium|low",
      "output_json": {}  # Structured data
  }
  ```
  
- **Jargon Enforcement**: 108 banned terms (e.g., "leverage", "synergy", "paradigm")
- **Memory Schema** (Qdrant):
  ```python
  {
      "tenant_id": str,
      "content": str,
      "memory_type": "anomaly|briefing|revenue_event",
      "agent": "AnomalyAgent|InvestorAgent|etc"
  }
  ```

### Workflow Integration
1. **Temporal Triggers**:
   - Go workflows invoke Python agents via gRPC
   - Agents run as activities in Temporal task queues

2. **Cross-Agent Collaboration**:
   - AnomalyAgent detects issue → triggers PulseAgent for full analysis
   - InvestorAgent uses PulseAgent's memory for historical context
   - QAAgent queries outputs from all other agents

3. **Human Feedback Loop**:
   - Founders ask questions → QAAgent responds using agent memories
   - Button clicks → Temporal signals → Update workflows

## Benefits
1. **Proactive Monitoring**: Automatic anomaly detection → full investigation
2. **Knowledge Continuity**: All findings archived with agent context
3. **Adaptive Responses**: System learns from historical patterns
4. **Quality Assurance**: Built-in validation at multiple levels