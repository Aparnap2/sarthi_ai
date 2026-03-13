-- name: InsertFinanceOp :one
INSERT INTO finance_ops (founder_id, task_type, payload, status, due_date)
VALUES ($1, $2, $3, $4, $5)
RETURNING *;

-- name: GetFinanceOpByID :one
SELECT * FROM finance_ops
WHERE id = $1;

-- name: ListFinanceOpsByFounder :many
SELECT * FROM finance_ops
WHERE founder_id = $1
ORDER BY created_at DESC;

-- name: ListFinanceOpsByStatus :many
SELECT * FROM finance_ops
WHERE status = $1
ORDER BY due_date ASC;

-- name: UpdateFinanceOpStatus :one
UPDATE finance_ops
SET status = $2,
    completed_at = CASE 
        WHEN $2 IN ('completed', 'auto_executed') AND completed_at IS NULL THEN NOW()
        WHEN $2 NOT IN ('completed', 'auto_executed') THEN NULL
        ELSE completed_at
    END,
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteFinanceOp :exec
DELETE FROM finance_ops WHERE id = $1;

-- name: InsertPeopleOp :one
INSERT INTO people_ops (founder_id, event_type, employee_name, payload, status, event_date)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING *;

-- name: GetPeopleOpByID :one
SELECT * FROM people_ops
WHERE id = $1;

-- name: ListPeopleOpsByFounder :many
SELECT * FROM people_ops
WHERE founder_id = $1
ORDER BY created_at DESC;

-- name: ListPeopleOpsByEventType :many
SELECT * FROM people_ops
WHERE event_type = $1
ORDER BY event_date DESC;

-- name: UpdatePeopleOpStatus :one
UPDATE people_ops
SET status = $2,
    completed_at = CASE WHEN $2 = 'completed' THEN NOW() ELSE completed_at END,
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeletePeopleOp :exec
DELETE FROM people_ops WHERE id = $1;

-- name: InsertLegalOp :one
INSERT INTO legal_ops (founder_id, document_type, document_name, expiry_date, esign_status, payload, status)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING *;

-- name: GetLegalOpByID :one
SELECT * FROM legal_ops
WHERE id = $1;

-- name: ListLegalOpsByFounder :many
SELECT * FROM legal_ops
WHERE founder_id = $1
ORDER BY created_at DESC;

-- name: ListLegalOpsExpiringSoon :many
SELECT * FROM legal_ops
WHERE expiry_date IS NOT NULL
  AND expiry_date <= NOW() + INTERVAL '30 days'
  AND esign_status IS DISTINCT FROM 'expired'
ORDER BY expiry_date ASC;

-- name: UpdateLegalOpStatus :one
UPDATE legal_ops
SET status = $2,
    esign_status = COALESCE($3, esign_status),
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteLegalOp :exec
DELETE FROM legal_ops WHERE id = $1;

-- name: InsertITAsset :one
INSERT INTO it_assets (founder_id, asset_type, asset_name, monthly_cost, last_used_date, renewal_date, payload, status)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING *;

-- name: GetITAssetByID :one
SELECT * FROM it_assets
WHERE id = $1;

-- name: ListITAssetsByFounder :many
SELECT * FROM it_assets
WHERE founder_id = $1
ORDER BY monthly_cost DESC;

-- name: ListITAssetsByStatus :many
SELECT * FROM it_assets
WHERE status = $1
ORDER BY asset_name ASC;

-- name: ListITAssetsRenewingSoon :many
SELECT * FROM it_assets
WHERE renewal_date IS NOT NULL
  AND renewal_date <= NOW() + INTERVAL '30 days'
  AND status = 'active'
ORDER BY renewal_date ASC;

-- name: UpdateITAssetStatus :one
UPDATE it_assets
SET status = $2,
    last_used_date = COALESCE($3, last_used_date),
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteITAsset :exec
DELETE FROM it_assets WHERE id = $1;

-- name: InsertAdminEvent :one
INSERT INTO admin_events (founder_id, event_type, title, payload, meeting_date, action_items, sop_reference)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING *;

-- name: GetAdminEventByID :one
SELECT * FROM admin_events
WHERE id = $1;

-- name: ListAdminEventsByFounder :many
SELECT * FROM admin_events
WHERE founder_id = $1
ORDER BY created_at DESC;

-- name: ListAdminEventsByType :many
SELECT * FROM admin_events
WHERE event_type = $1
ORDER BY meeting_date DESC;

-- name: UpdateAdminEvent :one
UPDATE admin_events
SET title = COALESCE($2, title),
    payload = COALESCE($3, payload),
    meeting_date = COALESCE($4, meeting_date),
    action_items = COALESCE($5, action_items),
    sop_reference = COALESCE($6, sop_reference),
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteAdminEvent :exec
DELETE FROM admin_events WHERE id = $1;
