package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/segmentio/kafka-go"
	"go.temporal.io/sdk/client"
	"iterateswarm-core/internal/workflow"
)

// FeedbackEvent represents a feedback event from the message queue.
type FeedbackEvent struct {
	FeedbackID string `json:"feedback_id"`
	Text       string `json:"text"`
	Source     string `json:"source"`
	UserID     string `json:"user_id"`
	ChannelID  string `json:"channel_id"`
	TeamID     string `json:"team_id"`
	Timestamp  string `json:"timestamp"`
}

func main() {
	// Read configuration from environment
	kafkaBrokers := os.Getenv("KAFKA_BROKERS")
	if kafkaBrokers == "" {
		kafkaBrokers = "localhost:9094"
	}

	temporalAddress := os.Getenv("TEMPORAL_ADDRESS")
	if temporalAddress == "" {
		temporalAddress = "localhost:7233"
	}

	log.Printf("===========================================")
	log.Printf("Starting IterateSwarm Redpanda Consumer...")
	log.Printf("===========================================")
	log.Printf("Kafka Brokers: %s", kafkaBrokers)
	log.Printf("Temporal Address: %s", temporalAddress)
	log.Printf("Topic: feedback-events")
	log.Printf("===========================================")

	// Connect to Temporal with retry
	var temporalClient client.Client
	var err error
	maxRetries := 5
	retryDelay := 2 * time.Second

	for i := 0; i < maxRetries; i++ {
		temporalClient, err = client.Dial(client.Options{
			HostPort: temporalAddress,
		})
		if err == nil {
			log.Println("✓ Connected to Temporal")
			break
		}
		log.Printf("⚠ Failed to connect to Temporal (attempt %d/%d): %v", i+1, maxRetries, err)
		if i < maxRetries-1 {
			time.Sleep(retryDelay)
		}
	}
	if err != nil {
		log.Fatalf("✗ Failed to connect to Temporal after %d attempts: %v", maxRetries, err)
	}
	defer temporalClient.Close()

	// Connect to Redpanda (Kafka) with retry
	var reader *kafka.Reader
	for i := 0; i < maxRetries; i++ {
		reader = kafka.NewReader(kafka.ReaderConfig{
			Brokers:  []string{kafkaBrokers},
			Topic:    "feedback-events",
			GroupID:  "iterateswarm-consumer-group",
			MinBytes: 10e3, // 10KB
			MaxBytes: 10e6, // 10MB
		})
		// Test connection
		_, err := reader.FetchMessage(context.Background())
		if err == nil {
			// Put the message back by committing offset
			reader.CommitMessages(context.Background())
			log.Println("✓ Connected to Redpanda")
			break
		}
		log.Printf("⚠ Failed to connect to Redpanda (attempt %d/%d): %v", i+1, maxRetries, err)
		reader.Close()
		if i < maxRetries-1 {
			time.Sleep(retryDelay)
		}
	}
	if err != nil {
		log.Fatalf("✗ Failed to connect to Redpanda after %d attempts: %v", maxRetries, err)
	}
	defer reader.Close()
	log.Println("✓ Listening on topic: feedback-events")
	log.Printf("===========================================")
	log.Println("Consumer ready - waiting for messages...")
	log.Printf("===========================================")

	// Handle graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		log.Println("\n⚠ Shutting down consumer...")
		cancel()
	}()

	// Statistics
	messageCount := 0
	errorCount := 0
	successCount := 0

	// Consume messages
	for {
		select {
		case <-ctx.Done():
			log.Printf("===========================================")
			log.Printf("Consumer shutdown complete")
			log.Printf("Total messages: %d, Success: %d, Errors: %d", messageCount, successCount, errorCount)
			log.Printf("===========================================")
			return
		default:
			// Set a timeout for fetching messages
			fetchCtx, fetchCancel := context.WithTimeout(ctx, 5*time.Second)
			msg, err := reader.FetchMessage(fetchCtx)
			fetchCancel()

			if err != nil {
				if ctx.Err() != nil {
					return
				}
				if err == context.DeadlineExceeded {
					// No message available, continue waiting
					continue
				}
				log.Printf("⚠ Failed to fetch message: %v", err)
				errorCount++
				continue
			}

			messageCount++
			log.Printf("➤ Received message (offset: %d, partition: %d)", msg.Offset, msg.Partition)

			var event FeedbackEvent
			if err := json.Unmarshal(msg.Value, &event); err != nil {
				log.Printf("✗ Failed to unmarshal message: %v", err)
				errorCount++
				// Commit anyway to avoid poison pill
				if err := reader.CommitMessages(ctx, msg); err != nil {
					log.Printf("⚠ Failed to commit offset: %v", err)
				}
				continue
			}

			log.Printf("  Feedback ID: %s", event.FeedbackID)
			log.Printf("  Source: %s", event.Source)
			log.Printf("  User ID: %s", event.UserID)
			log.Printf("  Text: %s", truncateString(event.Text, 100))

			// Start Temporal workflow
			workflowID := fmt.Sprintf("feedback-workflow-%s", event.FeedbackID)
			workflowOptions := client.StartWorkflowOptions{
				ID:        workflowID,
				TaskQueue: "GO_TASK_QUEUE",  // Use separate queue for Go-based activities
			}

			workflowInput := workflow.FeedbackInput{
				Text:      event.Text,
				Source:    event.Source,
				UserID:    event.UserID,
				ChannelID: event.ChannelID,
				RepoOwner: os.Getenv("GITHUB_OWNER"),
				RepoName:  os.Getenv("GITHUB_REPO"),
			}

			log.Printf("➤ Starting Temporal workflow: %s", workflowID)
			workflowRun, err := temporalClient.ExecuteWorkflow(ctx, workflowOptions, workflow.FeedbackWorkflow, workflowInput)
			if err != nil {
				log.Printf("✗ Failed to start workflow: %v", err)
				errorCount++
				// Don't commit - let it retry
				continue
			}

			log.Printf("✓ Started workflow: %s (run: %s)", workflowRun.GetID(), workflowRun.GetRunID())
			successCount++

			// Commit offset
			if err := reader.CommitMessages(ctx, msg); err != nil {
				log.Printf("⚠ Failed to commit offset: %v", err)
			}
		}
	}
}

// truncateString truncates a string to the specified max length.
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
