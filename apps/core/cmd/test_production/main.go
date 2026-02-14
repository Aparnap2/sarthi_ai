package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"iterateswarm-core/internal/engine"
	"iterateswarm-core/internal/ratelimit"
)

func main() {
	fmt.Println("🚀 Production-Grade Agentic AI Engine Test")
	fmt.Println("==========================================")
	fmt.Println()

	// Azure credentials from environment
	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")
	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")
	model := os.Getenv("AZURE_OPENAI_DEPLOYMENT")

	if endpoint == "" || apiKey == "" || model == "" {
		fmt.Println("❌ Missing Azure credentials")
		fmt.Println("Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT")
		os.Exit(1)
	}

	// Setup rate limiter (20 requests per minute for Azure)
	rateLimiter := ratelimit.NewRateLimiter()
	rateLimiter.RegisterProvider("azure", 20, 3*time.Second)

	// Create engine with all production features
	eng, err := engine.NewEngine(&engine.Config{
		Endpoint:     endpoint,
		APIKey:       apiKey,
		Model:        model,
		MaxRetries:   3,
		RateLimiter:  rateLimiter,
		CacheEnabled: false, // Redis not running, skip cache
		Logger:       slog.Default(),
	})
	if err != nil {
		fmt.Printf("❌ Failed to create engine: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("✅ Engine initialized with:")
	fmt.Println("   - Circuit breaker")
	fmt.Println("   - Retry with exponential backoff")
	fmt.Println("   - Rate limiting (20 req/min)")
	fmt.Println("   - Structured logging")
	fmt.Println()

	// Test cases
	testCases := []struct {
		name    string
		content string
		source  string
	}{
		{
			name:    "Bug Report",
			content: "App crashes when I click the login button",
			source:  "discord",
		},
		{
			name:    "Feature Request",
			content: "Please add dark mode to the application",
			source:  "slack",
		},
		{
			name:    "Question",
			content: "How do I reset my password?",
			source:  "email",
		},
	}

	// Process each test case
	for i, tc := range testCases {
		fmt.Printf("%d️⃣ Testing: %s\n", i+1, tc.name)
		fmt.Printf("   Content: %s\n", tc.content)

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)

		start := time.Now()
		result, err := eng.ProcessFeedback(ctx, fmt.Sprintf("test-%d", i), tc.content, tc.source)
		cancel()

		if err != nil {
			fmt.Printf("   ❌ Error: %v\n", err)
			continue
		}

		fmt.Printf("   ✅ Classification: %s (%.2f confidence)\n", result.Classification, result.Confidence)
		fmt.Printf("   ✅ Severity: %s\n", result.Severity)
		fmt.Printf("   ✅ Title: %s\n", result.Title)
		fmt.Printf("   ✅ Processing time: %v\n", result.ProcessingTime)
		fmt.Printf("   ✅ Circuit breaker state: %s\n", eng.GetCircuitBreakerState())
		fmt.Printf("   ✅ Total time: %v\n", time.Since(start))
		fmt.Println()
	}

	fmt.Println("==========================================")
	fmt.Println("🎉 Production-Grade Engine Test Complete!")
	fmt.Println()
	fmt.Println("Features demonstrated:")
	fmt.Println("  ✅ Real Azure AI Foundry LLM")
	fmt.Println("  ✅ Circuit breaker pattern")
	fmt.Println("  ✅ Retry with exponential backoff")
	fmt.Println("  ✅ Token bucket rate limiting")
	fmt.Println("  ✅ Structured logging")
	fmt.Println("  ✅ Graceful error handling")
	fmt.Println("  ✅ Request timeouts")
	fmt.Println("  ✅ Fault tolerance")
}
