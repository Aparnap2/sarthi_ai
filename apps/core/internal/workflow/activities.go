package workflow

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"iterateswarm-core/internal/agents"
	"iterateswarm-core/internal/logging"
	"iterateswarm-core/internal/memory"
	"iterateswarm-core/internal/retry"

	"github.com/bwmarrin/discordgo"
	"github.com/google/go-github/v50/github"
	"golang.org/x/oauth2"
	
	// gRPC imports for Python agent communication
	aiv1 "github.com/Aparnap2/iterate_swarm/gen/go/ai/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// Activities contains the workflow activities.
type Activities struct {
	logger *logging.Logger
}

// NewActivities creates a new Activities instance.
func NewActivities() *Activities {
	return &Activities{
		logger: logging.NewLogger("workflow"),
	}
}

// AnalyzeFeedbackInput is the input for the AnalyzeFeedback activity.
type AnalyzeFeedbackInput struct {
	Text      string
	Source    string
	UserID    string
	ChannelID string
}

// AnalyzeFeedback analyzes feedback using Go-based AI agents (replaces Python gRPC).
func (a *Activities) AnalyzeFeedback(ctx context.Context, input AnalyzeFeedbackInput) (*AnalyzeFeedbackOutput, error) {
	startTime := time.Now()
	a.logger.Info("analyzing feedback",
		"source", input.Source,
		"user_id", input.UserID,
		"text_length", len(input.Text),
	)

	// Step 1: Check for duplicates using Qdrant
	qdrantClient, err := memory.NewQdrantClientFromEnv()
	if err != nil {
		a.logger.Error("failed to create qdrant client", err)
		return nil, fmt.Errorf("failed to create qdrant client: %w", err)
	}

	if err := qdrantClient.EnsureCollection(ctx); err != nil {
		a.logger.Error("failed to ensure qdrant collection", err)
		return nil, fmt.Errorf("failed to ensure collection: %w", err)
	}

	isDuplicate, _, err := qdrantClient.CheckDuplicate(ctx, input.Text)
	if err != nil {
		a.logger.Error("duplicate check failed", err)
		return nil, fmt.Errorf("duplicate check failed: %w", err)
	}

	if isDuplicate {
		a.logger.Info("feedback is duplicate, skipping analysis")
		return &AnalyzeFeedbackOutput{
			IsDuplicate: true,
		}, nil
	}

	// Step 2: Triage (classify and determine severity)
	// P1-2 FIX: Add nil check and validation before using agent
	triageAgent := agents.NewTriageAgentFromEnv()
	if triageAgent == nil {
		a.logger.Error("triage agent is nil", fmt.Errorf("failed to create triage agent - check AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT environment variables"))
		return nil, fmt.Errorf("triage agent unavailable: AI service not configured")
	}

	triageResult, err := triageAgent.Classify(ctx, input.UserID, input.Text, input.Source)
	if err != nil {
		a.logger.Error("triage failed", err)
		return nil, fmt.Errorf("triage failed: %w", err)
	}

	// Step 3: Generate spec
	// P1-2 FIX: Add nil check before using agent
	specAgent := agents.NewSpecAgentFromEnv()
	if specAgent == nil {
		a.logger.Error("spec agent is nil", fmt.Errorf("failed to create spec agent - check AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT environment variables"))
		return nil, fmt.Errorf("spec agent unavailable: AI service not configured")
	}

	specResult, err := specAgent.GenerateSpec(
		ctx,
		input.UserID,
		input.Text,
		input.Source,
		triageResult.Classification,
		triageResult.Severity,
		triageResult.Reasoning,
		triageResult.Confidence,
	)
	if err != nil {
		a.logger.Error("spec generation failed", err)
		return nil, fmt.Errorf("spec generation failed: %w", err)
	}

	// Step 4: Index for future duplicate detection
	metadata := map[string]interface{}{
		"user_id":        input.UserID,
		"classification": triageResult.Classification,
		"severity":       triageResult.Severity,
		"confidence":     triageResult.Confidence,
	}
	if err := qdrantClient.IndexFeedback(ctx, input.UserID, input.Text, metadata); err != nil {
		a.logger.Error("failed to index feedback", err)
		// Don't fail if indexing fails
	}

	// Build description from spec
	description := buildDescription(specResult)

	// P3-1 FIX: Include confidence from AI response (not hardcoded)
	output := &AnalyzeFeedbackOutput{
		IsDuplicate: false,
		Title:       specResult.Title,
		Description: description,
		Labels:      specResult.SuggestedLabels,
		Severity:    triageResult.Severity,
		IssueType:   triageResult.Classification,
		Confidence:  triageResult.Confidence, // Real confidence from Azure AI
	}

	duration := time.Since(startTime)
	a.logger.LogActivity(ctx, "AnalyzeFeedback", duration, true,
		"is_duplicate", output.IsDuplicate,
		"issue_type", output.IssueType,
		"severity", output.Severity,
	)

	return output, nil
}

// buildDescription creates a GitHub issue description from the spec result.
func buildDescription(spec *agents.SpecResult) string {
	var parts []string

	if len(spec.ReproductionSteps) > 0 {
		parts = append(parts, "## Reproduction Steps")
		for i, step := range spec.ReproductionSteps {
			parts = append(parts, fmt.Sprintf("%d. %s", i+1, step))
		}
		parts = append(parts, "")
	}

	if len(spec.AffectedComponents) > 0 {
		parts = append(parts, "## Affected Components")
		for _, comp := range spec.AffectedComponents {
			parts = append(parts, fmt.Sprintf("- %s", comp))
		}
		parts = append(parts, "")
	}

	if len(spec.AcceptanceCriteria) > 0 {
		parts = append(parts, "## Acceptance Criteria")
		for _, criteria := range spec.AcceptanceCriteria {
			parts = append(parts, fmt.Sprintf("- [ ] %s", criteria))
		}
		parts = append(parts, "")
	}

	return strings.Join(parts, "\n")
}

// severityColor maps severity levels to Discord embed colors.
var severityColor = map[string]int{
	"critical":    0xff0000,
	"high":        0xff6600,
	"medium":      0xffff00,
	"low":         0x00ff00,
	"unspecified": 0x808080,
}

// issueTypeEmoji maps issue types to emojis.
var issueTypeEmoji = map[string]string{
	"bug":         "🐛",
	"feature":     "✨",
	"question":    "❓",
	"unspecified": "📝",
}

// SendDiscordApproval sends an approval request to Discord with Approve/Reject buttons.
func (a *Activities) SendDiscordApproval(ctx context.Context, input SendDiscordApprovalInput) error {
	startTime := time.Now()
	a.logger.Info("sending discord approval request",
		"channel_id", input.ChannelID,
		"issue_title", input.IssueTitle,
		"workflow_id", input.WorkflowID,
	)

	// Get Discord bot token from environment
	discordToken := os.Getenv("DISCORD_BOT_TOKEN")
	if discordToken == "" {
		a.logger.Warn("discord token not configured, skipping notification")
		return nil
	}

	// Create Discord session with retry
	var dg *discordgo.Session
	err := retry.SimpleRetry(func() error {
		var createErr error
		dg, createErr = discordgo.New("Bot " + discordToken)
		return createErr
	})
	if err != nil {
		a.logger.Error("failed to create discord session", err)
		return fmt.Errorf("failed to create Discord session: %w", err)
	}

	// Get color for severity
	color := severityColor[strings.ToLower(input.Severity)]
	if color == 0 {
		color = severityColor["unspecified"]
	}

	// Get emoji for issue type
	emoji := issueTypeEmoji[strings.ToLower(input.IssueType)]
	if emoji == "" {
		emoji = issueTypeEmoji["unspecified"]
	}

	// Create embed for the issue proposal
	embed := &discordgo.MessageEmbed{
		Title:       fmt.Sprintf("%s New Issue Proposed: %s", emoji, input.IssueTitle),
		Description: truncateString(input.IssueBody, 4000),
		Color:       color,
		Fields: []*discordgo.MessageEmbedField{
			{
				Name:   "Severity",
				Value:  strings.ToUpper(input.Severity),
				Inline: true,
			},
			{
				Name:   "Type",
				Value:  strings.ToUpper(input.IssueType),
				Inline: true,
			},
			{
				Name:   "Labels",
				Value:  strings.Join(input.IssueLabels, ", "),
				Inline: true,
			},
			{
				Name:   "Workflow ID",
				Value:  input.WorkflowID,
				Inline: false,
			},
		},
		Footer: &discordgo.MessageEmbedFooter{
			Text: "IterateSwarm AI ChatOps",
		},
		Timestamp: time.Now().Format(time.RFC3339),
	}

	// P1-1 FIX: Use WorkflowID in custom_id format: "action:workflow_id"
	// This ensures precise signal routing back to the specific workflow
	customIDFormat := input.WorkflowID

	approveBtn := discordgo.Button{
		Label:    "Approve",
		Style:    discordgo.SuccessButton,
		CustomID: fmt.Sprintf("approve:%s", customIDFormat),
	}

	rejectBtn := discordgo.Button{
		Label:    "Reject",
		Style:    discordgo.DangerButton,
		CustomID: fmt.Sprintf("reject:%s", customIDFormat),
	}

	// Get channel info and send message with retry
	var channel *discordgo.Channel
	err = retry.SimpleRetry(func() error {
		var channelErr error
		channel, channelErr = dg.Channel(input.ChannelID)
		return channelErr
	})
	if err != nil {
		a.logger.Error("failed to get discord channel", err, "channel_id", input.ChannelID)
		return fmt.Errorf("failed to get Discord channel: %w", err)
	}

	a.logger.Info("sending to discord channel", "channel_name", channel.Name)

	var msg *discordgo.Message
	err = retry.SimpleRetry(func() error {
		var sendErr error
		msg, sendErr = dg.ChannelMessageSendComplex(input.ChannelID, &discordgo.MessageSend{
			Embeds:     []*discordgo.MessageEmbed{embed},
			Components: []discordgo.MessageComponent{discordgo.ActionsRow{Components: []discordgo.MessageComponent{approveBtn, rejectBtn}}},
		})
		return sendErr
	})
	if err != nil {
		a.logger.Error("failed to send discord message", err, "channel_id", input.ChannelID)
		return fmt.Errorf("failed to send Discord message: %w", err)
	}

	duration := time.Since(startTime)
	a.logger.LogActivity(ctx, "SendDiscordApproval", duration, true,
		"message_id", msg.ID,
		"channel_id", input.ChannelID,
	)

	return nil
}

// CreateGitHubIssue creates a GitHub issue when approved.
// Supports test mode via TEST_GITHUB_REPO environment variable for E2E testing.
func (a *Activities) CreateGitHubIssue(ctx context.Context, input CreateGitHubIssueInput) (string, error) {
	startTime := time.Now()
	a.logger.Info("creating github issue",
		"title", input.Title,
		"repo_owner", input.RepoOwner,
		"repo_name", input.RepoName,
	)

	// Get GitHub token from environment
	githubToken := os.Getenv("GITHUB_TOKEN")
	if githubToken == "" {
		a.logger.Warn("github token not configured, skipping issue creation")
		return "", nil
	}

	// Create OAuth2 client for GitHub authentication
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: githubToken},
	)
	tc := oauth2.NewClient(ctx, ts)
	client := github.NewClient(tc)

	// Get repository owner from environment if not provided
	owner := input.RepoOwner
	if owner == "" {
		owner = os.Getenv("GITHUB_OWNER")
	}
	if owner == "" {
		return "", fmt.Errorf("GITHUB_OWNER not set and RepoOwner not provided")
	}

	// Get repository name from environment if not provided
	// P4 FIX: Support TEST_GITHUB_REPO for E2E testing isolation
	repo := input.RepoName
	if repo == "" {
		// Check if we're in test mode
		testRepo := os.Getenv("TEST_GITHUB_REPO")
		if testRepo != "" && os.Getenv("TEST_MODE") == "true" {
			repo = testRepo
			a.logger.Info("using test repository for E2E testing", "repo", repo)
		} else {
			repo = os.Getenv("GITHUB_REPO")
		}
	}
	if repo == "" {
		return "", fmt.Errorf("GITHUB_REPO not set and RepoName not provided")
	}

	// Prepare issue request
	issueLabels := &input.Labels
	if issueLabels == nil || len(*issueLabels) == 0 {
		defaultLabels := []string{"ai-generated"}
		issueLabels = &defaultLabels
	}

	issueRequest := &github.IssueRequest{
		Title:  &input.Title,
		Body:   &input.Body,
		Labels: issueLabels,
	}

	// Add assignee if provided
	if input.Assignee != "" {
		issueRequest.Assignee = &input.Assignee
	}

	// Create the issue with retry
	var issue *github.Issue
	err := retry.SimpleRetry(func() error {
		var createErr error
		issue, _, createErr = client.Issues.Create(ctx, owner, repo, issueRequest)
		return createErr
	})
	if err != nil {
		a.logger.Error("failed to create github issue", err,
			"owner", owner,
			"repo", repo,
		)
		return "", fmt.Errorf("failed to create GitHub issue: %w", err)
	}

	issueURL := issue.GetHTMLURL()
	duration := time.Since(startTime)
	a.logger.LogActivity(ctx, "CreateGitHubIssue", duration, true,
		"issue_url", issueURL,
		"issue_number", issue.GetNumber(),
	)

	return issueURL, nil
}

// truncateString truncates a string to the specified max length.
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

// StartSwarmInput is the input for the StartSwarm activity.
type StartSwarmInput struct {
	TaskID       string
	FeedbackText string
	Source       string
	UserID       string
	Config       SwarmConfig
}

// SwarmConfig controls which agents are enabled.
type SwarmConfig struct {
	EnableResearcher bool
	EnableSRE        bool
	EnableSWE        bool
	EnableReviewer   bool
}

// StartSwarmOutput contains the results from the multi-agent swarm.
type StartSwarmOutput struct {
	TaskID       string
	Status       string
	Results      []AgentResult
	PRURL        string
	ErrorMessage string
}

// AgentResult contains output from a single agent.
type AgentResult struct {
	AgentName    string
	Success      bool
	Output       string
	Confidence   float64
	ErrorMessage string
}

// StartSwarm calls the Python gRPC server to execute the multi-agent swarm.
func (a *Activities) StartSwarm(ctx context.Context, input StartSwarmInput) (*StartSwarmOutput, error) {
	startTime := time.Now()
	a.logger.Info("starting multi-agent swarm",
		"task_id", input.TaskID,
		"user_id", input.UserID,
		"source", input.Source,
	)

	// Get gRPC server address from environment
	grpcAddr := os.Getenv("AI_GRPC_ADDRESS")
	if grpcAddr == "" {
		grpcAddr = "localhost:50051" // Default address
	}

	// Create gRPC connection with timeout
	connCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(connCtx, grpcAddr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		a.logger.Error("failed to connect to AI gRPC server", err, "address", grpcAddr)
		return nil, fmt.Errorf("failed to connect to AI service: %w", err)
	}
	defer conn.Close()

	// Create gRPC client
	client := aiv1.NewAgentServiceClient(conn)

	// Build gRPC request
	req := &aiv1.StartSwarmRequest{
		TaskId:       input.TaskID,
		FeedbackText: input.FeedbackText,
		Source:       input.Source,
		UserId:       input.UserID,
		Config: &aiv1.SwarmConfig{
			EnableResearcher: input.Config.EnableResearcher,
			EnableSre:        input.Config.EnableSRE,
			EnableSwe:        input.Config.EnableSWE,
			EnableReviewer:   input.Config.EnableReviewer,
		},
	}

	// Call gRPC with timeout
	callCtx, callCancel := context.WithTimeout(ctx, 5*time.Minute)
	defer callCancel()

	resp, err := client.StartSwarm(callCtx, req)
	if err != nil {
		a.logger.Error("StartSwarm gRPC call failed", err, "task_id", input.TaskID)
		return nil, fmt.Errorf("swarm execution failed: %w", err)
	}

	// Map gRPC response to Go struct
	results := make([]AgentResult, len(resp.Results))
	for i, r := range resp.Results {
		results[i] = AgentResult{
			AgentName:    r.AgentName,
			Success:      r.Success,
			Output:       r.Output,
			Confidence:   float64(r.Confidence),
			ErrorMessage: r.ErrorMessage,
		}
	}

	// Map status
	status := "unknown"
	switch resp.Status {
	case aiv1.SwarmStatus_SWARM_STATUS_COMPLETED:
		status = "completed"
	case aiv1.SwarmStatus_SWARM_STATUS_FAILED:
		status = "failed"
	case aiv1.SwarmStatus_SWARM_STATUS_INTERRUPTED:
		status = "interrupted"
	case aiv1.SwarmStatus_SWARM_STATUS_PENDING:
		status = "pending"
	case aiv1.SwarmStatus_SWARM_STATUS_RUNNING:
		status = "running"
	}

	output := &StartSwarmOutput{
		TaskID:       resp.TaskId,
		Status:       status,
		Results:      results,
		PRURL:        resp.PrUrl,
		ErrorMessage: resp.ErrorMessage,
	}

	duration := time.Since(startTime)
	a.logger.LogActivity(ctx, "StartSwarm", duration, output.Status == "completed",
		"task_id", output.TaskID,
		"status", output.Status,
		"pr_url", output.PRURL,
	)

	return output, nil
}
