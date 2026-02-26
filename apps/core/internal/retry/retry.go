package retry

import "time"

// SimpleRetry provides simple retry functionality
type SimpleRetry struct {
	maxAttempts int
	delayMs     int
}

// NewSimpleRetry creates a new retry handler
func NewSimpleRetry(maxAttempts int, delayMs int) *SimpleRetry {
	return &SimpleRetry{
		maxAttempts: maxAttempts,
		delayMs:     delayMs,
	}
}

// Execute runs the function with retries
func (r *SimpleRetry) Execute(fn func() error) error {
	var lastErr error
	for i := 0; i < r.maxAttempts; i++ {
		if err := fn(); err == nil {
			return nil
		} else {
			lastErr = err
		}
		if i < r.maxAttempts-1 {
			time.Sleep(time.Duration(r.delayMs) * time.Millisecond)
		}
	}
	return lastErr
}
