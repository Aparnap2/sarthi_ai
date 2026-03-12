package workflow

import (
	"fmt"
	"time"

	"go.temporal.io/sdk/temporal"
	"go.temporal.io/sdk/workflow"
)

const (
	// OnboardingTaskQueue is the task queue for onboarding workflows
	OnboardingTaskQueue = "ONBOARDING_TASK_QUEUE"

	// AnswerSignal is the signal name for receiving onboarding answers
	AnswerSignal = "onboarding_answer"

	// AnswerTimeoutPerQuestion is the timeout for each question (48 hours)
	AnswerTimeoutPerQuestion = 48 * time.Hour

	// TotalQuestions is the total number of onboarding questions
	TotalQuestions = 6
)

// OnboardingInput is the input to the OnboardingWorkflow
type OnboardingInput struct {
	FounderID      string `json:"founder_id"`
	TelegramUserID string `json:"telegram_user_id"`
	Language       string `json:"language"` // "en" | "hi"
}

// OnboardingOutput is the output from the OnboardingWorkflow
type OnboardingOutput struct {
	Archetype        string  `json:"archetype"`
	DynamicThreshold float64 `json:"dynamic_threshold"`
	Completed        bool    `json:"completed"`
	TimedOutAt       string  `json:"timed_out_at,omitempty"`
}

// OnboardingWorkflow runs the 6-question onboarding flow
func OnboardingWorkflow(ctx workflow.Context, input OnboardingInput) (OnboardingOutput, error) {
	logger := workflow.GetLogger(ctx)
	logger.Info("starting onboarding workflow", "founder_id", input.FounderID, "language", input.Language)

	// Set activity options with retry policy
	ao := workflow.ActivityOptions{
		StartToCloseTimeout: 30 * time.Second,
		RetryPolicy: &temporal.RetryPolicy{
			MaximumAttempts: 3,
		},
	}
	ctx = workflow.WithActivityOptions(ctx, ao)

	// Track answered question IDs
	answeredIDs := []string{}

	// Step 1: Get and send first question
	var firstQ QuestionPayload
	err := workflow.ExecuteActivity(ctx, GetNextQuestionActivity, GetNextQuestionInput{
		AnsweredIDs: answeredIDs,
		Language:    input.Language,
	}).Get(ctx, &firstQ)
	if err != nil {
		logger.Error("failed to get first question", "error", err)
		return OnboardingOutput{}, fmt.Errorf("failed to get first question: %w", err)
	}

	err = workflow.ExecuteActivity(ctx, SendTelegramOnboardingMessageActivity, SendOnboardingMessageInput{
		TelegramUserID:  input.TelegramUserID,
		Message:         firstQ.Text,
		QuestionNumber:  1,
		TotalQuestions:  TotalQuestions,
		IsFirstQuestion: true,
	}).Get(ctx, nil)
	if err != nil {
		logger.Error("failed to send first question", "error", err)
		return OnboardingOutput{}, fmt.Errorf("failed to send first question: %w", err)
	}

	// Step 2: Loop through all 6 questions
	for len(answeredIDs) < TotalQuestions {
		questionNumber := len(answeredIDs) + 1
		logger.Info("waiting for answer", "question_number", questionNumber)

		// Wait for answer signal (48h timeout)
		answerChan := workflow.GetSignalChannel(ctx, AnswerSignal)
		var answer AnswerSignalPayload

		// Wait for answer with timeout
		timedOut, err := workflow.AwaitWithTimeout(
			ctx,
			AnswerTimeoutPerQuestion,
			func() bool {
				return answerChan.ReceiveAsync(&answer)
			},
		)
		if err != nil {
			logger.Error("error waiting for answer", "error", err)
			return OnboardingOutput{}, fmt.Errorf("error waiting for answer: %w", err)
		}

		// Handle timeout - send gentle nudge
		if timedOut || answer.RawAnswer == "" {
			logger.Info("question timed out, sending nudge", "question_number", questionNumber)

			// Send gentle nudge message
			nudgeErr := workflow.ExecuteActivity(ctx, SendTelegramOnboardingMessageActivity, SendOnboardingMessageInput{
				TelegramUserID: input.TelegramUserID,
				Message:        fmt.Sprintf("Whenever you're ready — I'm here. Question %d/%d is still waiting for you.", questionNumber, TotalQuestions),
				QuestionNumber: questionNumber,
				TotalQuestions: TotalQuestions,
			}).Get(ctx, nil)
			if nudgeErr != nil {
				logger.Warn("failed to send nudge", "error", nudgeErr)
			}

			// Give one more 48h window
			timedOut2, err := workflow.AwaitWithTimeout(
				ctx,
				AnswerTimeoutPerQuestion,
				func() bool {
					return answerChan.ReceiveAsync(&answer)
				},
			)
			if err != nil {
				logger.Error("error waiting for answer after nudge", "error", err)
				return OnboardingOutput{}, fmt.Errorf("error waiting for answer after nudge: %w", err)
			}

			// Still no answer → abandon onboarding
			if timedOut2 || answer.RawAnswer == "" {
				logger.Info("onboarding abandoned due to timeout", "question_number", questionNumber)
				return OnboardingOutput{
					Completed:  false,
					TimedOutAt: fmt.Sprintf("question_%d", questionNumber),
				}, nil
			}
		}

		logger.Info("received answer", "question_number", questionNumber, "answer_length", len(answer.RawAnswer))

		// Get current question (should match the one we sent)
		var currentQ QuestionPayload
		err = workflow.ExecuteActivity(ctx, GetNextQuestionActivity, GetNextQuestionInput{
			AnsweredIDs: answeredIDs,
			Language:    input.Language,
		}).Get(ctx, &currentQ)
		if err != nil {
			logger.Error("failed to get current question", "error", err)
			return OnboardingOutput{}, fmt.Errorf("failed to get current question: %w", err)
		}

		// Process answer via Python gRPC / AI service
		var processResult ProcessAnswerResult
		err = workflow.ExecuteActivity(ctx, ProcessOnboardingAnswerActivity, ProcessAnswerInput{
			FounderID:    input.FounderID,
			QuestionID:   currentQ.ID,
			QuestionText: currentQ.Text,
			RawAnswer:    answer.RawAnswer,
		}).Get(ctx, &processResult)
		if err != nil {
			logger.Error("failed to process answer", "question_id", currentQ.ID, "error", err)
			return OnboardingOutput{}, fmt.Errorf("failed to process answer for question %s: %w", currentQ.ID, err)
		}

		// Store in Postgres
		err = workflow.ExecuteActivity(ctx, StoreOnboardingAnswerActivity, processResult).Get(ctx, nil)
		if err != nil {
			logger.Error("failed to store answer", "question_id", currentQ.ID, "error", err)
			return OnboardingOutput{}, fmt.Errorf("failed to store answer for question %s: %w", currentQ.ID, err)
		}

		// Add to answered list
		answeredIDs = append(answeredIDs, currentQ.ID)
		logger.Info("answer processed and stored", "question_id", currentQ.ID, "answered_count", len(answeredIDs))

		// Send next question or completion message
		if len(answeredIDs) < TotalQuestions {
			var nextQ QuestionPayload
			err = workflow.ExecuteActivity(ctx, GetNextQuestionActivity, GetNextQuestionInput{
				AnsweredIDs: answeredIDs,
				Language:    input.Language,
			}).Get(ctx, &nextQ)
			if err != nil {
				logger.Error("failed to get next question", "error", err)
				return OnboardingOutput{}, fmt.Errorf("failed to get next question: %w", err)
			}

			err = workflow.ExecuteActivity(ctx, SendTelegramOnboardingMessageActivity, SendOnboardingMessageInput{
				TelegramUserID: input.TelegramUserID,
				Message:        nextQ.Text,
				QuestionNumber: len(answeredIDs) + 1,
				TotalQuestions: TotalQuestions,
			}).Get(ctx, nil)
			if err != nil {
				logger.Error("failed to send next question", "error", err)
				return OnboardingOutput{}, fmt.Errorf("failed to send next question: %w", err)
			}
		}
	}

	// Step 3: All 6 answered → detect archetype
	logger.Info("all questions answered, detecting archetype", "founder_id", input.FounderID)
	var archetypeResult ArchetypeResult
	err = workflow.ExecuteActivity(ctx, DetectArchetypeActivity, DetectArchetypeInput{
		FounderID: input.FounderID,
	}).Get(ctx, &archetypeResult)
	if err != nil {
		logger.Error("failed to detect archetype", "error", err)
		return OnboardingOutput{}, fmt.Errorf("failed to detect archetype: %w", err)
	}

	// Step 4: Update founders table with archetype and threshold
	err = workflow.ExecuteActivity(ctx, CompleteOnboardingActivity, CompleteOnboardingInput{
		FounderID:        input.FounderID,
		Archetype:        archetypeResult.Archetype,
		DynamicThreshold: archetypeResult.Threshold,
	}).Get(ctx, nil)
	if err != nil {
		logger.Error("failed to complete onboarding", "error", err)
		return OnboardingOutput{}, fmt.Errorf("failed to complete onboarding: %w", err)
	}

	// Step 5: Send completion message
	completionMsg := buildCompletionMessage(archetypeResult.Archetype, input.Language)
	err = workflow.ExecuteActivity(ctx, SendTelegramOnboardingMessageActivity, SendOnboardingMessageInput{
		TelegramUserID: input.TelegramUserID,
		Message:        completionMsg,
		IsCompletion:   true,
		QuestionNumber: TotalQuestions,
		TotalQuestions: TotalQuestions,
	}).Get(ctx, nil)
	if err != nil {
		logger.Warn("failed to send completion message", "error", err)
	}

	logger.Info("onboarding completed successfully",
		"founder_id", input.FounderID,
		"archetype", archetypeResult.Archetype,
		"threshold", archetypeResult.Threshold,
	)

	return OnboardingOutput{
		Archetype:        archetypeResult.Archetype,
		DynamicThreshold: archetypeResult.Threshold,
		Completed:        true,
	}, nil
}

// buildCompletionMessage creates a personalized completion message based on archetype
func buildCompletionMessage(archetype, lang string) string {
	labels := map[string]string{
		"builder":  "You're a Builder — strong on execution. I'll watch for the customer conversation gap.",
		"hustler":  "You're a Hustler — strong on sales. I'll watch for overcommitment and scope creep.",
		"analyst":  "You're an Analyst — strong on insight. I'll watch for analysis paralysis.",
		"operator": "You're an Operator — strong on process. I'll watch for the innovation edge.",
	}

	label, ok := labels[archetype]
	if !ok {
		label = "I've got your full context now."
	}

	return fmt.Sprintf("✅ I know your business now.\n\n%s\n\nI'll be quiet unless I see something worth your attention. You'll hear from me when it matters.", label)
}
