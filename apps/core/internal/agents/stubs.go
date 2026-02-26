package agents

import "context"

// TriageAgent stub for compilation
type TriageAgent struct{}

// NewTriageAgentFromEnv creates a stub triage agent
func NewTriageAgentFromEnv() *TriageAgent {
	return &TriageAgent{}
}

// Classify classifies feedback (stub)
func (a *TriageAgent) Classify(ctx context.Context, userID, text, source string) (interface{}, error) {
	return map[string]interface{}{
		"classification": "bug",
		"severity":       "medium",
		"confidence":     0.8,
	}, nil
}

// SpecResult represents a spec generation result
type SpecResult struct {
	Title       string
	Description string
	Type        string
	Severity    string
	Labels      []string
	Confidence  float64
}

// SpecAgent stub for compilation
type SpecAgent struct{}

// NewSpecAgentFromEnv creates a stub spec agent
func NewSpecAgentFromEnv() *SpecAgent {
	return &SpecAgent{}
}

// GenerateSpec generates a spec (stub)
func (a *SpecAgent) GenerateSpec(ctx context.Context, feedback string) (*SpecResult, error) {
	return &SpecResult{
		Title:       "Stub fix",
		Description: "Stub description",
		Type:        "bug",
		Severity:    "medium",
		Confidence:  0.8,
	}, nil
}
