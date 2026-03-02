package retry

import (
	"fmt"
	"time"
)

// Retrier provides simple retry functionality
type Retrier struct {
	maxAttempts int
	delayMs     int
}

// NewRetrier creates a new retry handler
func NewRetrier(maxAttempts int, delayMs int) *Retrier {
	return &Retrier{
		maxAttempts: maxAttempts,
		delayMs:     delayMs,
	}
}

// Execute runs the function with retries
func (r *Retrier) Execute(fn func() error) error {
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

// SimpleRetry is a convenience function that executes a function with default retry settings
func SimpleRetry(fn func() error) error {
	return RetryWithConfig(fn, 3, 100)
}

// RetryWithConfig executes a function with custom retry settings
func RetryWithConfig(fn func() error, maxAttempts, delayMs int) error {
	var lastErr error
	for i := 0; i < maxAttempts; i++ {
		if err := fn(); err == nil {
			return nil
		} else {
			lastErr = err
		}
		if i < maxAttempts-1 {
			time.Sleep(time.Duration(delayMs) * time.Millisecond)
		}
	}
	return fmt.Errorf("after %d attempts: %w", maxAttempts, lastErr)
}
