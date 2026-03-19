package workflow

import (
	"context"
	"fmt"
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
	"iterateswarm-core/internal/events"
)

// SarthiContinueAsNewThreshold is the number of events before triggering Continue-As-New in SarthiRouter
const SarthiContinueAsNewThreshold = 1000

// SarthiRouterState tracks workflow state across Continue-As-New cycles
type SarthiRouterState struct {
	TenantID        string          `json:"tenant_id"`
	EventsProcessed int             `json:"events_processed"`
	SeenKeys        map[string]bool `json:"seen_keys"`
}

// EventRoutingTable maps event types to workflow names
type EventRoutingTable map[string][]string

// GetRoutingTable returns the event routing configuration
// This is the central routing logic for Sarthi v1.0
func GetRoutingTable() EventRoutingTable {
	return EventRoutingTable{
		// ==================== REVENUE TRACKER ====================
		// Payment & Subscription events from Razorpay
		"PAYMENT_SUCCESS":        {"RevenueWorkflow"},
		"SUBSCRIPTION_CREATED":   {"RevenueWorkflow"},
		"SUBSCRIPTION_UPDATED":   {"RevenueWorkflow"},
		"SUBSCRIPTION_CANCELED":  {"RevenueWorkflow"},
		"PAYMENT_FAILED":         {"RevenueWorkflow"},
		"INVOICE_PAID":           {"RevenueWorkflow"},
		"INVOICE_EXPIRED":        {"RevenueWorkflow"},
		"REFUND_CREATED":         {"RevenueWorkflow"},

		// CRM & Sales events
		"CRM_DEAL_CREATED":       {"RevenueWorkflow"},
		"CRM_DEAL_UPDATED":       {"RevenueWorkflow"},
		"CRM_DEAL_WON":           {"RevenueWorkflow"},
		"CRM_DEAL_LOST":          {"RevenueWorkflow"},

		// Weekly tick for revenue review
		"TIME_TICK_WEEKLY":       {"RevenueWorkflow", "ChiefOfStaffWorkflow"}, // Multi-route

		// ==================== CS AGENT ====================
		// User lifecycle events
		"USER_SIGNED_UP":         {"CSWorkflow"},
		"USER_LOGGED_IN":         {"CSWorkflow"},
		"USER_LOGGED_OUT":        {"CSWorkflow"},
		"USER_PROFILE_UPDATED":   {"CSWorkflow"},

		// Support events
		"SUPPORT_TICKET_CREATED": {"CSWorkflow"},
		"SUPPORT_TICKET_UPDATED": {"CSWorkflow"},
		"SUPPORT_TICKET_RESOLVED":{"CSWorkflow"},

		// Day-based ticks for CS follow-ups
		"TIME_TICK_D1":           {"CSWorkflow"}, // Day 1 check-in
		"TIME_TICK_D3":           {"CSWorkflow"}, // Day 3 follow-up
		"TIME_TICK_D7":           {"CSWorkflow"}, // Day 7 retention check

		// ==================== PEOPLE COORDINATOR ====================
		// Employee lifecycle
		"EMPLOYEE_CREATED":       {"PeopleWorkflow"},
		"EMPLOYEE_UPDATED":       {"PeopleWorkflow"},
		"EMPLOYEE_TERMINATED":    {"PeopleWorkflow"},

		// Checklist & onboarding
		"CHECKLIST_ITEM_CONFIRMED":{"PeopleWorkflow"},
		"CHECKLIST_ITEM_COMPLETED":{"PeopleWorkflow"},
		"ONBOARDING_STARTED":     {"PeopleWorkflow"},
		"ONBOARDING_COMPLETED":   {"PeopleWorkflow"},

		// ==================== FINANCE MONITOR ====================
		// Expense & accounting
		"EXPENSE_RECORDED":       {"FinanceWorkflow"},
		"EXPENSE_APPROVED":       {"FinanceWorkflow"},
		"EXPENSE_REJECTED":       {"FinanceWorkflow"},

		// Bank & payment processing
		"BANK_WEBHOOK":           {"FinanceWorkflow"},
		"BANK_TRANSACTION":       {"FinanceWorkflow"},
		"VENDOR_INVOICE_RECEIVED":{"FinanceWorkflow"},
		"VENDOR_INVOICE_PAID":    {"FinanceWorkflow"},

		// Daily finance review
		"TIME_TICK_DAILY":        {"FinanceWorkflow"},

		// ==================== CHIEF OF STAFF ====================
		// Monthly executive review
		"TIME_TICK_MONTHLY":      {"ChiefOfStaffWorkflow"},

		// Agent outputs require CoS attention
		"AGENT_OUTPUT":           {"ChiefOfStaffWorkflow"},

		// Strategic decisions
		"DECISION_LOGGED":        {"ChiefOfStaffWorkflow"},
		"POLICY_CHANGE":          {"ChiefOfStaffWorkflow"},
	}
}

// SarthiRouter is the parent router that spawns child workflows based on event type.
// It implements the router pattern with Continue-As-New at 1000 events to prevent
// Temporal history size bloat.
func SarthiRouter(ctx workflow.Context, tenantID string) error {
	state := SarthiRouterState{
		TenantID:        tenantID,
		EventsProcessed: 0,
		SeenKeys:        make(map[string]bool),
	}

	routingTable := GetRoutingTable()

	// Get signal channel for incoming events
	signalChan := workflow.GetSignalChannel(ctx, "sarthi.events")

	for {
		// Guard: Continue-As-New before hitting Temporal history limits
		// This is critical for long-running workflows to prevent history size errors
		if state.EventsProcessed >= SarthiContinueAsNewThreshold {
			workflow.GetLogger(ctx).Info(
				"Triggering Continue-As-New",
				"events_processed", state.EventsProcessed,
				"tenant_id", state.TenantID,
			)
			return workflow.NewContinueAsNewError(ctx, SarthiRouter, state.TenantID)
		}

		// Receive next event from signal channel
		var envelope events.EventEnvelope
		signalChan.Receive(ctx, &envelope)

		// Idempotency: skip duplicate events based on idempotency key
		// This prevents double-processing of retried events
		if state.SeenKeys[envelope.IdempotencyKey] {
			workflow.GetLogger(ctx).Info(
				"Skipping duplicate event",
				"idempotency_key", envelope.IdempotencyKey,
				"event_type", envelope.EventType,
				"event_id", envelope.TraceID,
			)
			continue
		}
		state.SeenKeys[envelope.IdempotencyKey] = true
		state.EventsProcessed++

		// Route to appropriate workflows based on event type
		workflowNames, exists := routingTable[envelope.EventType]
		if !exists {
			// Unknown event - send to Dead Letter Queue for manual inspection
			workflow.GetLogger(ctx).Warn(
				"Unknown event type, sending to DLQ",
				"event_type", envelope.EventType,
				"source", envelope.Source,
				"tenant_id", envelope.TenantID,
			)

			// Execute DLQ activity with timeout
			ao := workflow.ActivityOptions{
				StartToCloseTimeout: 5 * time.Second,
				RetryPolicy: &temporal.RetryPolicy{
					InitialInterval:    time.Second,
					BackoffCoefficient: 2.0,
					MaximumAttempts:    3,
				},
			}
			ctxWithAO := workflow.WithActivityOptions(ctx, ao)
			workflow.ExecuteActivity(ctxWithAO, SendToDLQActivity, envelope)
			continue
		}

		// Spawn child workflows for each target workflow
		// Multi-route events (like TIME_TICK_WEEKLY) will spawn multiple children
		for _, workflowName := range workflowNames {
			var childWorkflow interface{}
			switch workflowName {
			case "RevenueWorkflow":
				childWorkflow = RevenueWorkflow
			case "CSWorkflow":
				childWorkflow = CSWorkflow
			case "PeopleWorkflow":
				childWorkflow = PeopleWorkflow
			case "FinanceWorkflow":
				childWorkflow = FinanceWorkflow
			case "ChiefOfStaffWorkflow":
				childWorkflow = ChiefOfStaffWorkflow
			default:
				workflow.GetLogger(ctx).Error(
					"Unknown workflow name in routing table",
					"workflow_name", workflowName,
					"event_type", envelope.EventType,
				)
				continue
			}

			// Create child workflow context with fire-and-forget semantics
			// ParentClosePolicyAbandon ensures child continues even if parent stops
			childCtx := workflow.WithChildOptions(ctx, workflow.ChildWorkflowOptions{
				WorkflowID:        fmt.Sprintf("child:%s:%s:%s", workflowName, envelope.TenantID, envelope.TraceID),
				TaskQueue:         "ai_task_queue",
				ParentClosePolicy: 1, // PARENT_CLOSE_POLICY_ABANDON
				RetryPolicy: &temporal.RetryPolicy{
					InitialInterval:    time.Second,
					BackoffCoefficient: 2.0,
					MaximumAttempts:    3,
				},
			})

			// Fire-and-forget: do NOT wait for child completion
			// This allows the router to continue processing events immediately
			_ = workflow.ExecuteChildWorkflow(childCtx, childWorkflow, envelope)

			workflow.GetLogger(ctx).Info(
				"Spawned child workflow",
				"event_type", envelope.EventType,
				"workflow_name", workflowName,
				"tenant_id", envelope.TenantID,
				"trace_id", envelope.TraceID,
			)
		}
	}
}

// RevenueWorkflow handles all revenue-related events (payments, subscriptions, CRM deals).
// This is a stub to be implemented in Phase 6.
func RevenueWorkflow(ctx workflow.Context, envelope events.EventEnvelope) error {
	workflow.GetLogger(ctx).Info(
		"RevenueWorkflow started",
		"event_type", envelope.EventType,
		"tenant_id", envelope.TenantID,
		"trace_id", envelope.TraceID,
	)
	// TODO: Implement RevenueWorkflow agent logic
	return nil
}

// CSWorkflow handles customer success events (signups, support tickets, engagement ticks).
// This is a stub to be implemented in Phase 6.
func CSWorkflow(ctx workflow.Context, envelope events.EventEnvelope) error {
	workflow.GetLogger(ctx).Info(
		"CSWorkflow started",
		"event_type", envelope.EventType,
		"tenant_id", envelope.TenantID,
		"trace_id", envelope.TraceID,
	)
	// TODO: Implement CSWorkflow agent logic
	return nil
}

// PeopleWorkflow handles HR/people operations (employee lifecycle, onboarding, checklists).
// This is a stub to be implemented in Phase 6.
func PeopleWorkflow(ctx workflow.Context, envelope events.EventEnvelope) error {
	workflow.GetLogger(ctx).Info(
		"PeopleWorkflow started",
		"event_type", envelope.EventType,
		"tenant_id", envelope.TenantID,
		"trace_id", envelope.TraceID,
	)
	// TODO: Implement PeopleWorkflow agent logic
	return nil
}

// FinanceWorkflow handles finance operations (expenses, bank webhooks, vendor invoices).
// This is a stub to be implemented in Phase 6.
func FinanceWorkflow(ctx workflow.Context, envelope events.EventEnvelope) error {
	workflow.GetLogger(ctx).Info(
		"FinanceWorkflow started",
		"event_type", envelope.EventType,
		"tenant_id", envelope.TenantID,
		"trace_id", envelope.TraceID,
	)
	// TODO: Implement FinanceWorkflow agent logic
	return nil
}

// ChiefOfStaffWorkflow handles executive-level events (monthly reviews, agent outputs, decisions).
// This is a stub to be implemented in Phase 6.
func ChiefOfStaffWorkflow(ctx workflow.Context, envelope events.EventEnvelope) error {
	workflow.GetLogger(ctx).Info(
		"ChiefOfStaffWorkflow started",
		"event_type", envelope.EventType,
		"tenant_id", envelope.TenantID,
		"trace_id", envelope.TraceID,
	)
	// TODO: Implement ChiefOfStaffWorkflow agent logic
	return nil
}

// SendToDLQActivity writes unknown/unroutable events to the dead letter queue.
// This allows manual inspection and debugging of unexpected events.
func SendToDLQActivity(ctx context.Context, envelope events.EventEnvelope) error {
	// TODO: Implement actual DLQ storage (PostgreSQL dead_letter_events table)
	// For now, log the event for debugging
	fmt.Printf("DLQ: Unknown event type=%q source=%q tenant=%q trace=%q\n",
		envelope.EventType, envelope.Source, envelope.TenantID, envelope.TraceID)
	return nil
}
