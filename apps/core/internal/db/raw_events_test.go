package db_test

import (
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// testFounderID creates a test founder and returns the ID
func testFounderID() uuid.UUID {
	return uuid.New()
}

// newUUID generates a new UUID string for test uniqueness
func newUUID() string {
	return uuid.New().String()
}

// TestRawEventsTableExists verifies the raw_events table exists after migration
func TestRawEventsTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'raw_events'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "raw_events table must exist after migration")
}

// TestRawEventInsertAndFetch tests basic CRUD operations on raw_events table
func TestRawEventInsertAndFetch(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	id := uuid.New()
	_, err := db.Exec(`
		INSERT INTO raw_events
			(id, founder_id, source, event_name, topic, sop_name,
			 payload_hash, payload_body)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`, id, testFounderID(), "razorpay", "payment.captured",
		"finance.revenue.captured", "SOP_REVENUE_RECEIVED",
		"sha256:abc123", `{"payment_id":"pay_test"}`)
	require.NoError(t, err)

	var count int
	err = db.QueryRow("SELECT COUNT(*) FROM raw_events WHERE id=$1", id).Scan(&count)
	require.NoError(t, err)
	assert.Equal(t, 1, count, "Should have exactly 1 raw_event with the test ID")
}

// TestIdempotencyKeyPreventsDoubleInsert tests the unique constraint on idempotency_key
func TestIdempotencyKeyPreventsDoubleInsert(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	ikey := "razorpay:pay_idem_test:" + newUUID()
	insert := func() error {
		_, err := db.Exec(`
			INSERT INTO raw_events
				(founder_id, source, event_name, topic, sop_name,
				 payload_hash, payload_body, idempotency_key)
			VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
		`, testFounderID(), "razorpay", "payment.captured",
			"finance.revenue.captured", "SOP_REVENUE_RECEIVED",
			"sha256:x", `{}`, ikey)
		return err
	}

	// First insert should succeed
	require.NoError(t, insert(), "First insert should succeed")

	// Second insert with same idempotency_key must fail on UNIQUE constraint
	err := insert()
	assert.Error(t, err, "duplicate idempotency_key must be rejected")
	assert.Contains(t, err.Error(), "duplicate key", "Error should mention duplicate key violation")
}

// TestSopJobsTableExists verifies the sop_jobs table exists after migration
func TestSopJobsTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'sop_jobs'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "sop_jobs table must exist after migration")
}

// TestConnectorStatesTableExists verifies the connector_states table exists after migration
func TestConnectorStatesTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'connector_states'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "connector_states table must exist after migration")
}

// TestDeadLetterEventsTableExists verifies the dead_letter_events table exists after migration
func TestDeadLetterEventsTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'dead_letter_events'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "dead_letter_events table must exist after migration")
}

// TestTransactionsTableExists verifies the transactions table exists after migration
func TestTransactionsTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'transactions'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "transactions table must exist after migration")
}

// TestAccountsPayableTableExists verifies the accounts_payable table exists after migration
func TestAccountsPayableTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'accounts_payable'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "accounts_payable table must exist after migration")
}

// TestComplianceCalendarTableExists verifies the compliance_calendar table exists after migration
func TestComplianceCalendarTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'compliance_calendar'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "compliance_calendar table must exist after migration")
}

// TestSopFindingsTableExists verifies the sop_findings table exists after migration
func TestSopFindingsTableExists(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	var exists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'sop_findings'
		)
	`).Scan(&exists)
	require.NoError(t, err)
	assert.True(t, exists, "sop_findings table must exist after migration")
}

// TestSopJobCRUD tests basic CRUD operations on sop_jobs table
func TestSopJobCRUD(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// First create a raw_event to reference
	rawEventID := uuid.New()
	_, err := db.Exec(`
		INSERT INTO raw_events
			(id, founder_id, source, event_name, topic, sop_name,
			 payload_hash, payload_body)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`, rawEventID, testFounderID(), "test_source", "test.event",
		"test.topic", "SOP_TEST", "sha256:test", `{}`)
	require.NoError(t, err)

	// Create SOP job
	var jobID uuid.UUID
	err = db.QueryRow(`
		INSERT INTO sop_jobs
			(founder_id, raw_event_id, sop_name, status, temporal_run_id, temporal_wf_id)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id
	`, testFounderID(), rawEventID, "SOP_REVENUE_RECEIVED", "pending", "run_123", "wf_456").Scan(&jobID)
	require.NoError(t, err, "Failed to insert sop_job")
	require.NotEmpty(t, jobID, "Created job ID should not be empty")

	// Verify job was created
	var status string
	err = db.QueryRow(`SELECT status FROM sop_jobs WHERE id = $1`, jobID).Scan(&status)
	require.NoError(t, err)
	assert.Equal(t, "pending", status, "Initial status should be 'pending'")

	// Update job status
	var updatedStatus string
	err = db.QueryRow(`
		UPDATE sop_jobs
		SET status = 'completed', completed_at = NOW()
		WHERE id = $1
		RETURNING status
	`, jobID).Scan(&updatedStatus)
	require.NoError(t, err)
	assert.Equal(t, "completed", updatedStatus, "Updated status should be 'completed'")
}

// TestConnectorStateUniqueConstraint tests the unique constraint on founder_id + connector
func TestConnectorStateUniqueConstraint(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	founderID := testFounderID()
	connector := "razorpay"

	// First insert should succeed
	_, err := db.Exec(`
		INSERT INTO connector_states
			(founder_id, connector, access_token, refresh_token, health)
		VALUES ($1, $2, $3, $4, $5)
	`, founderID, connector, "token1", "refresh1", "active")
	require.NoError(t, err, "First insert should succeed")

	// Second insert with same founder_id + connector must fail
	_, err = db.Exec(`
		INSERT INTO connector_states
			(founder_id, connector, access_token, refresh_token, health)
		VALUES ($1, $2, $3, $4, $5)
	`, founderID, connector, "token2", "refresh2", "active")
	assert.Error(t, err, "Duplicate founder_id + connector must be rejected")
	assert.Contains(t, err.Error(), "duplicate key", "Error should mention duplicate key violation")
}

// TestTransactionUniqueConstraint tests the unique constraint on founder_id + external_id
func TestTransactionUniqueConstraint(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	founderID := testFounderID()
	externalID := "txn_external_123"

	// First insert should succeed
	_, err := db.Exec(`
		INSERT INTO transactions
			(founder_id, txn_date, description, debit, credit, external_id)
		VALUES ($1, NOW(), $2, $3, $4, $5)
	`, founderID, "Test transaction", 100.00, 0.00, externalID)
	require.NoError(t, err, "First insert should succeed")

	// Second insert with same founder_id + external_id must fail
	_, err = db.Exec(`
		INSERT INTO transactions
			(founder_id, txn_date, description, debit, credit, external_id)
		VALUES ($1, NOW(), $2, $3, $4, $5)
	`, founderID, "Duplicate transaction", 200.00, 0.00, externalID)
	assert.Error(t, err, "Duplicate founder_id + external_id must be rejected")
	assert.Contains(t, err.Error(), "duplicate key", "Error should mention duplicate key violation")
}

// TestSopFindingWithFK tests foreign key relationship between sop_findings and sop_jobs
func TestSopFindingWithFK(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Create a raw_event first
	rawEventID := uuid.New()
	_, err := db.Exec(`
		INSERT INTO raw_events
			(id, founder_id, source, event_name, topic, sop_name,
			 payload_hash, payload_body)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`, rawEventID, testFounderID(), "test_source", "test.event",
		"test.topic", "SOP_TEST", "sha256:test", `{}`)
	require.NoError(t, err)

	// Create SOP job
	var jobID uuid.UUID
	err = db.QueryRow(`
		INSERT INTO sop_jobs
			(founder_id, raw_event_id, sop_name, status)
		VALUES ($1, $2, $3, $4)
		RETURNING id
	`, testFounderID(), rawEventID, "SOP_TEST", "pending").Scan(&jobID)
	require.NoError(t, err)

	// Create SOP finding referencing the job
	var findingID uuid.UUID
	err = db.QueryRow(`
		INSERT INTO sop_findings
			(sop_job_id, founder_id, sop_name, finding_type, headline, body, hitl_risk)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id
	`, jobID, testFounderID(), "SOP_TEST", "insight", "Test Headline", "Test body content", "low").Scan(&findingID)
	require.NoError(t, err, "Failed to insert sop_finding")
	require.NotEmpty(t, findingID, "Created finding ID should not be empty")

	// Verify finding was created with correct data
	var headline string
	err = db.QueryRow(`SELECT headline FROM sop_findings WHERE id = $1`, findingID).Scan(&headline)
	require.NoError(t, err)
	assert.Equal(t, "Test Headline", headline, "Headline should match")
}

// TestDeadLetterEventInsert tests inserting into dead_letter_events table
func TestDeadLetterEventInsert(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Create a raw_event first
	rawEventID := uuid.New()
	founderID := testFounderID()
	_, err := db.Exec(`
		INSERT INTO raw_events
			(id, founder_id, source, event_name, topic, sop_name,
			 payload_hash, payload_body)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`, rawEventID, founderID, "test_source", "test.event",
		"test.topic", "SOP_TEST", "sha256:test", `{}`)
	require.NoError(t, err)

	// Create dead letter event
	var dleID uuid.UUID
	err = db.QueryRow(`
		INSERT INTO dead_letter_events
			(raw_event_id, founder_id, source, event_name, failure_reason, raw_payload, retry_count)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id
	`, rawEventID, founderID, "test_source", "test.event", "Processing failed: timeout", `{"error": "timeout"}`, 3).Scan(&dleID)
	require.NoError(t, err, "Failed to insert dead_letter_event")
	require.NotEmpty(t, dleID, "Created DLE ID should not be empty")

	// Verify DLE was created
	var reason string
	var retries int
	err = db.QueryRow(`SELECT failure_reason, retry_count FROM dead_letter_events WHERE id = $1`, dleID).Scan(&reason, &retries)
	require.NoError(t, err)
	assert.Equal(t, "Processing failed: timeout", reason, "Failure reason should match")
	assert.Equal(t, 3, retries, "Retry count should match")
}

// TestAccountsPayableInsert tests inserting into accounts_payable table
func TestAccountsPayableInsert(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	founderID := testFounderID()
	vendorName := "Test Vendor Pvt Ltd"
	amount := 50000.00
	dueDate := "2026-04-15"
	invoiceNumber := "INV-2026-001"

	// Create accounts payable entry
	var apID uuid.UUID
	err := db.QueryRow(`
		INSERT INTO accounts_payable
			(founder_id, vendor_name, amount, currency, due_date, invoice_number, source, status)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id
	`, founderID, vendorName, amount, "INR", dueDate, invoiceNumber, "razorpay", "pending_approval").Scan(&apID)
	require.NoError(t, err, "Failed to insert accounts_payable")
	require.NotEmpty(t, apID, "Created AP ID should not be empty")

	// Verify AP was created
	var retAmount float64
	var retStatus string
	err = db.QueryRow(`SELECT amount, status FROM accounts_payable WHERE id = $1`, apID).Scan(&retAmount, &retStatus)
	require.NoError(t, err)
	assert.Equal(t, amount, retAmount, "Amount should match")
	assert.Equal(t, "pending_approval", retStatus, "Status should match")
}

// TestComplianceCalendarInsert tests inserting into compliance_calendar table
func TestComplianceCalendarInsert(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	founderID := testFounderID()
	filingType := "GST Monthly Return"
	dueDate := "2026-04-20"
	description := "GST filing for March 2026"

	// Create compliance calendar entry
	var ccID uuid.UUID
	err := db.QueryRow(`
		INSERT INTO compliance_calendar
			(founder_id, jurisdiction, filing_type, due_date, description, status)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id
	`, founderID, "IN", filingType, dueDate, description, "pending").Scan(&ccID)
	require.NoError(t, err, "Failed to insert compliance_calendar")
	require.NotEmpty(t, ccID, "Created CC ID should not be empty")

	// Verify CC was created
	var retFilingType string
	var retJurisdiction string
	err = db.QueryRow(`SELECT filing_type, jurisdiction FROM compliance_calendar WHERE id = $1`, ccID).Scan(&retFilingType, &retJurisdiction)
	require.NoError(t, err)
	assert.Equal(t, filingType, retFilingType, "Filing type should match")
	assert.Equal(t, "IN", retJurisdiction, "Jurisdiction should match default")
}

// TestRawEventsIndexes verifies indexes are created on raw_events table
func TestRawEventsIndexes(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Check for idx_raw_events_founder_source index
	var idxExists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM pg_indexes
			WHERE tablename = 'raw_events'
			AND indexname = 'idx_raw_events_founder_source'
		)
	`).Scan(&idxExists)
	require.NoError(t, err)
	assert.True(t, idxExists, "idx_raw_events_founder_source index must exist")

	// Check for idx_raw_events_idempotency index
	err = db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM pg_indexes
			WHERE tablename = 'raw_events'
			AND indexname = 'idx_raw_events_idempotency'
		)
	`).Scan(&idxExists)
	require.NoError(t, err)
	assert.True(t, idxExists, "idx_raw_events_idempotency index must exist")
}

// TestSopJobsIndexes verifies indexes are created on sop_jobs table
func TestSopJobsIndexes(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Check for idx_sop_jobs_founder_sop index
	var idxExists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM pg_indexes
			WHERE tablename = 'sop_jobs'
			AND indexname = 'idx_sop_jobs_founder_sop'
		)
	`).Scan(&idxExists)
	require.NoError(t, err)
	assert.True(t, idxExists, "idx_sop_jobs_founder_sop index must exist")

	// Check for idx_sop_jobs_status index
	err = db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM pg_indexes
			WHERE tablename = 'sop_jobs'
			AND indexname = 'idx_sop_jobs_status'
		)
	`).Scan(&idxExists)
	require.NoError(t, err)
	assert.True(t, idxExists, "idx_sop_jobs_status index must exist")
}

// TestTransactionsIndexes verifies indexes are created on transactions table
func TestTransactionsIndexes(t *testing.T) {
	db := getTestDB(t)
	defer db.Close()

	// Check for idx_transactions_founder_date index
	var idxExists bool
	err := db.QueryRow(`
		SELECT EXISTS (
			SELECT 1 FROM pg_indexes
			WHERE tablename = 'transactions'
			AND indexname = 'idx_transactions_founder_date'
		)
	`).Scan(&idxExists)
	require.NoError(t, err)
	assert.True(t, idxExists, "idx_transactions_founder_date index must exist")
}
