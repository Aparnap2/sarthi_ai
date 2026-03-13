package workflow

import (
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

// InternalOpsInput is the input to the InternalOpsWorkflow.
type InternalOpsInput struct {
	FounderID   string                 `json:"founder_id"`
	EventType   string                 `json:"event_type"`
	EventPayload map[string]interface{} `json:"event_payload"`
	ChannelID   string                 `json:"channel_id,omitempty"`
}

// InternalOpsOutput contains the result of internal ops processing.
type InternalOpsOutput struct {
	DeskRouted   string                 `json:"desk_routed"`
	Result       map[string]interface{} `json:"result"`
	TasksCreated []string               `json:"tasks_created,omitempty"`
	AlertsSent   []string               `json:"alerts_sent,omitempty"`
}

// HITLClassification represents the human-in-the-loop classification level.
type HITLClassification string

const (
	HITLLow    HITLClassification = "LOW"
	HITLMedium HITLClassification = "MEDIUM"
	HITLHigh   HITLClassification = "HIGH"
)

// DeskType represents the type of desk handling the event.
type DeskType string

const (
	DeskFinance     DeskType = "finance"
	DeskPeople      DeskType = "people"
	DeskLegal       DeskType = "legal"
	DeskIntelligence DeskType = "intelligence"
	DeskIT          DeskType = "it"
	DeskAdmin       DeskType = "admin"
)

// InternalOpsWorkflow processes internal operations events through appropriate desks.
// This workflow handles all 6 desks: Finance, People, Legal, Intelligence, IT, Admin.
func InternalOpsWorkflow(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	// Set activity options with retry policy
	ao := workflow.ActivityOptions{
		StartToCloseTimeout: 5 * time.Minute,
		HeartbeatTimeout:    30 * time.Second,
		RetryPolicy: &temporal.RetryPolicy{
			InitialInterval:    time.Second,
			BackoffCoefficient: 2.0,
			MaximumInterval:    time.Minute,
			MaximumAttempts:    5,
		},
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	workflow.GetLogger(ctx).Info("starting internal ops workflow",
		"founder_id", input.FounderID,
		"event_type", input.EventType,
	)

	// Step 1: Route event to appropriate desk
	var deskType DeskType
	var hitlLevel HITLClassification

	err := workflow.ExecuteActivity(ctx, RouteInternalEvent, RouteInternalEventInput{
		EventType:   input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &RouteInternalEventOutput{
		DeskType:     &deskType,
		HITLLevel:    &hitlLevel,
	})
	if err != nil {
		workflow.GetLogger(ctx).Error("failed to route event", "error", err)
		return nil, err
	}

	workflow.GetLogger(ctx).Info("event routed",
		"desk", deskType,
		"hitl_level", hitlLevel,
	)

	// Step 2: Process with appropriate desk based on routing
	var result *InternalOpsOutput

	switch deskType {
	case DeskFinance:
		result, err = processFinanceDesk(ctx, input)
	case DeskPeople:
		result, err = processPeopleDesk(ctx, input)
	case DeskLegal:
		result, err = processLegalDesk(ctx, input)
	case DeskIntelligence:
		result, err = processIntelligenceDesk(ctx, input)
	case DeskIT:
		result, err = processITDesk(ctx, input)
	case DeskAdmin:
		result, err = processAdminDesk(ctx, input)
	default:
		return nil, temporal.NewNonRetryableApplicationError("unknown desk type", "InvalidDesk", nil)
	}

	if err != nil {
		workflow.GetLogger(ctx).Error("desk processing failed",
			"desk", deskType,
			"error", err,
		)
		return nil, err
	}

	result.DeskRouted = string(deskType)

	// Step 3: Apply HITL gate if needed (MEDIUM/HIGH classification)
	if hitlLevel == HITLMedium || hitlLevel == HITLHigh {
		err := applyHITLGate(ctx, input, result, hitlLevel)
		if err != nil {
			workflow.GetLogger(ctx).Error("HITL gate failed", "error", err)
			return nil, err
		}
	}

	// Step 4: Persist result to database
	err = workflow.ExecuteActivity(ctx, PersistInternalOpsResult, PersistInternalOpsResultInput{
		FounderID:   input.FounderID,
		EventType:   input.EventType,
		DeskType:    string(deskType),
		Result:      result.Result,
		TasksCreated: result.TasksCreated,
		HITLLevel:   string(hitlLevel),
	}).Get(ctx, nil)

	if err != nil {
		workflow.GetLogger(ctx).Warn("failed to persist result", "error", err)
		// Don't fail workflow on persistence error
	}

	workflow.GetLogger(ctx).Info("internal ops workflow completed",
		"desk", deskType,
		"hitl_level", hitlLevel,
		"tasks_created", len(result.TasksCreated),
	)

	return result, nil
}

// processFinanceDesk processes events through Finance Desk
func processFinanceDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessFinanceOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessFinanceOps, ProcessFinanceOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// processPeopleDesk processes events through People Desk
func processPeopleDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessPeopleOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessPeopleOps, ProcessPeopleOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// processLegalDesk processes events through Legal Desk
func processLegalDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessLegalOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessLegalOps, ProcessLegalOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// processIntelligenceDesk processes events through Intelligence Desk
func processIntelligenceDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessIntelligenceOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessIntelligenceOps, ProcessIntelligenceOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// processITDesk processes events through IT Desk
func processITDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessITOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessITOps, ProcessITOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// processAdminDesk processes events through Admin Desk
func processAdminDesk(ctx workflow.Context, input InternalOpsInput) (*InternalOpsOutput, error) {
	var result ProcessAdminOpsOutput
	err := workflow.ExecuteActivity(ctx, ProcessAdminOps, ProcessAdminOpsInput{
		FounderID:    input.FounderID,
		EventType:    input.EventType,
		EventPayload: input.EventPayload,
	}).Get(ctx, &result)

	if err != nil {
		return nil, err
	}

	return &InternalOpsOutput{
		Result:       result.Result,
		TasksCreated: result.TasksCreated,
		AlertsSent:   result.AlertsSent,
	}, nil
}

// applyHITLGate applies human-in-the-loop approval gate for MEDIUM/HIGH classification
func applyHITLGate(ctx workflow.Context, input InternalOpsInput, result *InternalOpsOutput, hitlLevel HITLClassification) error {
	// Create HITL record
	err := workflow.ExecuteActivity(ctx, CreateHITLRecord, CreateHITLRecordInput{
		FounderID:   input.FounderID,
		EventType:   input.EventType,
		DeskType:    result.DeskRouted,
		HITLLevel:   string(hitlLevel),
		Result:      result.Result,
		ChannelID:   input.ChannelID,
	}).Get(ctx, nil)

	if err != nil {
		return err
	}

	// Wait for approval signal
	signalChan := workflow.GetSignalChannel(ctx, "hitl-approval")
	var approved bool

	// Wait for signal with 48-hour timeout
	timedOut, err := workflow.AwaitWithTimeout(ctx, 48*time.Hour, func() bool {
		return signalChan.ReceiveAsync(&approved)
	})

	if err != nil {
		return err
	}

	if timedOut {
		workflow.GetLogger(ctx).Warn("HITL approval timed out")
		// Notify timeout
		_ = workflow.ExecuteActivity(ctx, NotifyHITLTimeout, NotifyHITLTimeoutInput{
			ChannelID:  input.ChannelID,
			IssueTitle: input.EventType,
			WorkflowID: input.FounderID,
		}).Get(ctx, nil)
		return nil
	}

	if !approved {
		workflow.GetLogger(ctx).Info("HITL approval rejected")
		return nil
	}

	workflow.GetLogger(ctx).Info("HITL approval received")
	return nil
}
