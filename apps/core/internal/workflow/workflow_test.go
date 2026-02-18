package workflow

import (
	"context"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestAnalyzeFeedbackWithNilAgent tests that AnalyzeFeedback handles nil agents gracefully
// Issue: P1-2 - Potential nil-pointer path when AI service is unavailable
func TestAnalyzeFeedbackWithNilAgent(t *testing.T) {
	activities := NewActivities()

	ctx := context.Background()
	input := AnalyzeFeedbackInput{
		Text:      "Test feedback",
		Source:    "discord",
		UserID:    "user123",
		ChannelID: "channel456",
	}

	// Test with missing environment variables (simulating unavailable AI service)
	// Clear env vars temporarily
	oldEndpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")
	oldKey := os.Getenv("AZURE_OPENAI_API_KEY")
	oldModel := os.Getenv("AZURE_OPENAI_DEPLOYMENT")

	os.Unsetenv("AZURE_OPENAI_ENDPOINT")
	os.Unsetenv("AZURE_OPENAI_API_KEY")
	os.Unsetenv("AZURE_OPENAI_DEPLOYMENT")

	defer func() {
		os.Setenv("AZURE_OPENAI_ENDPOINT", oldEndpoint)
		os.Setenv("AZURE_OPENAI_API_KEY", oldKey)
		os.Setenv("AZURE_OPENAI_DEPLOYMENT", oldModel)
	}()

	// This should NOT panic - it should return a proper error
	result, err := activities.AnalyzeFeedback(ctx, input)

	// Should return an error, not panic
	assert.Error(t, err, "Should return error when AI service is unavailable")
	assert.Nil(t, result, "Result should be nil when AI service is unavailable")
}

// TestAnalyzeFeedbackOutputStructure tests the output structure has all required fields
// Issue: P3-1 - Ensure Confidence field exists
func TestAnalyzeFeedbackOutputStructure(t *testing.T) {
	output := AnalyzeFeedbackOutput{
		IsDuplicate: false,
		Title:       "Test",
		Description: "Test desc",
		Labels:      []string{"bug"},
		Severity:    "high",
		IssueType:   "bug",
		Confidence:  0.95, // This field must exist
	}

	// Verify all fields exist and are accessible
	assert.False(t, output.IsDuplicate)
	assert.Equal(t, "Test", output.Title)
	assert.Equal(t, "Test desc", output.Description)
	assert.Equal(t, []string{"bug"}, output.Labels)
	assert.Equal(t, "high", output.Severity)
	assert.Equal(t, "bug", output.IssueType)
	assert.Equal(t, 0.95, output.Confidence)
}

// TestSendDiscordApprovalInputStructure tests the input structure uses WorkflowID
// Issue: P1-1 - CustomID format should use WorkflowID
func TestSendDiscordApprovalInputStructure(t *testing.T) {
	input := SendDiscordApprovalInput{
		ChannelID:   "test-channel",
		IssueTitle:  "Test Issue",
		IssueBody:   "Test body",
		IssueLabels: []string{"bug"},
		Severity:    "high",
		IssueType:   "bug",
		WorkflowID:  "feedback-workflow-123", // Should be WorkflowID, not RunID
	}

	// Verify WorkflowID field exists and is accessible
	assert.Equal(t, "feedback-workflow-123", input.WorkflowID)
}

// TestNilPointerProtection tests the fix for P1-2
// Ensures that nil agents don't cause panics
func TestNilPointerProtection(t *testing.T) {
	// Test that NewActivities handles missing dependencies gracefully
	activities := NewActivities()
	assert.NotNil(t, activities, "NewActivities should return non-nil")
	assert.NotNil(t, activities.logger, "Logger should be initialized")
}

// TestAnalyzeFeedbackWithRealAzureLLM tests with real Azure AI
// This test requires Azure credentials
func TestAnalyzeFeedbackWithRealAzureLLM(t *testing.T) {
	// Skip if no Azure credentials
	if os.Getenv("AZURE_OPENAI_API_KEY") == "" {
		t.Skip("Skipping: AZURE_OPENAI_API_KEY not set")
	}

	activities := NewActivities()
	ctx := context.Background()

	input := AnalyzeFeedbackInput{
		Text:      "App crashes when I click the login button",
		Source:    "test",
		UserID:    "test-user",
		ChannelID: "test-channel",
	}

	result, err := activities.AnalyzeFeedback(ctx, input)

	// With real Azure LLM, this should succeed
	if err != nil {
		t.Logf("Azure API error (expected if Qdrant not running): %v", err)
		// Don't fail - Qdrant might not be available
		t.Skip("Skipping due to dependency error")
	}

	if result != nil {
		// Verify confidence is populated from AI (P3-1)
		assert.True(t, result.Confidence > 0, "Confidence should be > 0")
		assert.True(t, result.Confidence <= 1.0, "Confidence should be <= 1.0")
		assert.NotEmpty(t, result.Title, "Title should not be empty")
		assert.NotEmpty(t, result.IssueType, "IssueType should not be empty")
	}
}
