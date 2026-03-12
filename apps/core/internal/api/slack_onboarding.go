package api

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/google/uuid"
	"iterateswarm-core/internal/logging"
)

// OnboardingQuestions defines the 6-question onboarding flow
var OnboardingQuestions = []struct {
	ID          string `json:"id"`
	Text        string `json:"text"`
	ContextType string `json:"context_type"`
}{
	{"mission", "What problem are you solving, and why does it matter to you personally?", "mission"},
	{"philosophy_money", "When revenue and product quality conflict, which wins for you — and why?", "philosophy"},
	{"non_negotiable", "What would you never do to grow this company, even if it worked?", "non_negotiable"},
	{"icp", "Describe the one customer who, if you had 100 of them, would make this company successful.", "icp"},
	{"success", "What does winning look like in 12 months? And failing?", "goal"},
	{"constraints", "What are your hard constraints right now — time, money, skills, anything?", "constraint"},
}

// OnboardingResult represents the result of processing an onboarding answer
type OnboardingResult struct {
	QuestionID      string  `json:"question_id"`
	QuestionText    string  `json:"question_text"`
	ContextType     string  `json:"context_type"`
	Content         string  `json:"content"`
	Confidence      float64 `json:"confidence"`
	QdrantPointID   string  `json:"qdrant_point_id"`
	ImplicitConstraints []string `json:"implicit_constraints,omitempty"`
	Keywords        []string `json:"keywords,omitempty"`
}

// handleOnboardingReply processes a founder's answer during onboarding
func (h *Handler) handleOnboardingReply(founderID, slackUserID, answer, threadTS string) error {
	ctx := context.Background()
	logger := logging.NewLogger("onboarding")

	// Get answered question IDs
	var answeredIDs []string
	rows, err := h.db.QueryContext(ctx, `
		SELECT question_id FROM onboarding_answers 
		WHERE founder_id = $1 
		ORDER BY created_at
	`, founderID)
	if err != nil {
		logger.Error("failed to get answered questions", err)
		return fmt.Errorf("failed to get answered questions: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			logger.Error("failed to scan question id", err)
			continue
		}
		answeredIDs = append(answeredIDs, id)
	}

	// Get next question
	nextQ := getNextQuestion(answeredIDs)
	if nextQ == nil {
		logger.Info("onboarding already complete", "founder_id", founderID)
		return nil
	}

	// For v1, we'll store the answer directly without Python agent call
	// In v2, this would call the Python ContextInterviewAgent via gRPC
	result := OnboardingResult{
		QuestionID:   nextQ.ID,
		QuestionText: nextQ.Text,
		ContextType:  nextQ.ContextType,
		Content:      answer,
		Confidence:   1.0,
	}

	// Store in Postgres
	_, err = h.db.ExecContext(ctx, `
		INSERT INTO onboarding_answers (founder_id, question_id, question_text, raw_answer, extracted_context_type, extracted_content, confidence)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (founder_id, question_id) DO NOTHING
	`, founderID, result.QuestionID, result.QuestionText, answer, result.ContextType, result.Content, result.Confidence)
	if err != nil {
		logger.Error("failed to store onboarding answer", err)
		return fmt.Errorf("failed to store answer: %w", err)
	}

	answeredIDs = append(answeredIDs, result.QuestionID)
	isComplete := len(answeredIDs) >= 6

	if isComplete {
		// Detect archetype (simplified for v1 - in v2 this calls Python agent)
		archetype := detectArchetypeFromAnswers(ctx, h.db, founderID)
		threshold := getThresholdForArchetype(archetype)
		
		_, err = h.db.ExecContext(ctx, `
			UPDATE founders 
			SET onboarding_complete = true, 
			    archetype = $2, 
			    dynamic_threshold = $3,
			    onboarding_started_at = COALESCE(onboarding_started_at, NOW())
			WHERE id = $1
		`, founderID, archetype, threshold)
		if err != nil {
			logger.Error("failed to update founder onboarding status", err)
			return fmt.Errorf("failed to update founder: %w", err)
		}

		// Send completion message
		completionMsg := buildOnboardingCompleteMessage(archetype)
		err = h.sendSlackMessage(slackUserID, completionMsg)
		if err != nil {
			logger.Error("failed to send completion message", err)
		}

		logger.Info("onboarding complete", 
			"founder_id", founderID, 
			"archetype", archetype,
			"threshold", threshold)
		return nil
	}

	// Ask next question
	nextQuestion := getNextQuestion(answeredIDs)
	if nextQuestion != nil {
		questionNum := len(answeredIDs) + 1
		msg := fmt.Sprintf("*Question %d/6:*\n%s", questionNum, nextQuestion.Text)
		err = h.sendSlackMessage(slackUserID, msg)
		if err != nil {
			logger.Error("failed to send next question", err)
			return err
		}
		logger.Info("sent next onboarding question", 
			"founder_id", founderID, 
			"question_num", questionNum,
			"question_id", nextQuestion.ID)
	}

	return nil
}

// startOnboarding initiates the onboarding flow for a new founder
func (h *Handler) startOnboarding(slackUserID string) (string, error) {
	ctx := context.Background()
	logger := logging.NewLogger("onboarding")

	// Check if founder already exists
	var founderID string
	err := h.db.QueryRowContext(ctx, `
		SELECT id FROM founders WHERE slack_user_id = $1
	`, slackUserID).Scan(&founderID)
	
	if err == nil {
		// Founder exists, check if onboarding complete
		var onboardingComplete bool
		err = h.db.QueryRowContext(ctx, `
			SELECT onboarding_complete FROM founders WHERE id = $1
		`, founderID).Scan(&onboardingComplete)
		
		if err == nil && onboardingComplete {
			logger.Info("founder already onboarded", "founder_id", founderID)
			return "", fmt.Errorf("founder already onboarded")
		}
	} else if err == sql.ErrNoRows {
		// New founder
		founderID = uuid.New().String()
		_, err = h.db.ExecContext(ctx, `
			INSERT INTO founders (id, slack_user_id, onboarding_started_at) 
			VALUES ($1, $2, NOW())
			ON CONFLICT (slack_user_id) DO NOTHING
		`, founderID, slackUserID)
		if err != nil {
			logger.Error("failed to create founder", err)
			return "", fmt.Errorf("failed to create founder: %w", err)
		}
		logger.Info("created new founder", "founder_id", founderID, "slack_user_id", slackUserID)
	} else {
		logger.Error("failed to check founder existence", err)
		return "", fmt.Errorf("failed to check founder: %w", err)
	}

	// Send welcome message with first question
	welcome := "👋 I'm Saarathi — your AI co-founder.\n\n" +
		"I watch your behavior, remember your context, and intervene when I see something worth your attention.\n\n" +
		"Before I can be useful, I need to understand your business. 6 questions — answer honestly.\n\n" +
		fmt.Sprintf("*Question 1/6:*\n%s", OnboardingQuestions[0].Text)

	err = h.sendSlackMessage(slackUserID, welcome)
	if err != nil {
		logger.Error("failed to send welcome message", err)
		return "", fmt.Errorf("failed to send welcome: %w", err)
	}

	logger.Info("onboarding started", "founder_id", founderID, "slack_user_id", slackUserID)
	return founderID, nil
}

// getNextQuestion returns the next unanswered question
func getNextQuestion(answeredIDs []string) *struct {
	ID          string
	Text        string
	ContextType string
} {
	for _, q := range OnboardingQuestions {
		found := false
		for _, answeredID := range answeredIDs {
			if answeredID == q.ID {
				found = true
				break
			}
		}
		if !found {
			return &struct {
				ID          string
				Text        string
				ContextType string
			}{
				ID:          q.ID,
				Text:        q.Text,
				ContextType: q.ContextType,
			}
		}
	}
	return nil
}

// detectArchetypeFromAnswers analyzes founder answers to detect archetype
func detectArchetypeFromAnswers(ctx context.Context, db *sql.DB, founderID string) string {
	// Simplified archetype detection for v1
	// In v2, this would call the Python ContextInterviewAgent.detect_archetype()
	
	var answers []string
	rows, err := db.QueryContext(ctx, `
		SELECT raw_answer FROM onboarding_answers WHERE founder_id = $1
	`, founderID)
	if err != nil {
		return "unknown"
	}
	defer rows.Close()

	for rows.Next() {
		var answer string
		rows.Scan(&answer)
		answers = append(answers, answer)
	}

	// Simple keyword-based detection (v1 stub)
	allAnswers := ""
	for _, a := range answers {
		allAnswers += a + " "
	}

	// Detect based on keywords
	if containsAny(allAnswers, []string{"build", "code", "product", "ship", "feature"}) {
		return "builder"
	}
	if containsAny(allAnswers, []string{"sell", "revenue", "customer", "sales", "growth"}) {
		return "hustler"
	}
	if containsAny(allAnswers, []string{"analyze", "data", "metric", "research", "understand"}) {
		return "analyst"
	}
	if containsAny(allAnswers, []string{"process", "system", "operate", "scale", "efficient"}) {
		return "operator"
	}

	return "unknown"
}

// getThresholdForArchetype returns the dynamic threshold for an archetype
func getThresholdForArchetype(archetype string) float64 {
	thresholds := map[string]float64{
		"builder":  0.60,
		"hustler":  0.55,
		"analyst":  0.65,
		"operator": 0.70,
	}
	if threshold, ok := thresholds[archetype]; ok {
		return threshold
	}
	return 0.60 // default
}

// buildOnboardingCompleteMessage creates the completion message
func buildOnboardingCompleteMessage(archetype string) string {
	labels := map[string]string{
		"builder":  "You're a Builder — strong on execution, watch the customer conversation gap.",
		"hustler":  "You're a Hustler — strong on sales, watch scope creep and overcommitment.",
		"analyst":  "You're an Analyst — strong on insight, watch analysis paralysis.",
		"operator": "You're an Operator — strong on process, watch losing the innovation edge.",
	}
	label := labels[archetype]
	if label == "" {
		label = "I've got your full context now."
	}
	return "✅ I know your business now.\n\n" + label + "\n\nI'll be quiet unless I see something worth your attention."
}

// containsAny checks if text contains any of the keywords
func containsAny(text string, keywords []string) bool {
	text = lower(text)
	for _, kw := range keywords {
		if contains(text, kw) {
			return true
		}
	}
	return false
}

// lower converts string to lowercase
func lower(s string) string {
	result := ""
	for _, r := range s {
		if r >= 'A' && r <= 'Z' {
			result += string(r + 32)
		} else {
			result += string(r)
		}
	}
	return result
}

// contains checks if s contains substr (case-insensitive)
func contains(s, substr string) bool {
	s = lower(s)
	substr = lower(substr)
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// sendSlackMessage sends a DM to a Slack user
func (h *Handler) sendSlackMessage(slackUserID, text string) error {
	// For v1, this is a stub that logs the message
	// In v2, this would use the Slack Bolt API to send actual DMs
	logger := logging.NewLogger("slack")
	logger.Info("would send Slack message", 
		"user_id", slackUserID, 
		"text", text,
		"channel_type", "im")
	
	// TODO: Implement actual Slack API call using bolt-go or slack-go
	// For now, just log it
	return nil
}
