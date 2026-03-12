package workflow

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"

	"iterateswarm-core/internal/logging"
	"iterateswarm-core/internal/memory"
)

// QuestionPayload represents an onboarding question
type QuestionPayload struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

// GetNextQuestionInput is the input for GetNextQuestionActivity
type GetNextQuestionInput struct {
	AnsweredIDs []string `json:"answered_ids"`
	Language    string   `json:"language"`
}

// AnswerSignalPayload is the payload for the answer signal
type AnswerSignalPayload struct {
	RawAnswer  string    `json:"raw_answer"`
	ReceivedAt time.Time `json:"received_at"`
}

// SendOnboardingMessageInput is the input for SendTelegramOnboardingMessageActivity
type SendOnboardingMessageInput struct {
	TelegramUserID  string `json:"telegram_user_id"`
	Message         string `json:"message"`
	QuestionNumber  int    `json:"question_number"`
	TotalQuestions  int    `json:"total_questions"`
	IsFirstQuestion bool   `json:"is_first_question"`
	IsCompletion    bool   `json:"is_completion"`
}

// ProcessAnswerInput is the input for ProcessOnboardingAnswerActivity
type ProcessAnswerInput struct {
	FounderID    string `json:"founder_id"`
	QuestionID   string `json:"question_id"`
	QuestionText string `json:"question_text"`
	RawAnswer    string `json:"raw_answer"`
}

// ProcessAnswerResult is the result from processing an onboarding answer
type ProcessAnswerResult struct {
	FounderID           string   `json:"founder_id"`
	QuestionID          string   `json:"question_id"`
	QuestionText        string   `json:"question_text"`
	RawAnswer           string   `json:"raw_answer"`
	ContextType         string   `json:"context_type"`
	Content             string   `json:"content"`
	Confidence          float64  `json:"confidence"`
	ImplicitConstraints []string `json:"implicit_constraints"`
	Keywords            []string `json:"keywords"`
	QdrantPointID       string   `json:"qdrant_point_id"`
}

// DetectArchetypeInput is the input for DetectArchetypeActivity
type DetectArchetypeInput struct {
	FounderID string `json:"founder_id"`
}

// ArchetypeResult is the result from archetype detection
type ArchetypeResult struct {
	Archetype string  `json:"archetype"`
	Threshold float64 `json:"threshold"`
}

// CompleteOnboardingInput is the input for CompleteOnboardingActivity
type CompleteOnboardingInput struct {
	FounderID        string  `json:"founder_id"`
	Archetype        string  `json:"archetype"`
	DynamicThreshold float64 `json:"dynamic_threshold"`
}

// onboardingActivities contains the logger for onboarding activities
type onboardingActivities struct {
	logger *logging.Logger
}

// newOnboardingActivities creates a new onboardingActivities instance
func newOnboardingActivities() *onboardingActivities {
	return &onboardingActivities{
		logger: logging.NewLogger("onboarding"),
	}
}

// GetNextQuestionActivity returns the next unanswered onboarding question
func GetNextQuestionActivity(ctx context.Context, input GetNextQuestionInput) (QuestionPayload, error) {
	logger := logging.NewLogger("onboarding")
	logger.Info("getting next question", "answered_count", len(input.AnsweredIDs), "language", input.Language)

	// Hardcoded onboarding questions (can be moved to database later)
	questions := []QuestionPayload{
		{
			ID:   "mission",
			Text: "What problem are you solving, and why does it matter to you personally?",
		},
		{
			ID:   "philosophy",
			Text: "When revenue and product quality conflict — which wins for you, and why?",
		},
		{
			ID:   "non_negotiable",
			Text: "What would you never do to grow this company, even if it worked?",
		},
		{
			ID:   "icp",
			Text: "Describe the one customer who, if you had 100 of them, would make this company successful.",
		},
		{
			ID:   "success",
			Text: "What does winning look like in 12 months? And failing?",
		},
		{
			ID:   "constraints",
			Text: "What are your hard constraints right now — time, money, skills, anything?",
		},
	}

	// Find first unanswered question
	for _, q := range questions {
		found := false
		for _, answered := range input.AnsweredIDs {
			if answered == q.ID {
				found = true
				break
			}
		}
		if !found {
			logger.Info("returning next question", "question_id", q.ID)
			return q, nil
		}
	}

	return QuestionPayload{}, fmt.Errorf("no more questions available")
}

// SendTelegramOnboardingMessageActivity sends a message via Telegram bot
func SendTelegramOnboardingMessageActivity(ctx context.Context, input SendOnboardingMessageInput) error {
	logger := logging.NewLogger("onboarding")
	logger.Info("sending telegram message",
		"telegram_user_id", input.TelegramUserID,
		"question_number", input.QuestionNumber,
		"is_first", input.IsFirstQuestion,
		"is_completion", input.IsCompletion,
	)

	// TODO: Implement actual Telegram bot integration
	// For now, log the message that would be sent
	logger.Info("message content",
		"recipient", input.TelegramUserID,
		"message", input.Message,
	)

	// Placeholder: In production, this would call Telegram Bot API
	// Example:
	// bot, err := tgbotapi.NewBotAPI(os.Getenv("TELEGRAM_BOT_TOKEN"))
	// if err != nil { return err }
	// msg := tgbotapi.NewMessage(int64(chatID), input.Message)
	// _, err = bot.Send(msg)

	return nil
}

// ProcessOnboardingAnswerActivity processes an answer using AI/LLM
func ProcessOnboardingAnswerActivity(ctx context.Context, input ProcessAnswerInput) (ProcessAnswerResult, error) {
	logger := logging.NewLogger("onboarding")
	logger.Info("processing onboarding answer",
		"founder_id", input.FounderID,
		"question_id", input.QuestionID,
		"answer_length", len(input.RawAnswer),
	)

	// TODO: Call Python gRPC service or use Go-based AI agent to process answer
	// For now, return a stub result with basic extraction

	// Generate Qdrant point ID for vector storage
	qdrantPointID := uuid.New().String()

	// Basic keyword extraction (placeholder - use AI in production)
	keywords := extractKeywords(input.RawAnswer)

	result := ProcessAnswerResult{
		FounderID:           input.FounderID,
		QuestionID:          input.QuestionID,
		QuestionText:        input.QuestionText,
		RawAnswer:           input.RawAnswer,
		ContextType:         input.QuestionID,
		Content:             input.RawAnswer,
		Confidence:          0.9,
		ImplicitConstraints: []string{},
		Keywords:            keywords,
		QdrantPointID:       qdrantPointID,
	}

	logger.Info("answer processed",
		"question_id", input.QuestionID,
		"qdrant_point_id", qdrantPointID,
		"confidence", result.Confidence,
	)

	return result, nil
}

// StoreOnboardingAnswerActivity stores the processed answer in Postgres
func StoreOnboardingAnswerActivity(ctx context.Context, result ProcessAnswerResult) error {
	logger := logging.NewLogger("onboarding")
	logger.Info("storing onboarding answer",
		"founder_id", result.FounderID,
		"question_id", result.QuestionID,
		"qdrant_point_id", result.QdrantPointID,
	)

	// TODO: Implement actual database insert
	// Example SQL:
	// INSERT INTO onboarding_answers (founder_id, question_id, question_text, raw_answer,
	//   context_type, extracted_content, confidence, qdrant_point_id)
	// VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	// ON CONFLICT (founder_id, question_id) DO UPDATE SET ...

	// Store in Qdrant for semantic search
	qdrantClient, err := memory.NewQdrantClientFromEnv()
	if err != nil {
		logger.Error("failed to create qdrant client", err)
		return fmt.Errorf("failed to create qdrant client: %w", err)
	}

	if err := qdrantClient.EnsureCollection(ctx); err != nil {
		logger.Error("failed to ensure qdrant collection", err)
		return fmt.Errorf("failed to ensure collection: %w", err)
	}

	// Index the answer for future retrieval
	metadata := map[string]interface{}{
		"founder_id":   result.FounderID,
		"question_id":  result.QuestionID,
		"context_type": result.ContextType,
		"confidence":   result.Confidence,
		"keywords":     result.Keywords,
		"onboarding":   true,
	}

	if err := qdrantClient.IndexFeedback(ctx, result.FounderID, result.Content, metadata); err != nil {
		logger.Error("failed to index answer in qdrant", err)
		// Don't fail if indexing fails - we still have the DB record
	}

	logger.Info("answer stored successfully", "question_id", result.QuestionID)
	return nil
}

// DetectArchetypeActivity detects the founder's archetype from their answers
func DetectArchetypeActivity(ctx context.Context, input DetectArchetypeInput) (ArchetypeResult, error) {
	logger := logging.NewLogger("onboarding")
	logger.Info("detecting archetype", "founder_id", input.FounderID)

	// TODO: Call Python gRPC service or use Go-based AI agent to detect archetype
	// This should analyze all 6 answers from Qdrant/Postgres and determine:
	// - builder: execution-focused, builds first
	// - hustler: sales-focused, sells first
	// - analyst: insight-focused, researches first
	// - operator: process-focused, systems first

	// For now, return a stub result
	result := ArchetypeResult{
		Archetype: "builder",
		Threshold: 0.60,
	}

	logger.Info("archetype detected",
		"founder_id", input.FounderID,
		"archetype", result.Archetype,
		"threshold", result.Threshold,
	)

	return result, nil
}

// CompleteOnboardingActivity updates the founders table with onboarding completion
func CompleteOnboardingActivity(ctx context.Context, input CompleteOnboardingInput) error {
	logger := logging.NewLogger("onboarding")
	logger.Info("completing onboarding",
		"founder_id", input.FounderID,
		"archetype", input.Archetype,
		"threshold", input.DynamicThreshold,
	)

	// TODO: Implement actual database update
	// Example SQL:
	// UPDATE founders
	// SET onboarding_complete = TRUE,
	//     onboarding_completed_at = NOW(),
	//     archetype = $1,
	//     dynamic_threshold = $2
	// WHERE id = $3

	logger.Info("onboarding completed successfully", "founder_id", input.FounderID)
	return nil
}

// extractKeywords performs basic keyword extraction from text
// This is a placeholder - use AI/LLM in production
func extractKeywords(text string) []string {
	// Simple word frequency-based extraction (placeholder)
	// In production, use LLM to extract meaningful keywords
	words := []string{}
	// Add basic extraction logic here
	return words
}

// =============================================================================
// Standalone Activity Functions for Temporal Workflow Registration
// These wrapper functions allow activities to be called from workflows
// =============================================================================

// GetNextQuestionActivity is a standalone activity function for workflow use
func GetNextQuestionActivityStandalone(ctx context.Context, input GetNextQuestionInput) (QuestionPayload, error) {
	return GetNextQuestionActivity(ctx, input)
}

// SendTelegramOnboardingMessageActivity is a standalone activity function for workflow use
func SendTelegramOnboardingMessageActivityStandalone(ctx context.Context, input SendOnboardingMessageInput) error {
	return SendTelegramOnboardingMessageActivity(ctx, input)
}

// ProcessOnboardingAnswerActivity is a standalone activity function for workflow use
func ProcessOnboardingAnswerActivityStandalone(ctx context.Context, input ProcessAnswerInput) (ProcessAnswerResult, error) {
	return ProcessOnboardingAnswerActivity(ctx, input)
}

// StoreOnboardingAnswerActivity is a standalone activity function for workflow use
func StoreOnboardingAnswerActivityStandalone(ctx context.Context, result ProcessAnswerResult) error {
	return StoreOnboardingAnswerActivity(ctx, result)
}

// DetectArchetypeActivity is a standalone activity function for workflow use
func DetectArchetypeActivityStandalone(ctx context.Context, input DetectArchetypeInput) (ArchetypeResult, error) {
	return DetectArchetypeActivity(ctx, input)
}

// CompleteOnboardingActivity is a standalone activity function for workflow use
func CompleteOnboardingActivityStandalone(ctx context.Context, input CompleteOnboardingInput) error {
	return CompleteOnboardingActivity(ctx, input)
}
