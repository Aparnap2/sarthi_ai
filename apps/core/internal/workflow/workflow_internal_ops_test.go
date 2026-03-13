package workflow_test

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/suite"
	"go.temporal.io/sdk/testsuite"

	"iterateswarm-core/internal/workflow"
)

// InternalOpsWorkflowTestSuite is the test suite for internal ops workflows.
type InternalOpsWorkflowTestSuite struct {
	suite.Suite
	testsuite.WorkflowTestSuite
	env *testsuite.TestWorkflowEnvironment
}

func (s *InternalOpsWorkflowTestSuite) SetupTest() {
	s.env = s.NewTestWorkflowEnvironment()
	s.env.RegisterWorkflow(workflow.InternalOpsWorkflow)

	// Mock persist activity (common to all tests)
	s.env.OnActivity(workflow.PersistInternalOpsResult, mock.Anything, mock.Anything).
		Return(nil).Maybe()

	s.env.OnActivity(workflow.CreateHITLRecord, mock.Anything, mock.Anything).
		Return(nil).Maybe()
}

func (s *InternalOpsWorkflowTestSuite) AfterTest(_, _ string) {
	s.env.AssertExpectations(s.T())
}

func TestInternalOpsWorkflowSuite(t *testing.T) {
	suite.Run(t, new(InternalOpsWorkflowTestSuite))
}

// TestBankStatementWorkflow tests bank statement → Finance Desk flow
func (s *InternalOpsWorkflowTestSuite) TestBankStatementWorkflow() {
	// Override mock for this test
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskFinance),
			HITLLevel: getHITLLevelPtr(workflow.HITLLow),
		}, nil)

	s.env.OnActivity(workflow.ProcessFinanceOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessFinanceOpsOutput{
			Result: map[string]interface{}{
				"finding": "Cash runway: 6 months",
				"action":  "Review burn rate",
			},
			TasksCreated: []string{"task-1", "task-2"},
			AlertsSent:   []string{"alert-1"},
		}, nil)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-123",
		EventType: "bank_statement",
		EventPayload: map[string]interface{}{
			"balance": 500000,
			"currency": "INR",
		},
		ChannelID: "telegram-channel-123",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("finance", result.DeskRouted)
	s.NotNil(result.Result)
}

// TestNewHireWorkflow tests new hire → People Desk flow
func (s *InternalOpsWorkflowTestSuite) TestNewHireWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskPeople),
			HITLLevel: getHITLLevelPtr(workflow.HITLMedium),
		}, nil)

	s.env.OnActivity(workflow.ProcessPeopleOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessPeopleOpsOutput{
			Result: map[string]interface{}{
				"onboarding_status": "initiated",
				"tasks_assigned": 5,
			},
			TasksCreated: []string{"onboarding-task-1", "onboarding-task-2"},
			AlertsSent:   []string{},
		}, nil)

	// Simulate HITL approval
	s.env.RegisterDelayedCallback(func() {
		s.env.SignalWorkflow("hitl-approval", true)
	}, 1*time.Second)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-456",
		EventType: "new_hire",
		EventPayload: map[string]interface{}{
			"employee_name": "John Doe",
			"role": "Software Engineer",
			"start_date": "2026-03-15",
		},
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("people", result.DeskRouted)
	s.Equal(2, len(result.TasksCreated))
}

// TestContractUploadWorkflow tests contract upload → Legal Desk flow
func (s *InternalOpsWorkflowTestSuite) TestContractUploadWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskLegal),
			HITLLevel: getHITLLevelPtr(workflow.HITLHigh),
		}, nil)

	s.env.OnActivity(workflow.ProcessLegalOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessLegalOpsOutput{
			Result: map[string]interface{}{
				"contract_type": "Vendor Agreement",
				"expiry_date": "2027-03-15",
				"risk_level": "medium",
			},
			TasksCreated: []string{"review-contract"},
			AlertsSent:   []string{"expiry-alert"},
		}, nil)

	// Simulate HITL approval
	s.env.RegisterDelayedCallback(func() {
		s.env.SignalWorkflow("hitl-approval", true)
	}, 1*time.Second)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-789",
		EventType: "contract_uploaded",
		EventPayload: map[string]interface{}{
			"contract_name": "Vendor Agreement",
			"file_path": "/contracts/vendor-agreement.pdf",
		},
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("legal", result.DeskRouted)
	s.Equal("expiry-alert", result.AlertsSent[0])
}

// TestMeetingTranscriptWorkflow tests meeting transcript → Admin Desk flow
func (s *InternalOpsWorkflowTestSuite) TestMeetingTranscriptWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskAdmin),
			HITLLevel: getHITLLevelPtr(workflow.HITLLow),
		}, nil)

	s.env.OnActivity(workflow.ProcessAdminOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessAdminOpsOutput{
			Result: map[string]interface{}{
				"sop_generated": true,
				"action_items": 3,
			},
			TasksCreated: []string{"follow-up-1", "follow-up-2"},
			AlertsSent:   []string{},
		}, nil)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-000",
		EventType: "meeting_transcript",
		EventPayload: map[string]interface{}{
			"transcript":   "Meeting discussion content...",
			"participants": []interface{}{"Alice", "Bob"},
		},
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("admin", result.DeskRouted)
	s.Equal(2, len(result.TasksCreated))
}

// TestRevenueAnomalyWorkflow tests revenue anomaly → Intelligence Desk flow
func (s *InternalOpsWorkflowTestSuite) TestRevenueAnomalyWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskIntelligence),
			HITLLevel: getHITLLevelPtr(workflow.HITLMedium),
		}, nil)

	s.env.OnActivity(workflow.ProcessIntelligenceOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessIntelligenceOpsOutput{
			Result: map[string]interface{}{
				"anomaly_type": "revenue_spike",
				"confidence": 0.95,
				"recommendation": "Investigate source",
			},
			TasksCreated: []string{"investigate-anomaly"},
			AlertsSent:   []string{"cfo-alert"},
		}, nil)

	// Simulate HITL approval
	s.env.RegisterDelayedCallback(func() {
		s.env.SignalWorkflow("hitl-approval", true)
	}, 1*time.Second)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-111",
		EventType: "revenue_anomaly",
		EventPayload: map[string]interface{}{
			"current_revenue": 1000000,
			"expected_revenue": 500000,
			"variance_percent": 100,
		},
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("intelligence", result.DeskRouted)
	s.Equal("cfo-alert", result.AlertsSent[0])
}

// TestSaaSSubscriptionWorkflow tests SaaS subscription → IT Desk flow
func (s *InternalOpsWorkflowTestSuite) TestSaaSSubscriptionWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskIT),
			HITLLevel: getHITLLevelPtr(workflow.HITLLow),
		}, nil)

	s.env.OnActivity(workflow.ProcessITOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessITOpsOutput{
			Result: map[string]interface{}{
				"tool_name": "Slack",
				"monthly_cost": 5000,
				"utilization": 0.85,
			},
			TasksCreated: []string{"review-subscription"},
			AlertsSent:   []string{},
		}, nil)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-222",
		EventType: "saas_subscription",
		EventPayload: map[string]interface{}{
			"tool_name": "Slack",
			"cost": 5000,
			"seats": 10,
		},
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	s.Equal("it", result.DeskRouted)
}

// TestHITLRejectionWorkflow tests HITL rejection path
func (s *InternalOpsWorkflowTestSuite) TestHITLRejectionWorkflow() {
	s.env.OnActivity(workflow.RouteInternalEvent, mock.Anything, mock.Anything).
		Return(&workflow.RouteInternalEventOutput{
			DeskType:  getDeskTypePtr(workflow.DeskFinance),
			HITLLevel: getHITLLevelPtr(workflow.HITLHigh),
		}, nil)

	s.env.OnActivity(workflow.ProcessFinanceOps, mock.Anything, mock.Anything).
		Return(&workflow.ProcessFinanceOpsOutput{
			Result: map[string]interface{}{"status": "processed"},
		}, nil)

	// Simulate HITL rejection
	s.env.RegisterDelayedCallback(func() {
		s.env.SignalWorkflow("hitl-approval", false)
	}, 1*time.Second)

	var result *workflow.InternalOpsOutput
	s.env.ExecuteWorkflow(workflow.InternalOpsWorkflow, workflow.InternalOpsInput{
		FounderID: "founder-uuid-333",
		EventType: "bank_statement",
		EventPayload: map[string]interface{}{},
		ChannelID: "telegram-channel",
	})

	s.True(s.env.IsWorkflowCompleted())
	s.NoError(s.env.GetWorkflowError())
	s.NoError(s.env.GetWorkflowResult(&result))

	// Workflow should complete but action not taken due to rejection
	s.Equal("finance", result.DeskRouted)
}

// TestRoutingAccuracy tests that all event types route to correct desks
func (s *InternalOpsWorkflowTestSuite) TestRoutingAccuracy() {
	testCases := []struct {
		eventType  string
		expectedDesk workflow.DeskType
	}{
		{"bank_statement", workflow.DeskFinance},
		{"new_hire", workflow.DeskPeople},
		{"contract_uploaded", workflow.DeskLegal},
		{"revenue_anomaly", workflow.DeskIntelligence},
		{"saas_subscription", workflow.DeskIT},
		{"meeting_transcript", workflow.DeskAdmin},
	}

	for _, tc := range testCases {
		s.Run(tc.eventType, func() {
			// Test routing activity directly
			output, err := workflow.RouteInternalEvent(context.Background(), workflow.RouteInternalEventInput{
				EventType: tc.eventType,
				EventPayload: map[string]interface{}{},
			})
			s.NoError(err)
			s.Equal(tc.expectedDesk, *output.DeskType)
		})
	}
}

// Helper functions
func getDeskTypePtr(desk workflow.DeskType) *workflow.DeskType {
	return &desk
}

func getHITLLevelPtr(level workflow.HITLClassification) *workflow.HITLClassification {
	return &level
}
