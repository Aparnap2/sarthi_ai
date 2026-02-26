package memory

import "context"

// QdrantClient stub for compilation
type QdrantClient struct{}

// NewQdrantClientFromEnv creates a stub Qdrant client
func NewQdrantClientFromEnv() (*QdrantClient, error) {
	return &QdrantClient{}, nil
}

// Close closes the stub client
func (c *QdrantClient) Close() {}

// CheckDuplicate checks for duplicate feedback (stub)
func (c *QdrantClient) CheckDuplicate(ctx context.Context, text string) (bool, float64, error) {
	return false, 0.0, nil
}

// EnsureCollection ensures the collection exists (stub)
func (c *QdrantClient) EnsureCollection(ctx context.Context) error {
	return nil
}
