package api_test

import (
	"testing"

	"github.com/stretchr/testify/assert"

	"iterateswarm-core/internal/api"
	"iterateswarm-core/internal/db"
	"iterateswarm-core/internal/redpanda"
	"iterateswarm-core/internal/temporal"
)

func TestNewHandler(t *testing.T) {
	// Verify that NewHandler correctly accepts dependencies
	// even if they are nil (checking struct initialization)
	repo := db.NewRepository(nil)
	var rp *redpanda.Client
	var tm *temporal.Client

	handler := api.NewHandler(rp, tm, repo)
	assert.NotNil(t, handler)
}

// TestParseCustomID tests the custom_id parsing with validation
// Issue: P2-1 - Input validation gaps for interaction payload parsing
func TestParseCustomID(t *testing.T) {
	testCases := []struct {
		name           string
		customID       string
		expectError    bool
		expectedAction string
		expectedID     string
		description    string
	}{
		{
			name:           "Valid approve format with underscore",
			customID:       "approve_feedback-123",
			expectError:    false,
			expectedAction: "approve",
			expectedID:     "feedback-123",
			description:    "Standard valid format with underscore separator",
		},
		{
			name:           "Valid reject format with underscore",
			customID:       "reject_feedback-456",
			expectError:    false,
			expectedAction: "reject",
			expectedID:     "feedback-456",
			description:    "Valid reject action",
		},
		{
			name:           "Valid colon format (future-proofing)",
			customID:       "approve:workflow-123",
			expectError:    false,
			expectedAction: "approve",
			expectedID:     "workflow-123",
			description:    "Colon separator format",
		},
		{
			name:        "Empty custom_id",
			customID:    "",
			expectError: true,
			description: "Should reject empty custom_id",
		},
		{
			name:        "Only action, no ID",
			customID:    "approve_",
			expectError: true,
			description: "Missing workflow ID after separator",
		},
		{
			name:        "Only ID, no action",
			customID:    "_feedback-123",
			expectError: true,
			description: "Missing action before separator",
		},
		{
			name:        "No separator",
			customID:    "approvefeedback-123",
			expectError: true,
			description: "Missing separator",
		},
		{
			name:        "Invalid action",
			customID:    "delete_feedback-123",
			expectError: true,
			description: "Action not in allowed set (approve/reject)",
		},
		{
			name:        "Too many parts with underscore",
			customID:    "approve_feedback_123_extra",
			expectError: true,
			description: "More than 2 parts when split by underscore",
		},
		{
			name:        "XSS attempt",
			customID:    "<script>_feedback-123",
			expectError: true,
			description: "XSS attempt in action part",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			action, workflowID, err := api.ParseCustomID(tc.customID)

			if tc.expectError {
				assert.Error(t, err, tc.description)
				assert.Empty(t, action, "Action should be empty on error")
				assert.Empty(t, workflowID, "WorkflowID should be empty on error")
			} else {
				assert.NoError(t, err, tc.description)
				assert.Equal(t, tc.expectedAction, action, "Action mismatch")
				assert.Equal(t, tc.expectedID, workflowID, "WorkflowID mismatch")
			}
		})
	}
}

// TestParseCustomIDAllowedActions tests that only specific actions are allowed
func TestParseCustomIDAllowedActions(t *testing.T) {
	allowedActions := []string{"approve", "reject"}
	invalidActions := []string{"delete", "update", "create", "", "APPROVE", "Approve", "reject"}

	for _, action := range allowedActions {
		t.Run("Valid action: "+action, func(t *testing.T) {
			customID := action + "_workflow-123"
			parsedAction, _, err := api.ParseCustomID(customID)
			assert.NoError(t, err)
			assert.Equal(t, action, parsedAction)
		})
	}

	for _, action := range invalidActions {
		if action == "reject" {
			// Skip reject as it's valid
			continue
		}
		t.Run("Invalid action: "+action, func(t *testing.T) {
			customID := action + "_workflow-123"
			_, _, err := api.ParseCustomID(customID)
			assert.Error(t, err, "Should reject invalid action: %s", action)
		})
	}
}
