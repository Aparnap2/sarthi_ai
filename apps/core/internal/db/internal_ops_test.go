package db_test

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// getTestDB returns a test database connection from environment variables.
// Priority: TEST_DATABASE_URL > DATABASE_URL > default localhost:5432
func getTestDB(t *testing.T) *sql.DB {
	t.Helper()

	// Get connection string from environment
	connStr := os.Getenv("TEST_DATABASE_URL")
	if connStr == "" {
		connStr = os.Getenv("DATABASE_URL")
	}
	if connStr == "" {
		// Fallback default for local development
		connStr = "postgres://iterateswarm:iterateswarm@localhost:5432/iterateswarm?sslmode=disable"
	}

	db, err := sql.Open("postgres", connStr)
	require.NoError(t, err, "Failed to open database connection")

	// Verify connection
	err = db.Ping()
	require.NoError(t, err, "Failed to ping database - ensure Docker PostgreSQL is running: docker ps | grep postgres")

	return db
}

// cleanupTable deletes all test data from a table (whitelist enforced)
func cleanupTable(t *testing.T, db *sql.DB, table string) {
	t.Helper()

	// Whitelist of allowed tables for cleanup
	allowedTables := map[string]bool{
		"finance_ops":   true,
		"people_ops":    true,
		"legal_ops":     true,
		"it_assets":     true,
		"admin_events":  true,
		"founders":      true,
		"trigger_log":   true,
		"memory_snapshot": true,
		"weekly_reflection": true,
		"company_context": true,
		"commitment":    true,
	}

	if !allowedTables[table] {
		t.Fatalf("Table %q not in allowed list - refusing to DELETE FROM unknown table", table)
		return
	}

	_, err := db.Exec(fmt.Sprintf("DELETE FROM %s WHERE 1=1", table))
	if err != nil {
		t.Logf("Warning: Failed to cleanup table %s: %v", table, err)
	}
}

// createTestFounder creates a test founder and returns the ID
func createTestFounder(t *testing.T, db *sql.DB, ctx context.Context, slackUserID string) uuid.UUID {
	t.Helper()
	var founderID uuid.UUID
	err := db.QueryRowContext(ctx, `
		INSERT INTO founders (slack_user_id, slack_team_id, name, stage)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (slack_user_id) DO UPDATE SET name = $3
		RETURNING id
	`, slackUserID, "test-team-id", "Test User", "building").Scan(&founderID)
	require.NoError(t, err, "Failed to create test founder")
	return founderID
}

// cleanupFounder deletes a test founder (cascades to child tables)
func cleanupFounder(t *testing.T, db *sql.DB, ctx context.Context, slackUserID string) {
	t.Helper()
	_, err := db.ExecContext(ctx, "DELETE FROM founders WHERE slack_user_id = $1", slackUserID)
	if err != nil {
		t.Fatalf("cleanupFounder: failed to delete founder %s: %v", slackUserID, err)
	}
}

// ═══════════════════════════════════════════════════════════════════════════════
// Finance Ops Tests
// ═══════════════════════════════════════════════════════════════════════════════

// TestFinanceOpsCRUD tests create/read/update/delete operations for finance_ops table
func TestFinanceOpsCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "finance_ops")
	ctx := context.Background()

	// Create a test founder first (required for FK constraints)
	founderID := createTestFounder(t, db, ctx, "test-finance-user")
	defer cleanupFounder(t, db, ctx, "test-finance-user")

	dueDate := time.Now().Add(24 * time.Hour)
	payload := map[string]interface{}{
		"invoice_id": "INV-2026-001",
		"amount":     5000.00,
		"vendor":     "AWS",
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("json marshal payload: %v", err)
	}

	// CREATE: Insert a finance_ops row
	var createdID uuid.UUID
	err = db.QueryRowContext(ctx, `
		INSERT INTO finance_ops (founder_id, task_type, payload, status, due_date)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`, founderID, "ar_reminder", payloadJSON, "pending", dueDate).Scan(&createdID)

	require.NoError(t, err, "Failed to insert finance_ops row")
	require.NotEmpty(t, createdID, "Created ID should not be empty")

	// READ: Read it back
	var (
		id          uuid.UUID
		retFounder  uuid.UUID
		retType     string
		retPayload  []byte
		retStatus   string
		retDueDate  time.Time
		retCreated  time.Time
		retUpdated  time.Time
		retComplete *time.Time
	)

	err = db.QueryRowContext(ctx, `
		SELECT id, founder_id, task_type, payload, status, due_date, completed_at, created_at, updated_at
		FROM finance_ops
		WHERE id = $1
	`, createdID).Scan(&id, &retFounder, &retType, &retPayload, &retStatus, &retDueDate, &retComplete, &retCreated, &retUpdated)

	require.NoError(t, err, "Failed to read finance_ops row")

	// VERIFY: All fields match
	assert.Equal(t, createdID, id, "ID should match")
	assert.Equal(t, founderID, retFounder, "FounderID should match")
	assert.Equal(t, "ar_reminder", retType, "TaskType should match")
	assert.Equal(t, "pending", retStatus, "Status should match")
	assert.InDelta(t, dueDate.Unix(), retDueDate.Unix(), 5, "DueDate should match within 5 seconds")

	// Verify payload JSON
	var retPayloadMap map[string]interface{}
	err = json.Unmarshal(retPayload, &retPayloadMap)
	require.NoError(t, err, "Failed to unmarshal payload")
	assert.Equal(t, "INV-2026-001", retPayloadMap["invoice_id"], "Invoice ID in payload should match")
	assert.Equal(t, 5000.00, retPayloadMap["amount"], "Amount in payload should match")

	// UPDATE: Mark as completed
	var updatedStatus string
	err = db.QueryRowContext(ctx, `
		UPDATE finance_ops
		SET status = 'completed', completed_at = NOW(), updated_at = NOW()
		WHERE id = $1
		RETURNING status
	`, createdID).Scan(&updatedStatus)

	require.NoError(t, err, "Failed to update finance_ops status")
	assert.Equal(t, "completed", updatedStatus, "Updated status should be 'completed'")

	// DELETE: Clean up
	_, err = db.ExecContext(ctx, "DELETE FROM finance_ops WHERE id = $1", createdID)
	require.NoError(t, err, "Failed to delete finance_ops row")

	// Verify deletion
	var count int
	err = db.QueryRowContext(ctx, "SELECT COUNT(*) FROM finance_ops WHERE id = $1", createdID).Scan(&count)
	require.NoError(t, err, "Failed to count deleted row")
	assert.Equal(t, 0, count, "Row should be deleted")
}

// TestFinanceOpsByFounder tests listing finance ops by founder
func TestFinanceOpsByFounder(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "finance_ops")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-finance-list")
	defer cleanupFounder(t, db, ctx, "test-finance-list")

	// Insert 3 finance ops
	for i := 0; i < 3; i++ {
		payload := fmt.Sprintf(`{"task": %d}`, i)
		_, err := db.ExecContext(ctx, `
			INSERT INTO finance_ops (founder_id, task_type, payload, status)
			VALUES ($1, $2, $3, $4)
		`, founderID, "ap_due", payload, "pending")
		require.NoError(t, err, "Failed to insert finance_ops")
	}

	// Query by founder
	rows, err := db.QueryContext(ctx, `
		SELECT COUNT(*) FROM finance_ops WHERE founder_id = $1
	`, founderID)
	require.NoError(t, err, "Failed to query by founder")
	defer rows.Close()

	var count int
	require.True(t, rows.Next(), "Should have at least one row")
	err = rows.Scan(&count)
	require.NoError(t, err, "Failed to scan count")

	assert.Equal(t, 3, count, "Should have 3 finance ops for this founder")
}

// ═══════════════════════════════════════════════════════════════════════════════
// People Ops Tests
// ═══════════════════════════════════════════════════════════════════════════════

// TestPeopleOpsCRUD tests create/read/update/delete operations for people_ops table
func TestPeopleOpsCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "people_ops")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-people-user")
	defer cleanupFounder(t, db, ctx, "test-people-user")

	eventDate := time.Now().Add(7 * 24 * time.Hour)
	payload := map[string]interface{}{
		"department": "Engineering",
		"start_date": "2026-03-20",
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("json marshal payload: %v", err)
	}

	// CREATE
	var createdID uuid.UUID
	err = db.QueryRowContext(ctx, `
		INSERT INTO people_ops (founder_id, event_type, employee_name, payload, status, event_date)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id
	`, founderID, "onboarding", "John Doe", payloadJSON, "pending", eventDate).Scan(&createdID)

	require.NoError(t, err, "Failed to insert people_ops row")
	require.NotEmpty(t, createdID)

	// READ
	var (
		id          uuid.UUID
		retFounder  uuid.UUID
		retType     string
		retEmpName  string
		retStatus   string
		retEventDate time.Time
		retComplete *time.Time
	)

	err = db.QueryRowContext(ctx, `
		SELECT id, founder_id, event_type, employee_name, status, event_date, completed_at
		FROM people_ops
		WHERE id = $1
	`, createdID).Scan(&id, &retFounder, &retType, &retEmpName, &retStatus, &retEventDate, &retComplete)

	require.NoError(t, err, "Failed to read people_ops row")

	// VERIFY
	assert.Equal(t, createdID, id)
	assert.Equal(t, founderID, retFounder)
	assert.Equal(t, "onboarding", retType)
	assert.Equal(t, "John Doe", retEmpName)
	assert.Equal(t, "pending", retStatus)

	// UPDATE
	var updatedStatus string
	err = db.QueryRowContext(ctx, `
		UPDATE people_ops
		SET status = 'completed', completed_at = NOW()
		WHERE id = $1
		RETURNING status
	`, createdID).Scan(&updatedStatus)

	require.NoError(t, err)
	assert.Equal(t, "completed", updatedStatus)

	// DELETE
	_, err = db.ExecContext(ctx, "DELETE FROM people_ops WHERE id = $1", createdID)
	require.NoError(t, err)
}

// TestPeopleOpsByEventType tests listing people ops by event type
func TestPeopleOpsByEventType(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "people_ops")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-people-event")
	defer cleanupFounder(t, db, ctx, "test-people-event")

	// Insert different event types
	events := []string{"onboarding", "leave_request", "appraisal"}
	for _, eventType := range events {
		_, err := db.ExecContext(ctx, `
			INSERT INTO people_ops (founder_id, event_type, employee_name, status)
			VALUES ($1, $2, $3, $4)
		`, founderID, eventType, "Test Employee", "pending")
		require.NoError(t, err)
	}

	// Query by event type
	var count int
	err := db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM people_ops WHERE event_type = $1
	`, "onboarding").Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 1, count, "Should have 1 onboarding event")
}

// ═══════════════════════════════════════════════════════════════════════════════
// Legal Ops Tests
// ═══════════════════════════════════════════════════════════════════════════════

// TestLegalOpsCRUD tests create/read/update/delete operations for legal_ops table
func TestLegalOpsCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "legal_ops")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-legal-user")
	defer cleanupFounder(t, db, ctx, "test-legal-user")

	expiryDate := time.Now().Add(365 * 24 * time.Hour)
	payload := map[string]interface{}{
		"counterparty": "Acme Corp",
		"value":        100000,
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("json marshal payload: %v", err)
	}

	// CREATE
	var createdID uuid.UUID
	err = db.QueryRowContext(ctx, `
		INSERT INTO legal_ops (founder_id, document_type, document_name, expiry_date, esign_status, payload, status)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id
	`, founderID, "nda", "NDA - Acme Corp", expiryDate, "pending", payloadJSON, "pending").Scan(&createdID)

	require.NoError(t, err, "Failed to insert legal_ops row")
	require.NotEmpty(t, createdID)

	// READ
	var (
		id         uuid.UUID
		retFounder uuid.UUID
		retDocType string
		retDocName string
		retExpiry  time.Time
		retEsign   string
		retStatus  string
	)

	err = db.QueryRowContext(ctx, `
		SELECT id, founder_id, document_type, document_name, expiry_date, esign_status, status
		FROM legal_ops
		WHERE id = $1
	`, createdID).Scan(&id, &retFounder, &retDocType, &retDocName, &retExpiry, &retEsign, &retStatus)

	require.NoError(t, err, "Failed to read legal_ops row")

	// VERIFY
	assert.Equal(t, createdID, id)
	assert.Equal(t, founderID, retFounder)
	assert.Equal(t, "nda", retDocType)
	assert.Equal(t, "NDA - Acme Corp", retDocName)
	assert.Equal(t, "pending", retEsign)
	assert.Equal(t, "pending", retStatus)

	// UPDATE
	var updatedEsign string
	err = db.QueryRowContext(ctx, `
		UPDATE legal_ops
		SET esign_status = 'signed', status = 'completed', updated_at = NOW()
		WHERE id = $1
		RETURNING esign_status
	`, createdID).Scan(&updatedEsign)

	require.NoError(t, err)
	assert.Equal(t, "signed", updatedEsign)

	// DELETE
	_, err = db.ExecContext(ctx, "DELETE FROM legal_ops WHERE id = $1", createdID)
	require.NoError(t, err)
}

// TestLegalOpsExpiringSoon tests querying legal ops expiring soon
func TestLegalOpsExpiringSoon(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "legal_ops")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-legal-expiry")
	defer cleanupFounder(t, db, ctx, "test-legal-expiry")

	// Insert expiring document (in 10 days)
	expirySoon := time.Now().Add(10 * 24 * time.Hour)
	_, err := db.ExecContext(ctx, `
		INSERT INTO legal_ops (founder_id, document_type, document_name, expiry_date, esign_status)
		VALUES ($1, $2, $3, $4, $5)
	`, founderID, "contract", "Expiring Contract", expirySoon, "pending")
	require.NoError(t, err)

	// Insert non-expiring document (in 100 days)
	expiryLater := time.Now().Add(100 * 24 * time.Hour)
	_, err = db.ExecContext(ctx, `
		INSERT INTO legal_ops (founder_id, document_type, document_name, expiry_date, esign_status)
		VALUES ($1, $2, $3, $4, $5)
	`, founderID, "contract", "Later Contract", expiryLater, "pending")
	require.NoError(t, err)

	// Query expiring soon (within 30 days)
	var count int
	err = db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM legal_ops
		WHERE expiry_date IS NOT NULL
		  AND expiry_date <= NOW() + INTERVAL '30 days'
		  AND esign_status != 'expired'
	`).Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 1, count, "Should have 1 document expiring soon")
}

// ═══════════════════════════════════════════════════════════════════════════════
// IT Assets Tests
// ═══════════════════════════════════════════════════════════════════════════════

// TestITAssetsCRUD tests create/read/update/delete operations for it_assets table
func TestITAssetsCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "it_assets")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-it-user")
	defer cleanupFounder(t, db, ctx, "test-it-user")

	lastUsed := time.Now().Add(-24 * time.Hour)
	renewalDate := time.Now().Add(30 * 24 * time.Hour)
	payload := map[string]interface{}{
		"vendor": "GitHub",
		"seats":  5,
		"plan":   "Enterprise",
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("json marshal payload: %v", err)
	}

	// CREATE
	var createdID uuid.UUID
	err = db.QueryRowContext(ctx, `
		INSERT INTO it_assets (founder_id, asset_type, asset_name, monthly_cost, last_used_date, renewal_date, payload, status)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id
	`, founderID, "saas_subscription", "GitHub Enterprise", 21.00, lastUsed, renewalDate, payloadJSON, "active").Scan(&createdID)

	require.NoError(t, err, "Failed to insert it_assets row")
	require.NotEmpty(t, createdID)

	// READ
	var (
		id       uuid.UUID
		retFounder uuid.UUID
		retType  string
		retName  string
		retCost  float64
		retStatus string
	)

	err = db.QueryRowContext(ctx, `
		SELECT id, founder_id, asset_type, asset_name, monthly_cost, status
		FROM it_assets
		WHERE id = $1
	`, createdID).Scan(&id, &retFounder, &retType, &retName, &retCost, &retStatus)

	require.NoError(t, err, "Failed to read it_assets row")

	// VERIFY
	assert.Equal(t, createdID, id)
	assert.Equal(t, founderID, retFounder)
	assert.Equal(t, "saas_subscription", retType)
	assert.Equal(t, "GitHub Enterprise", retName)
	assert.Equal(t, 21.00, retCost)
	assert.Equal(t, "active", retStatus)

	// UPDATE - mark as unused
	var updatedStatus string
	err = db.QueryRowContext(ctx, `
		UPDATE it_assets
		SET status = 'unused', updated_at = NOW()
		WHERE id = $1
		RETURNING status
	`, createdID).Scan(&updatedStatus)

	require.NoError(t, err)
	assert.Equal(t, "unused", updatedStatus)

	// DELETE
	_, err = db.ExecContext(ctx, "DELETE FROM it_assets WHERE id = $1", createdID)
	require.NoError(t, err)
}

// TestITAssetsByStatus tests listing IT assets by status
func TestITAssetsByStatus(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "it_assets")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-it-status")
	defer cleanupFounder(t, db, ctx, "test-it-status")

	// Insert assets with different statuses
	assets := []struct {
		name   string
		status string
	}{
		{"Active SaaS", "active"},
		{"Unused Tool", "unused"},
		{"Cancelled Service", "cancelled"},
	}

	for _, asset := range assets {
		_, err := db.ExecContext(ctx, `
			INSERT INTO it_assets (founder_id, asset_type, asset_name, status)
			VALUES ($1, $2, $3, $4)
		`, founderID, "saas_subscription", asset.name, asset.status)
		require.NoError(t, err)
	}

	// Query active assets
	var count int
	err := db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM it_assets WHERE status = $1
	`, "active").Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 1, count, "Should have 1 active asset")
}

// ═══════════════════════════════════════════════════════════════════════════════
// Admin Events Tests
// ═══════════════════════════════════════════════════════════════════════════════

// TestAdminEventsCRUD tests create/read/update/delete operations for admin_events table
func TestAdminEventsCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "admin_events")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-admin-user")
	defer cleanupFounder(t, db, ctx, "test-admin-user")

	meetingDate := time.Now().Add(48 * time.Hour)
	payload := map[string]interface{}{
		"location":  "Zoom",
		"organizer": "CEO",
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("json marshal payload: %v", err)
	}
	actionItems := []map[string]interface{}{
		{"task": "Review Q1 metrics", "assignee": "CFO"},
		{"task": "Update hiring plan", "assignee": "CTO"},
	}
	actionItemsJSON, err := json.Marshal(actionItems)
	if err != nil {
		t.Fatalf("json marshal action items: %v", err)
	}

	// CREATE
	var createdID uuid.UUID
	err = db.QueryRowContext(ctx, `
		INSERT INTO admin_events (founder_id, event_type, title, payload, meeting_date, action_items, sop_reference)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id
	`, founderID, "meeting", "Q1 Review Meeting", payloadJSON, meetingDate, actionItemsJSON, "sops/q1-review.md").Scan(&createdID)

	require.NoError(t, err, "Failed to insert admin_events row")
	require.NotEmpty(t, createdID)

	// READ
	var (
		id        uuid.UUID
		retFounder uuid.UUID
		retType   string
		retTitle  string
		retMeeting time.Time
		retAction []byte
		retSOP    string
	)

	err = db.QueryRowContext(ctx, `
		SELECT id, founder_id, event_type, title, meeting_date, action_items, sop_reference
		FROM admin_events
		WHERE id = $1
	`, createdID).Scan(&id, &retFounder, &retType, &retTitle, &retMeeting, &retAction, &retSOP)

	require.NoError(t, err, "Failed to read admin_events row")

	// VERIFY
	assert.Equal(t, createdID, id)
	assert.Equal(t, founderID, retFounder)
	assert.Equal(t, "meeting", retType)
	assert.Equal(t, "Q1 Review Meeting", retTitle)
	assert.Equal(t, "sops/q1-review.md", retSOP)

	// Verify action items
	var retActionItems []map[string]interface{}
	err = json.Unmarshal(retAction, &retActionItems)
	require.NoError(t, err, "Failed to unmarshal action items")
	assert.Len(t, retActionItems, 2, "Should have 2 action items")
	assert.Equal(t, "Review Q1 metrics", retActionItems[0]["task"])

	// UPDATE
	var updatedTitle string
	err = db.QueryRowContext(ctx, `
		UPDATE admin_events
		SET title = $2, updated_at = NOW()
		WHERE id = $1
		RETURNING title
	`, createdID, "Updated Q1 Review").Scan(&updatedTitle)

	require.NoError(t, err)
	assert.Equal(t, "Updated Q1 Review", updatedTitle)

	// DELETE
	_, err = db.ExecContext(ctx, "DELETE FROM admin_events WHERE id = $1", createdID)
	require.NoError(t, err)
}

// TestAdminEventsByType tests listing admin events by type
func TestAdminEventsByType(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	cleanupTable(t, db, "admin_events")
	ctx := context.Background()

	// Create a test founder first
	founderID := createTestFounder(t, db, ctx, "test-admin-type")
	defer cleanupFounder(t, db, ctx, "test-admin-type")

	// Insert different event types
	events := []string{"meeting", "action_item", "sop", "announcement"}
	for _, eventType := range events {
		_, err := db.ExecContext(ctx, `
			INSERT INTO admin_events (founder_id, event_type, title)
			VALUES ($1, $2, $3)
		`, founderID, eventType, fmt.Sprintf("Test %s", eventType))
		require.NoError(t, err)
	}

	// Query by type
	var count int
	err := db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM admin_events WHERE event_type = $1
	`, "meeting").Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 1, count, "Should have 1 meeting event")

	// Query all events for founder
	err = db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM admin_events WHERE founder_id = $1
	`, founderID).Scan(&count)

	require.NoError(t, err)
	assert.Equal(t, 4, count, "Should have 4 total events")
}

// ═══════════════════════════════════════════════════════════════════════════════
// Integration Tests - Multiple Tables
// ═══════════════════════════════════════════════════════════════════════════════

// TestInternalOpsIntegration tests operations across all 5 tables
func TestInternalOpsIntegration(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Cleanup all tables
	cleanupTable(t, db, "finance_ops")
	cleanupTable(t, db, "people_ops")
	cleanupTable(t, db, "legal_ops")
	cleanupTable(t, db, "it_assets")
	cleanupTable(t, db, "admin_events")

	ctx := context.Background()

	// Create a test founder first (required for FK constraints)
	founderID := createTestFounder(t, db, ctx, "test-integration-user")
	defer cleanupFounder(t, db, ctx, "test-integration-user")

	// Create one record in each table
	tables := []string{"finance_ops", "people_ops", "legal_ops", "it_assets", "admin_events"}
	for _, table := range tables {
		var err error
		switch table {
		case "finance_ops":
			_, err = db.ExecContext(ctx, `
				INSERT INTO finance_ops (founder_id, task_type, payload, status)
				VALUES ($1, $2, $3, $4)
			`, founderID, "ar_reminder", `{"test": true}`, "pending")
		case "people_ops":
			_, err = db.ExecContext(ctx, `
				INSERT INTO people_ops (founder_id, event_type, employee_name, status)
				VALUES ($1, $2, $3, $4)
			`, founderID, "onboarding", "Test User", "pending")
		case "legal_ops":
			_, err = db.ExecContext(ctx, `
				INSERT INTO legal_ops (founder_id, document_type, document_name, esign_status, status)
				VALUES ($1, $2, $3, $4, $5)
			`, founderID, "nda", "Test NDA", "pending", "pending")
		case "it_assets":
			_, err = db.ExecContext(ctx, `
				INSERT INTO it_assets (founder_id, asset_type, asset_name, status)
				VALUES ($1, $2, $3, $4)
			`, founderID, "saas_subscription", "Test Asset", "active")
		case "admin_events":
			_, err = db.ExecContext(ctx, `
				INSERT INTO admin_events (founder_id, event_type, title)
				VALUES ($1, $2, $3)
			`, founderID, "meeting", "Test Meeting")
		}
		require.NoError(t, err, "Failed to insert into %s", table)
	}

	// Verify all tables have one record for this founder
	for _, table := range tables {
		var count int
		err := db.QueryRowContext(ctx, fmt.Sprintf(
			"SELECT COUNT(*) FROM %s WHERE founder_id = $1", table), founderID).Scan(&count)
		require.NoError(t, err, "Failed to count %s", table)
		assert.Equal(t, 1, count, "Should have 1 record in %s", table)
	}
}
