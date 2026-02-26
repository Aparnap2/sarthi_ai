package workflow

import (
	"context"
)

// Stub types for compilation - these are placeholders for missing packages

// From memory package
type QdrantClient struct{}

func NewQdrantClientFromEnv() (*QdrantClient, error) {
	return &QdrantClient{}, nil
}

func (c *QdrantClient) Close() {}

// From agents package
type TriageAgent struct{}
type SpecResult struct {
	Title       string
	Description string
	Type        string
	Severity    string
	Labels      []string
	Confidence  float64
}

func NewTriageAgentFromEnv() *TriageAgent {
	return &TriageAgent{}
}

func NewSpecAgentFromEnv() interface{} {
	return struct{}{}
}

// From retry package
type SimpleRetry struct{}

func NewSimpleRetry(maxAttempts int, delayMs int) *SimpleRetry {
	return &SimpleRetry{}
}

func (r *SimpleRetry) Execute(fn func() error) error {
	return fn()
}

// Additional stub types needed by activities
type DiscordApprovalInput struct {
	TaskID  string
	Title   string
	Content string
	RunID   string
}
