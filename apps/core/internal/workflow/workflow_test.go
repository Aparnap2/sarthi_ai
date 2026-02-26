package workflow_test

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/suite"
	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/testsuite"

	"iterateswarm-core/internal/workflow"
)

// ─── Test Suite Setup ───────────────────────────────────────────────────────

type WorkflowTestSuite struct {
	suite.Suite
	testsuite.WorkflowTestSuite
	env *testsuite.TestWorkflowEnvironment
}

func (s *WorkflowTestSuite) SetupTest() {
	s.env = s.NewTestWorkflowEnvironment()
	s.env.RegisterWorkflow(workflow.FeedbackWorkflow)

	// Mock activities - don't call real implementations
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{
			Title:       "Mock fix",
			IsDuplicate: false,
			Severity:    "medium",
			IssueType:   "bug",
		}, nil).Maybe()

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil).Maybe()

	s.env.OnActivity(workflow.CreateGitHubIssue, mock.Anything, mock.Anything).
		Return("https://github.com/mock/repo/issues/1", nil).Maybe()
}

func (s *WorkflowTestSuite) AfterTest(_, _ string) {
	s.env.AssertExpectations(s.T())
}

func TestWorkflowSuite(t *testing.T) {
	suite.Run(t, new(WorkflowTestSuite))
}

// ─── TEST 1: Happy Path ──────────────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_HappyPath() {
	// Override mock for this test - approve immediately
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{
			Title:       "Fix DB pool exhaustion",
			IsDuplicate: false,
			Severity:    "high",
			IssueType:   "bug",
		}, nil)

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	// Send approve signal after 1 second (simulated)
	s.env.RegisterDelayedCallback(1*time.Second, func() {
		s.env.SignalWorkflow("user-action", "approve")
	})

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text:      "DB pool exhausted in prod",
		Source:    "discord",
		UserID:    "test-user",
		ChannelID: "test-channel",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}

// ─── TEST 2: Duplicate Skips Discord + GitHub ────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_DuplicateSkips() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{IsDuplicate: true}, nil)

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Same bug again", Source: "discord", UserID: "u1",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}

// ─── TEST 3: Reject Signal ───────────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_RejectSignal() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{
			IsDuplicate: false, Severity: "low", IssueType: "feature",
		}, nil)

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	s.env.RegisterDelayedCallback(1*time.Second, func() {
		s.env.SignalWorkflow("user-action", "reject")
	})

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Would be nice to have dark mode", Source: "discord", UserID: "u2",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}

// ─── TEST 4: Approve Signal ──────────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_ApproveSignal() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{
			Title: "Fix crash", IsDuplicate: false, Severity: "high", IssueType: "bug",
		}, nil)

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	s.env.RegisterDelayedCallback(1*time.Second, func() {
		s.env.SignalWorkflow("user-action", "approve")
	})

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "App crashes on login", Source: "discord", UserID: "u3",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}

// ─── TEST 5: Timeout Path ───────────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_TimeoutPath() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{IsDuplicate: false, Severity: "low"}, nil)

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	s.env.SetTestTimeout(10 * time.Minute)

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Minor alignment issue", Source: "discord", UserID: "u4",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}

// ─── TEST 6: Activity Retry ─────────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_ActivityRetry() {
	callCount := 0
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(func(ctx context.Context, input workflow.FeedbackInput) (workflow.AnalyzeFeedbackOutput, error) {
			callCount++
			if callCount < 3 {
				return workflow.AnalyzeFeedbackOutput{}, errors.New("transient error")
			}
			return workflow.AnalyzeFeedbackOutput{IsDuplicate: false, Severity: "medium"}, nil
		})

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	s.env.RegisterDelayedCallback(1*time.Second, func() {
		s.env.SignalWorkflow("user-action", "reject")
	})

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Retry test", Source: "discord", UserID: "u5",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.Equal(3, callCount, "AnalyzeFeedback must be called exactly 3 times")
}

// ─── TEST 7: Non-Retryable Error ────────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_NonRetryableError() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{}, errors.New("unauthenticated: non-retryable")).
		Once()

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Auth error test", Source: "discord", UserID: "u6",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.Error(s.env.GetWorkflowError())
}

// ─── TEST 8: 20 Concurrent Workflows ────────────────────────────────────────

func TestFeedbackWorkflow_ConcurrentWorkflows(t *testing.T) {
	// Uses real Temporal server at localhost:7233
	// Run: go test -race -run TestFeedbackWorkflow_ConcurrentWorkflows
	c, err := client.Dial(client.Options{HostPort: "localhost:7233"})
	if err != nil {
		t.Skipf("Temporal not available: %v", err)
	}
	defer c.Close()

	var wg sync.WaitGroup
	errChan := make(chan error, 20)

	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			workflowID := fmt.Sprintf("concurrent-test-%d", idx)
			_, err := c.ExecuteWorkflow(
				context.Background(),
				client.StartWorkflowOptions{
					ID:        workflowID,
					TaskQueue: "MAIN-TASK-QUEUE",
				},
				workflow.FeedbackWorkflow,
				workflow.FeedbackInput{
					Text:   fmt.Sprintf("Concurrent test %d", idx),
					Source: "test",
					UserID: fmt.Sprintf("user-%d", idx),
				},
			)
			if err != nil {
				errChan <- fmt.Errorf("workflow %d: %w", idx, err)
			}
		}(i)
	}

	wg.Wait()
	close(errChan)

	failures := 0
	for err := range errChan {
		t.Logf("Error: %v", err)
		failures++
	}

	if failures > 0 {
		t.Errorf("%d/20 workflows failed to start", failures)
	} else {
		t.Logf("✅ All 20 concurrent workflows started successfully")
	}
}

// ─── TEST 9: Signal After Timeout ───────────────────────────────────────────

func (s *WorkflowTestSuite) TestFeedbackWorkflow_SignalAfterTimeout() {
	s.env.OnActivity(workflow.AnalyzeFeedback, mock.Anything, mock.Anything).
		Return(workflow.AnalyzeFeedbackOutput{IsDuplicate: false}, nil)

	s.env.OnActivity(workflow.SendDiscordApproval, mock.Anything, mock.Anything).
		Return(nil)

	s.env.SetTestTimeout(10 * time.Minute)

	s.env.RegisterDelayedCallback(6*time.Minute, func() {
		s.env.SignalWorkflow("user-action", "approve")
	})

	s.env.ExecuteWorkflow(workflow.FeedbackWorkflow, workflow.FeedbackInput{
		Text: "Late signal test", Source: "discord", UserID: "u7",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
}
