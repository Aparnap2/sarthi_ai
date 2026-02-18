package workflow

import (
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

// FeedbackInput is the input to the FeedbackWorkflow.
type FeedbackInput struct {
	Text      string
	Source    string
	UserID    string
	ChannelID string
	RepoOwner string
	RepoName  string
}

// AnalyzeFeedbackOutput contains the result of AI analysis.
type AnalyzeFeedbackOutput struct {
	IsDuplicate bool
	Title       string
	Description string
	Labels      []string
	Severity    string
	IssueType   string
	Confidence  float64 // P3-1: Added confidence field from AI response
}

// SendDiscordApprovalInput is input for sending Discord approval request.
// P1-1 FIX: Changed from WorkflowRunID to WorkflowID to fix signal routing
type SendDiscordApprovalInput struct {
	ChannelID   string
	IssueTitle  string
	IssueBody   string
	IssueLabels []string
	Severity    string
	IssueType   string
	WorkflowID  string // Was WorkflowRunID - now uses WorkflowID for correct signal routing
}

// CreateGitHubIssueInput is input for creating a GitHub issue.
type CreateGitHubIssueInput struct {
	Title     string
	Body      string
	Labels    []string
	RepoOwner string
	RepoName  string
	Assignee  string
}

// FeedbackWorkflow is the main workflow for processing feedback.
func FeedbackWorkflow(ctx workflow.Context, input FeedbackInput) error {
	// Set activity options with retry policy
	ao := workflow.ActivityOptions{
		StartToCloseTimeout: 2 * time.Minute,
		HeartbeatTimeout:    30 * time.Second,
		RetryPolicy: &temporal.RetryPolicy{
			InitialInterval:    time.Second,
			BackoffCoefficient: 2.0,
			MaximumInterval:    time.Minute,
			MaximumAttempts:    3,
		},
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	// Channel for receiving signals (user approval)
	signalChan := workflow.GetSignalChannel(ctx, "user-action")

	var analyzeResult *AnalyzeFeedbackOutput

	// Step 1: Analyze feedback with AI (now using Go activities)
	activities := NewActivities()
	err := workflow.ExecuteActivity(ctx, activities.AnalyzeFeedback, AnalyzeFeedbackInput{
		Text:      input.Text,
		Source:    input.Source,
		UserID:    input.UserID,
		ChannelID: input.ChannelID,
	}).Get(ctx, &analyzeResult)
	if err != nil {
		return err
	}

	// If duplicate, skip to end
	if analyzeResult.IsDuplicate {
		return nil
	}

	// Step 2: Send approval request to Discord
	// P1-1 FIX: Use WorkflowID instead of RunID for correct signal routing
	workflowInfo := workflow.GetInfo(ctx)
	err = workflow.ExecuteActivity(ctx, activities.SendDiscordApproval, SendDiscordApprovalInput{
		ChannelID:   input.ChannelID,
		IssueTitle:  analyzeResult.Title,
		IssueBody:   analyzeResult.Description,
		IssueLabels: analyzeResult.Labels,
		Severity:    analyzeResult.Severity,
		IssueType:   analyzeResult.IssueType,
		WorkflowID:  workflowInfo.WorkflowExecution.ID, // Was RunID - now uses ID
	}).Get(ctx, nil)
	if err != nil {
		return err
	}

	// Step 3: Wait for user approval (signal with timeout)
	var signalValue interface{}
	signalReceived := false

	// Wait for signal with 5 minute timeout
	_, _ = workflow.AwaitWithTimeout(ctx, 5*time.Minute, func() bool {
		received := signalChan.ReceiveAsync(&signalValue)
		if received {
			signalReceived = true
			return true
		}
		return false
	})

	// Check if we received a signal or timed out
	approved := false
	if signalReceived {
		if s, ok := signalValue.(string); ok {
			approved = s == "approve"
		}
	}

	// Step 4: Handle approval/rejection
	if !approved {
		return nil
	}

	// Step 5: Create GitHub issue
	err = workflow.ExecuteActivity(ctx, activities.CreateGitHubIssue, CreateGitHubIssueInput{
		Title:     analyzeResult.Title,
		Body:      analyzeResult.Description,
		Labels:    analyzeResult.Labels,
		RepoOwner: input.RepoOwner,
		RepoName:  input.RepoName,
	}).Get(ctx, nil)

	return err
}
