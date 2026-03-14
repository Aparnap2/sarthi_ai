package db

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	_ "github.com/lib/pq"
)

// DBTX is an interface for database operations, implemented by both *sql.DB and *pgxpool.Pool
type DBTX interface {
	QueryRow(ctx context.Context, query string, args ...interface{}) pgx.Row
	Exec(ctx context.Context, query string, args ...interface{}) (pgconn.CommandTag, error)
	Query(ctx context.Context, query string, args ...interface{}) (pgx.Rows, error)
}

// Repository provides database operations using PostgreSQL
// Replaces Redis functionality for production deployment on Azure
type Repository struct {
	db   *sql.DB
	pool *pgxpool.Pool
}

// NewRepository creates a new Repository with PostgreSQL connection
func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

// NewRepositoryFromPool creates a new Repository with a pgxpool.Pool
func NewRepositoryFromPool(pool *pgxpool.Pool) *Repository {
	return &Repository{pool: pool}
}

// Close closes the database connection
func (r *Repository) Close() error {
	if r.pool != nil {
		r.pool.Close()
	}
	if r.db != nil {
		return r.db.Close()
	}
	return nil
}

// ═══════════════════════════════════════════════════════════════════════════════
// Idempotency Key Operations (replaces Redis SETNX)
// ═══════════════════════════════════════════════════════════════════════════════

// SetIdempotencyKey attempts to set an idempotency key.
// Returns true if the key was newly created, false if it already exists.
func (r *Repository) SetIdempotencyKey(ctx context.Context, key, source string, ttl time.Duration) (bool, error) {
	query := `
		INSERT INTO idempotency_keys (key, source, created_at)
		VALUES ($1, $2, NOW())
		ON CONFLICT (key) DO NOTHING
		RETURNING key
	`
	var result string
	err := r.db.QueryRowContext(ctx, query, key, source).Scan(&result)
	if err == sql.ErrNoRows {
		return false, nil // Key already exists
	}
	if err != nil {
		return false, fmt.Errorf("failed to set idempotency key: %w", err)
	}
	return true, nil
}

// GetIdempotencyKey checks if an idempotency key exists
func (r *Repository) GetIdempotencyKey(ctx context.Context, key string) (bool, error) {
	query := `SELECT 1 FROM idempotency_keys WHERE key = $1`
	var result int
	err := r.db.QueryRowContext(ctx, query, key).Scan(&result)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("failed to check idempotency key: %w", err)
	}
	return true, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
// Token Budget Operations (replaces Redis INCRBY)
// ═══════════════════════════════════════════════════════════════════════════════

// GetTokenBudget retrieves the current token budget for a task
func (r *Repository) GetTokenBudget(ctx context.Context, taskID string) (used, limit int, err error) {
	query := `SELECT tokens_used, tokens_limit FROM token_budgets WHERE task_id = $1`
	err = r.db.QueryRowContext(ctx, query, taskID).Scan(&used, &limit)
	if err == sql.ErrNoRows {
		// Return default budget
		return 0, 50000, nil
	}
	if err != nil {
		return 0, 0, fmt.Errorf("failed to get token budget: %w", err)
	}
	return used, limit, nil
}

// IncrementTokenBudget adds tokens to the used count for a task
// Returns the new used count and an error if the limit is exceeded
func (r *Repository) IncrementTokenBudget(ctx context.Context, taskID string, tokens int) (newUsed int, withinBudget bool, err error) {
	query := `
		INSERT INTO token_budgets (task_id, tokens_used, tokens_limit)
		VALUES ($1, $2, 50000)
		ON CONFLICT (task_id) DO UPDATE
		SET tokens_used = token_budgets.tokens_used + $2,
		    updated_at = NOW()
		RETURNING tokens_used, tokens_limit
	`
	var used, limit int
	err = r.db.QueryRowContext(ctx, query, taskID, tokens).Scan(&used, &limit)
	if err != nil {
		return 0, false, fmt.Errorf("failed to increment token budget: %w", err)
	}
	return used, used <= limit, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
// Agent Context Operations (replaces Redis SharedContext)
// ═══════════════════════════════════════════════════════════════════════════════

// SetAgentContext stores agent findings for a task
func (r *Repository) SetAgentContext(ctx context.Context, taskID, agentRole string, findings map[string]interface{}) error {
	findingsJSON, err := json.Marshal(findings)
	if err != nil {
		return fmt.Errorf("failed to marshal findings: %w", err)
	}

	query := `
		INSERT INTO agent_context (task_id, agent_role, findings, updated_at)
		VALUES ($1, $2, $3, NOW())
		ON CONFLICT (task_id, agent_role) DO UPDATE
		SET findings = $3, updated_at = NOW()
	`
	_, err = r.db.ExecContext(ctx, query, taskID, agentRole, findingsJSON)
	if err != nil {
		return fmt.Errorf("failed to set agent context: %w", err)
	}
	return nil
}

// GetAgentContext retrieves agent findings for a task
func (r *Repository) GetAgentContext(ctx context.Context, taskID, agentRole string) (map[string]interface{}, error) {
	query := `SELECT findings FROM agent_context WHERE task_id = $1 AND agent_role = $2`
	var findingsJSON []byte
	err := r.db.QueryRowContext(ctx, query, taskID, agentRole).Scan(&findingsJSON)
	if err == sql.ErrNoRows {
		return map[string]interface{}{}, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get agent context: %w", err)
	}

	var findings map[string]interface{}
	if err := json.Unmarshal(findingsJSON, &findings); err != nil {
		return nil, fmt.Errorf("failed to unmarshal findings: %w", err)
	}
	return findings, nil
}

// GetAllAgentContext retrieves all agent findings for a task
func (r *Repository) GetAllAgentContext(ctx context.Context, taskID string) (map[string]map[string]interface{}, error) {
	query := `SELECT agent_role, findings FROM agent_context WHERE task_id = $1`
	rows, err := r.db.QueryContext(ctx, query, taskID)
	if err != nil {
		return nil, fmt.Errorf("failed to get all agent context: %w", err)
	}
	defer rows.Close()

	result := make(map[string]map[string]interface{})
	for rows.Next() {
		var agentRole string
		var findingsJSON []byte
		if err := rows.Scan(&agentRole, &findingsJSON); err != nil {
			return nil, fmt.Errorf("failed to scan agent context: %w", err)
		}

		var findings map[string]interface{}
		if err := json.Unmarshal(findingsJSON, &findings); err != nil {
			return nil, fmt.Errorf("failed to unmarshal findings: %w", err)
		}
		result[agentRole] = findings
	}

	return result, rows.Err()
}

// ═══════════════════════════════════════════════════════════════════════════════
// HITL Queue Operations (replaces Redis hitl:pending)
// ═══════════════════════════════════════════════════════════════════════════════

// HITLItem represents a human-in-the-loop approval request
type HITLItem struct {
	TaskID     string
	WorkflowID string
	IssueTitle string
	IssueBody  string
	Severity   string
	Status     string
	CreatedAt  time.Time
	ExpiresAt  time.Time
}

// AddToHITLQueue adds an item to the HITL approval queue
func (r *Repository) AddToHITLQueue(ctx context.Context, item HITLItem) error {
	query := `
		INSERT INTO hitl_queue (task_id, workflow_id, issue_title, issue_body, severity, status, created_at, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		ON CONFLICT (task_id) DO UPDATE
		SET workflow_id = $2, issue_title = $3, issue_body = $4, severity = $5, status = $6, created_at = $7, expires_at = $8
	`
	_, err := r.db.ExecContext(ctx, query,
		item.TaskID, item.WorkflowID, item.IssueTitle, item.IssueBody,
		item.Severity, item.Status, item.CreatedAt, item.ExpiresAt)
	if err != nil {
		return fmt.Errorf("failed to add to HITL queue: %w", err)
	}
	return nil
}

// GetHITLItem retrieves a HITL item by task ID
func (r *Repository) GetHITLItem(ctx context.Context, taskID string) (*HITLItem, error) {
	query := `SELECT task_id, workflow_id, issue_title, issue_body, severity, status, created_at, expires_at FROM hitl_queue WHERE task_id = $1`
	var item HITLItem
	err := r.db.QueryRowContext(ctx, query, taskID).Scan(
		&item.TaskID, &item.WorkflowID, &item.IssueTitle, &item.IssueBody,
		&item.Severity, &item.Status, &item.CreatedAt, &item.ExpiresAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to get HITL item: %w", err)
	}
	return &item, nil
}

// ListPendingHITL retrieves all pending HITL items
func (r *Repository) ListPendingHITL(ctx context.Context) ([]HITLItem, error) {
	query := `
		SELECT task_id, workflow_id, issue_title, issue_body, severity, status, created_at, expires_at
		FROM hitl_queue
		WHERE status = 'pending' AND expires_at > NOW()
		ORDER BY created_at DESC
	`
	rows, err := r.db.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to list pending HITL: %w", err)
	}
	defer rows.Close()

	var items []HITLItem
	for rows.Next() {
		var item HITLItem
		if err := rows.Scan(&item.TaskID, &item.WorkflowID, &item.IssueTitle, &item.IssueBody,
			&item.Severity, &item.Status, &item.CreatedAt, &item.ExpiresAt); err != nil {
			return nil, fmt.Errorf("failed to scan HITL item: %w", err)
		}
		items = append(items, item)
	}

	return items, rows.Err()
}

// UpdateHITLStatus updates the status of a HITL item
func (r *Repository) UpdateHITLStatus(ctx context.Context, taskID, status string) error {
	query := `UPDATE hitl_queue SET status = $2 WHERE task_id = $1`
	_, err := r.db.ExecContext(ctx, query, taskID, status)
	if err != nil {
		return fmt.Errorf("failed to update HITL status: %w", err)
	}
	return nil
}

// ═══════════════════════════════════════════════════════════════════════════════
// Agent Events Operations (replaces Redis Pub/Sub)
// ═══════════════════════════════════════════════════════════════════════════════

// AgentEvent represents an event from an agent
type AgentEvent struct {
	ID        int
	EventType string
	TaskID    string
	AgentName string
	Message   string
	Severity  string
	Metadata  map[string]interface{}
	CreatedAt time.Time
}

// PublishAgentEvent stores an agent event and triggers NOTIFY
func (r *Repository) PublishAgentEvent(ctx context.Context, event AgentEvent) error {
	metadataJSON, err := json.Marshal(event.Metadata)
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	query := `
		INSERT INTO agent_events (event_type, task_id, agent_name, message, severity, metadata)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, created_at
	`
	err = r.db.QueryRowContext(ctx, query,
		event.EventType, event.TaskID, event.AgentName, event.Message, event.Severity, metadataJSON).
		Scan(&event.ID, &event.CreatedAt)
	if err != nil {
		return fmt.Errorf("failed to publish agent event: %w", err)
	}
	return nil
}

// ListAgentEvents retrieves recent agent events
func (r *Repository) ListAgentEvents(ctx context.Context, limit int) ([]AgentEvent, error) {
	if limit <= 0 || limit > 1000 {
		limit = 100
	}

	query := `
		SELECT id, event_type, task_id, agent_name, message, severity, metadata, created_at
		FROM agent_events
		ORDER BY created_at DESC
		LIMIT $1
	`
	rows, err := r.db.QueryContext(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to list agent events: %w", err)
	}
	defer rows.Close()

	var events []AgentEvent
	for rows.Next() {
		var event AgentEvent
		var metadataJSON []byte
		if err := rows.Scan(&event.ID, &event.EventType, &event.TaskID, &event.AgentName,
			&event.Message, &event.Severity, &metadataJSON, &event.CreatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan agent event: %w", err)
		}
		if err := json.Unmarshal(metadataJSON, &event.Metadata); err != nil {
			return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
		}
		events = append(events, event)
	}

	return events, rows.Err()
}

// ═══════════════════════════════════════════════════════════════════════════════
// Legacy Feedback Operations
// ═══════════════════════════════════════════════════════════════════════════════

// ListFeedbackParams represents parameters for listing feedback
type ListFeedbackParams struct {
	Limit  int
	Offset int
}

// ListIssuesParams represents parameters for listing issues
type ListIssuesParams struct {
	Limit  int
	Offset int
}

// StoreFeedback stores feedback in the database
func (r *Repository) StoreFeedback(ctx context.Context, feedback map[string]interface{}) error {
	// TODO: Implement with actual feedback table
	return nil
}

// GetFeedback retrieves feedback by ID
func (r *Repository) GetFeedback(ctx context.Context, id string) (map[string]interface{}, error) {
	// TODO: Implement with actual feedback table
	return nil, nil
}

// ListFeedback retrieves multiple feedbacks
func (r *Repository) ListFeedback(ctx context.Context, params ListFeedbackParams) ([]map[string]interface{}, error) {
	// TODO: Implement with actual feedback table
	return nil, nil
}

// ListIssues retrieves multiple issues
func (r *Repository) ListIssues(ctx context.Context, params ListIssuesParams) ([]map[string]interface{}, error) {
	// TODO: Implement with actual issues table
	return nil, nil
}

// ═══════════════════════════════════════════════════════════════════════════════
// Raw Event Operations (SOP Runtime)
// ═══════════════════════════════════════════════════════════════════════════════

// RawEvent represents a raw event from an external source
type RawEvent struct {
	ID             string
	FounderID      string
	Source         string
	EventName      string
	Topic          string
	SOPName        string
	PayloadHash    string
	PayloadBody    []byte
	IdempotencyKey string
}

// RawEventStore provides operations for raw event storage
type RawEventStore interface {
	InsertRawEvent(ctx context.Context, event RawEvent) (string, error)
	InsertDLQ(ctx context.Context, eventName, reason string, payload []byte) error
}

// InsertRawEvent inserts a raw event into the database
func (r *Repository) InsertRawEvent(ctx context.Context, event RawEvent) (string, error) {
	query := `
		INSERT INTO raw_events
			(founder_id, source, event_name, topic, sop_name,
			 payload_hash, payload_body, idempotency_key)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id
	`
	
	var id string
	if r.pool != nil {
		err := r.pool.QueryRow(ctx, query,
			event.FounderID,
			event.Source,
			event.EventName,
			event.Topic,
			event.SOPName,
			event.PayloadHash,
			event.PayloadBody,
			event.IdempotencyKey,
		).Scan(&id)
		if err != nil {
			return "", fmt.Errorf("failed to insert raw event: %w", err)
		}
	} else if r.db != nil {
		err := r.db.QueryRowContext(ctx, query,
			event.FounderID,
			event.Source,
			event.EventName,
			event.Topic,
			event.SOPName,
			event.PayloadHash,
			event.PayloadBody,
			event.IdempotencyKey,
		).Scan(&id)
		if err != nil {
			return "", fmt.Errorf("failed to insert raw event: %w", err)
		}
	} else {
		return "", fmt.Errorf("no database connection configured")
	}
	
	return id, nil
}

// InsertDLQ inserts an event into the dead letter queue
func (r *Repository) InsertDLQ(ctx context.Context, eventName, reason string, payload []byte) error {
	query := `
		INSERT INTO dead_letter_events
			(source, event_name, failure_reason, raw_payload)
		VALUES ($1, $2, $3, $4)
	`
	
	if r.pool != nil {
		_, err := r.pool.Exec(ctx, query, "razorpay", eventName, reason, payload)
		if err != nil {
			return fmt.Errorf("failed to insert DLQ event: %w", err)
		}
	} else if r.db != nil {
		_, err := r.db.ExecContext(ctx, query, "razorpay", eventName, reason, payload)
		if err != nil {
			return fmt.Errorf("failed to insert DLQ event: %w", err)
		}
	} else {
		return fmt.Errorf("no database connection configured")
	}
	
	return nil
}

// Ensure Repository implements RawEventStore
var _ RawEventStore = (*Repository)(nil)
