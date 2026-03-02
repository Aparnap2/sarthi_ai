package agents

import "context"

// TriageResult represents the result of feedback classification.
type TriageResult struct {
	Classification string
	Severity       string
	Confidence     float64
	Reasoning      string
}

// TriageAgent stub for compilation
type TriageAgent struct{}

// NewTriageAgentFromEnv creates a stub triage agent
func NewTriageAgentFromEnv() *TriageAgent {
	return &TriageAgent{}
}

// Classify classifies feedback (stub)
func (a *TriageAgent) Classify(ctx context.Context, userID, text, source string) (*TriageResult, error) {
	return &TriageResult{
		Classification: "bug",
		Severity:       "medium",
		Confidence:     0.8,
		Reasoning:      "Stub classification result",
	}, nil
}

// SpecResult represents a spec generation result
type SpecResult struct {
	Title              string
	Description        string
	Type               string
	Severity           string
	Labels             []string
	Confidence         float64
	ReproductionSteps  []string
	AffectedComponents []string
	AcceptanceCriteria []string
}

// SpecAgent stub for compilation
type SpecAgent struct{}

// NewSpecAgentFromEnv creates a stub spec agent
func NewSpecAgentFromEnv() *SpecAgent {
	return &SpecAgent{}
}

// GenerateSpec generates a spec (stub)
// Parameters: ctx, userID, feedback, source, classification, severity, reasoning, confidence
func (a *SpecAgent) GenerateSpec(ctx context.Context, userID, feedback, source, classification, severity, reasoning string, confidence float64) (*SpecResult, error) {
	return &SpecResult{
		Title:       "Fix: " + feedback[:min(len(feedback), 50)],
		Description: "Stub description for: " + feedback,
		Type:        classification,
		Severity:    severity,
		Labels:      []string{"ai-generated", "bug"},
		Confidence:  confidence,
		ReproductionSteps: []string{
			"Step 1: Reproduce the issue",
			"Step 2: Observe the error",
		},
		AffectedComponents: []string{"core", "api"},
		AcceptanceCriteria: []string{
			"Issue is resolved",
			"Tests pass",
		},
	}, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
