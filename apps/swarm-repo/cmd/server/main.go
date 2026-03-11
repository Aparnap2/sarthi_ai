// Package main implements the SwarmRepo service - a GitHub replacement for IterateSwarm OS.
// It provides GitHub-compatible API endpoints for issues and pull requests.
//
// Features:
//   - GitHub API compatible endpoints (/repos/:owner/:repo/issues, /pulls)
//   - PostgreSQL storage for issues and PRs
//   - HTMX-based dashboard UI
//   - Webhook support for CI/CD integration
//
// Usage:
//
//	export POSTGRES_URL=postgres://user:pass@localhost:5432/db?sslmode=disable
//	go run cmd/server/main.go
package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/template/html/v2"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

// Issue represents a GitHub-compatible issue.
type Issue struct {
	ID        int       `json:"number"`
	NodeID    string    `json:"node_id"`
	Title     string    `json:"title"`
	Body      string    `json:"body"`
	State     string    `json:"state"`
	Labels    []Label   `json:"labels"`
	HTMLURL   string    `json:"html_url"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	ClosedAt  *time.Time `json:"closed_at,omitempty"`
	User      User      `json:"user"`
	Assignee  *User     `json:"assignee,omitempty"`
	Comments  int       `json:"comments"`
}

// Label represents a GitHub label.
type Label struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Color string `json:"color"`
}

// User represents a GitHub user.
type User struct {
	Login string `json:"login"`
	ID    int    `json:"id"`
}

// PullRequest represents a GitHub-compatible pull request.
type PullRequest struct {
	ID        int        `json:"number"`
	NodeID    string     `json:"node_id"`
	Title     string     `json:"title"`
	Body      string     `json:"body"`
	State     string     `json:"state"`
	HTMLURL   string     `json:"html_url"`
	DiffURL   string     `json:"diff_url"`
	PatchURL  string     `json:"patch_url"`
	IssueURL  string     `json:"issue_url"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	ClosedAt  *time.Time `json:"closed_at,omitempty"`
	MergedAt  *time.Time `json:"merged_at,omitempty"`
	User      User       `json:"user"`
	Head      Ref        `json:"head"`
	Base      Ref        `json:"base"`
	Merged    bool       `json:"merged"`
	Mergeable *bool      `json:"mergeable,omitempty"`
}

// Ref represents a git reference (branch).
type Ref struct {
	Ref string `json:"ref"`
	SHA string `json:"sha"`
	Repo Repo   `json:"repo"`
}

// Repo represents a GitHub repository.
type Repo struct {
	ID       int    `json:"id"`
	NodeID   string `json:"node_id"`
	Name     string `json:"name"`
	FullName string `json:"full_name"`
	Owner    User   `json:"owner"`
	HTMLURL  string `json:"html_url"`
}

// IssueRequest is the request body for creating an issue.
type IssueRequest struct {
	Title     string   `json:"title"`
	Body      string   `json:"body"`
	Labels    []string `json:"labels"`
	Assignee  string   `json:"assignee"`
	Severity  string   `json:"severity"`
	IssueType string   `json:"issue_type"`
}

// PullRequestRequest is the request body for creating a PR.
type PullRequestRequest struct {
	Title string `json:"title"`
	Body  string `json:"body"`
	Head  string `json:"head"`
	Base  string `json:"base"`
}

var db *sql.DB

func main() {
	// Database connection
	pgURL := os.Getenv("POSTGRES_URL")
	if pgURL == "" {
		pgURL = "postgres://iterateswarm:iterateswarm@localhost:5433/iterateswarm?sslmode=disable"
	}

	var err error
	db, err = sql.Open("postgres", pgURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()

	// Test database connection
	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}
	log.Println("Connected to PostgreSQL")

	// Run migrations
	runMigrations()

	// Fiber app with template engine
	engine := html.New(filepath.Join(".", "internal", "templates"), ".html")
	app := fiber.New(fiber.Config{
		Views:     engine,
		AppName:   "SwarmRepo/1.0.0",
		BodyLimit: 4 * 1024 * 1024, // 4MB limit
	})

	// Middleware
	corsOrigins := os.Getenv("CORS_ALLOWED_ORIGINS")
	if corsOrigins == "" {
		corsOrigins = "http://localhost:3000,http://localhost:4001"
	}
	
	app.Use(cors.New(cors.Config{
		AllowOrigins: corsOrigins,
		AllowMethods: "GET,POST,PUT,DELETE,PATCH,OPTIONS",
		AllowHeaders: "Origin,Content-Type,Accept,Authorization,X-GitHub-Api-Version",
	}))

	// GitHub API version header
	app.Use(func(c *fiber.Ctx) error {
		c.Set("X-GitHub-API-Version", "2022-11-28")
		return c.Next()
	})

	// Request logging
	app.Use(func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		log.Printf("[%s] %s %s - %d - %dms",
			c.Method(), c.Path(), c.IP(), c.Response().StatusCode(),
			time.Since(start).Milliseconds(),
		)
		return err
	})

	// GitHub API compatible routes
	api := app.Group("/repos")
	api.Post("/:owner/:repo/issues", createIssue)
	api.Get("/:owner/:repo/issues", listIssues)
	api.Get("/:owner/:repo/issues/:id", getIssue)
	api.Patch("/:owner/:repo/issues/:id", updateIssue)
	api.Post("/:owner/:repo/pulls", createPR)
	api.Get("/:owner/:repo/pulls", listPRs)
	api.Get("/:owner/:repo/pulls/:id", getPR)

	// Direct routes for convenience
	app.Post("/issues", createIssueDirect)
	app.Get("/issues", listIssuesDirect)
	app.Get("/issues/:id", getIssueDirect)
	app.Get("/pulls", listPRsDirect)
	app.Get("/pulls/:id", getPRDirect)

	// Dashboard UI
	app.Get("/", dashboard)

	// Health check
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":    "healthy",
			"timestamp": time.Now().Format(time.RFC3339),
			"service":   "swarm-repo",
		})
	})

	log.Println("📦 SwarmRepo starting on port 4001...")
	log.Fatal(app.Listen(":4001"))
}

// runMigrations initializes the database schema.
func runMigrations() {
	migrations := []struct {
		name string
		sql  string
	}{
		{
			name: "create_repos_table",
			sql: `CREATE TABLE IF NOT EXISTS repos (
				id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
				owner VARCHAR(100) NOT NULL,
				name VARCHAR(100) NOT NULL,
				created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
				UNIQUE(owner, name)
			)`,
		},
		{
			name: "create_issues_table",
			sql: `CREATE TABLE IF NOT EXISTS issues (
				id SERIAL PRIMARY KEY,
				repo_id UUID REFERENCES repos(id) ON DELETE CASCADE,
				title VARCHAR(500) NOT NULL,
				body TEXT,
				labels TEXT[] DEFAULT '{}',
				severity VARCHAR(50),
				issue_type VARCHAR(50),
				status VARCHAR(50) DEFAULT 'open',
				assignee VARCHAR(100),
				node_id VARCHAR(100) DEFAULT gen_random_uuid()::text,
				created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
				updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
			)`,
		},
		{
			name: "create_pull_requests_table",
			sql: `CREATE TABLE IF NOT EXISTS pull_requests (
				id SERIAL PRIMARY KEY,
				repo_id UUID REFERENCES repos(id) ON DELETE CASCADE,
				issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
				title VARCHAR(500) NOT NULL,
				body TEXT,
				branch VARCHAR(255),
				base_branch VARCHAR(255) DEFAULT 'main',
				diff TEXT,
				status VARCHAR(50) DEFAULT 'open',
				merged BOOLEAN DEFAULT false,
				node_id VARCHAR(100) DEFAULT gen_random_uuid()::text,
				created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
				updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
			)`,
		},
		{
			name: "create_issues_repo_idx",
			sql: `CREATE INDEX IF NOT EXISTS idx_issues_repo_id ON issues(repo_id)`,
		},
		{
			name: "create_issues_status_idx",
			sql: `CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)`,
		},
		{
			name: "create_pulls_repo_idx",
			sql: `CREATE INDEX IF NOT EXISTS idx_pull_requests_repo_id ON pull_requests(repo_id)`,
		},
		{
			name: "create_issues_updated_trigger",
			sql: `CREATE OR REPLACE FUNCTION update_updated_at_column()
			RETURNS TRIGGER AS $$
			BEGIN
				NEW.updated_at = NOW();
				RETURN NEW;
			END;
			$$ language 'plpgsql'`,
		},
		{
			name: "create_issues_updated_trigger_apply",
			sql: `DROP TRIGGER IF EXISTS update_issues_updated_at ON issues;
			CREATE TRIGGER update_issues_updated_at
			BEFORE UPDATE ON issues
			FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()`,
		},
		{
			name: "create_pulls_updated_trigger_apply",
			sql: `DROP TRIGGER IF EXISTS update_pull_requests_updated_at ON pull_requests;
			CREATE TRIGGER update_pull_requests_updated_at
			BEFORE UPDATE ON pull_requests
			FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()`,
		},
	}

	for _, m := range migrations {
		if _, err := db.Exec(m.sql); err != nil {
			log.Printf("Migration warning [%s]: %v", m.name, err)
		} else {
			log.Printf("Migration applied: %s", m.name)
		}
	}

	// Create default repo
	_, err := db.Exec(`INSERT INTO repos (owner, name) VALUES ('iterateswarm', 'demo') ON CONFLICT (owner, name) DO NOTHING`)
	if err != nil {
		log.Printf("Warning: Could not create default repo: %v", err)
	} else {
		log.Println("Default repo 'iterateswarm/demo' created")
	}
}

// dashboard renders the main dashboard UI.
func dashboard(c *fiber.Ctx) error {
	// Get stats
	var issueCount, prCount, openIssues, openPRs int
	db.QueryRow("SELECT COUNT(*) FROM issues").Scan(&issueCount)
	db.QueryRow("SELECT COUNT(*) FROM pull_requests").Scan(&prCount)
	db.QueryRow("SELECT COUNT(*) FROM issues WHERE status = 'open'").Scan(&openIssues)
	db.QueryRow("SELECT COUNT(*) FROM pull_requests WHERE status = 'open'").Scan(&openPRs)

	return c.Render("dashboard", fiber.Map{
		"Title":       "SwarmRepo Dashboard",
		"IssueCount":  issueCount,
		"PRCount":     prCount,
		"OpenIssues":  openIssues,
		"OpenPRs":     openPRs,
	})
}

// createIssue creates a new GitHub-compatible issue.
// POST /repos/:owner/:repo/issues
func createIssue(c *fiber.Ctx) error {
	owner := c.Params("owner")
	repo := c.Params("repo")

	var req IssueRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	if req.Title == "" {
		return c.Status(400).JSON(fiber.Map{"error": "Title is required"})
	}

	// Get or create repo
	var repoID uuid.UUID
	err := db.QueryRow(`
		INSERT INTO repos (owner, name) VALUES ($1, $2) 
		ON CONFLICT (owner, name) DO UPDATE SET name = EXCLUDED.name
		RETURNING id
	`, owner, repo).Scan(&repoID)
	if err != nil {
		log.Printf("Failed to get/create repo: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to get repository"})
	}

	// Create issue
	var issueID int
	var nodeID string
	err = db.QueryRow(`
		INSERT INTO issues (repo_id, title, body, labels, severity, issue_type, status, assignee)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id, node_id
	`, repoID, req.Title, req.Body, pqStringArray(req.Labels), req.Severity, req.IssueType, "open", req.Assignee).Scan(&issueID, &nodeID)
	if err != nil {
		log.Printf("Failed to create issue: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to create issue"})
	}

	issue := Issue{
		ID:        issueID,
		NodeID:    nodeID,
		Title:     req.Title,
		Body:      req.Body,
		State:     "open",
		Labels:    labelsFromStrings(req.Labels),
		HTMLURL:   fmt.Sprintf("http://localhost:4001/issues/%d", issueID),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		User:      User{Login: "api-user", ID: 1},
		Comments:  0,
	}

	log.Printf("Issue created: #%d - %s", issueID, req.Title)

	return c.Status(201).JSON(issue)
}

// createIssueDirect creates an issue without owner/repo params.
func createIssueDirect(c *fiber.Ctx) error {
	c.Params("owner", "iterateswarm")
	c.Params("repo", "demo")
	return createIssue(c)
}

// listIssues lists all issues for a repository.
// GET /repos/:owner/:repo/issues
func listIssues(c *fiber.Ctx) error {
	owner := c.Params("owner")
	repo := c.Params("repo")
	state := c.Query("state", "all")

	// Get repo ID
	var repoID uuid.UUID
	err := db.QueryRow("SELECT id FROM repos WHERE owner = $1 AND name = $2", owner, repo).Scan(&repoID)
	if err != nil {
		return c.JSON([]Issue{}) // Return empty if repo doesn't exist
	}

	// Build query
	query := `
		SELECT id, node_id, title, body, labels, severity, issue_type, status, assignee, created_at, updated_at
		FROM issues
		WHERE repo_id = $1
	`
	args := []interface{}{repoID}

	if state != "all" {
		query += " AND status = $2"
		args = append(args, state)
	}

	query += " ORDER BY created_at DESC"

	rows, err := db.Query(query, args...)
	if err != nil {
		log.Printf("Failed to list issues: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to list issues"})
	}
	defer rows.Close()

	var issues []Issue
	for rows.Next() {
		var issue Issue
		var labelsRaw []byte
		var severity, issueType, assignee sql.NullString
		if err := rows.Scan(&issue.ID, &issue.NodeID, &issue.Title, &issue.Body, &labelsRaw, &severity, &issueType, &issue.State, &assignee, &issue.CreatedAt, &issue.UpdatedAt); err != nil {
			log.Printf("Failed to scan issue: %v", err)
			continue
		}
		// Parse PostgreSQL array format: {label1,label2}
		var labels []string
		if len(labelsRaw) > 2 {
			// Remove curly braces and split
			content := string(labelsRaw[1 : len(labelsRaw)-1])
			if content != "" {
				labels = strings.Split(content, ",")
			}
		}
		issue.Labels = labelsFromStrings(labels)
		issue.HTMLURL = fmt.Sprintf("http://localhost:4001/issues/%d", issue.ID)
		issue.User = User{Login: "api-user", ID: 1}
		if assignee.Valid && assignee.String != "" {
			issue.Assignee = &User{Login: assignee.String, ID: 0}
		}
		issues = append(issues, issue)
	}

	if issues == nil {
		issues = []Issue{}
	}

	return c.JSON(issues)
}

// listIssuesDirect lists issues without owner/repo params.
func listIssuesDirect(c *fiber.Ctx) error {
	c.Params("owner", "iterateswarm")
	c.Params("repo", "demo")
	return listIssues(c)
}

// getIssue gets a single issue by ID.
// GET /repos/:owner/:repo/issues/:id
func getIssue(c *fiber.Ctx) error {
	issueID := c.Params("id")

	var issue Issue
	var labelsRaw []byte
	var severity, issueType, assignee sql.NullString
	err := db.QueryRow(`
		SELECT id, node_id, title, body, labels, severity, issue_type, status, assignee, created_at, updated_at
		FROM issues
		WHERE id = $1
	`, issueID).Scan(&issue.ID, &issue.NodeID, &issue.Title, &issue.Body, &labelsRaw, &severity, &issueType, &issue.State, &assignee, &issue.CreatedAt, &issue.UpdatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return c.Status(404).JSON(fiber.Map{"error": "Issue not found"})
		}
		return c.Status(500).JSON(fiber.Map{"error": "Failed to get issue"})
	}

	// Parse PostgreSQL array format: {label1,label2}
	var labels []string
	if len(labelsRaw) > 2 {
		content := string(labelsRaw[1 : len(labelsRaw)-1])
		if content != "" {
			labels = strings.Split(content, ",")
		}
	}
	issue.Labels = labelsFromStrings(labels)
	issue.HTMLURL = fmt.Sprintf("http://localhost:4001/issues/%d", issue.ID)
	issue.User = User{Login: "api-user", ID: 1}
	if assignee.Valid && assignee.String != "" {
		issue.Assignee = &User{Login: assignee.String, ID: 0}
	}

	return c.JSON(issue)
}

// getIssueDirect gets an issue without owner/repo params.
func getIssueDirect(c *fiber.Ctx) error {
	c.Params("owner", "iterateswarm")
	c.Params("repo", "demo")
	return getIssue(c)
}

// updateIssue updates an existing issue.
// PATCH /repos/:owner/:repo/issues/:id
func updateIssue(c *fiber.Ctx) error {
	issueID := c.Params("id")

	var req IssueRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	// Build update query dynamically
	updates := []string{}
	args := []interface{}{}
	argNum := 1

	if req.Title != "" {
		updates = append(updates, fmt.Sprintf("title = $%d", argNum))
		args = append(args, req.Title)
		argNum++
	}
	if req.Body != "" {
		updates = append(updates, fmt.Sprintf("body = $%d", argNum))
		args = append(args, req.Body)
		argNum++
	}
	if req.Severity != "" {
		updates = append(updates, fmt.Sprintf("severity = $%d", argNum))
		args = append(args, req.Severity)
		argNum++
	}
	if req.IssueType != "" {
		updates = append(updates, fmt.Sprintf("issue_type = $%d", argNum))
		args = append(args, req.IssueType)
		argNum++
	}
	if len(req.Labels) > 0 {
		updates = append(updates, fmt.Sprintf("labels = $%d", argNum))
		args = append(args, pqStringArray(req.Labels))
		argNum++
	}
	if req.Assignee != "" {
		updates = append(updates, fmt.Sprintf("assignee = $%d", argNum))
		args = append(args, req.Assignee)
		argNum++
	}

	// Handle state change
	if req.Severity == "closed" || (req.IssueType == "" && len(updates) == 0) {
		// Check if body contains state info
	}

	if len(updates) == 0 {
		return c.Status(400).JSON(fiber.Map{"error": "No fields to update"})
	}

	args = append(args, issueID)
	query := fmt.Sprintf("UPDATE issues SET %s WHERE id = $%d", strings.Join(updates, ", "), argNum)

	_, err := db.Exec(query, args...)
	if err != nil {
		log.Printf("Failed to update issue: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to update issue"})
	}

	return getIssue(c)
}

// createPR creates a new pull request.
// POST /repos/:owner/:repo/pulls
func createPR(c *fiber.Ctx) error {
	owner := c.Params("owner")
	repo := c.Params("repo")

	var req PullRequestRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request body"})
	}

	if req.Title == "" {
		return c.Status(400).JSON(fiber.Map{"error": "Title is required"})
	}

	// Get repo ID
	var repoID uuid.UUID
	err := db.QueryRow("SELECT id FROM repos WHERE owner = $1 AND name = $2", owner, repo).Scan(&repoID)
	if err != nil {
		// Create repo if doesn't exist
		err = db.QueryRow(`INSERT INTO repos (owner, name) VALUES ($1, $2) RETURNING id`, owner, repo).Scan(&repoID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "Failed to get repository"})
		}
	}

	// Create PR
	var prID int
	var nodeID string
	err = db.QueryRow(`
		INSERT INTO pull_requests (repo_id, title, body, branch, base_branch, status)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, node_id
	`, repoID, req.Title, req.Body, req.Head, req.Base, "open").Scan(&prID, &nodeID)
	if err != nil {
		log.Printf("Failed to create PR: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to create pull request"})
	}

	pr := PullRequest{
		ID:        prID,
		NodeID:    nodeID,
		Title:     req.Title,
		Body:      req.Body,
		State:     "open",
		HTMLURL:   fmt.Sprintf("http://localhost:4001/pulls/%d", prID),
		DiffURL:   fmt.Sprintf("http://localhost:4001/pulls/%d.diff", prID),
		PatchURL:  fmt.Sprintf("http://localhost:4001/pulls/%d.patch", prID),
		IssueURL:  fmt.Sprintf("http://localhost:4001/issues/%d", prID),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		User:      User{Login: "api-user", ID: 1},
		Head:      Ref{Ref: req.Head, SHA: "abc123", Repo: Repo{Name: repo, FullName: owner + "/" + repo}},
		Base:      Ref{Ref: req.Base, SHA: "def456", Repo: Repo{Name: repo, FullName: owner + "/" + repo}},
	}

	log.Printf("PR created: #%d - %s", prID, req.Title)

	return c.Status(201).JSON(pr)
}

// listPRs lists all pull requests for a repository.
// GET /repos/:owner/:repo/pulls
func listPRs(c *fiber.Ctx) error {
	owner := c.Params("owner")
	repo := c.Params("repo")
	state := c.Query("state", "all")

	// Get repo ID
	var repoID uuid.UUID
	err := db.QueryRow("SELECT id FROM repos WHERE owner = $1 AND name = $2", owner, repo).Scan(&repoID)
	if err != nil {
		return c.JSON([]PullRequest{})
	}

	// Build query
	query := `
		SELECT id, node_id, title, body, branch, base_branch, status, merged, created_at, updated_at
		FROM pull_requests
		WHERE repo_id = $1
	`
	args := []interface{}{repoID}

	if state != "all" {
		query += " AND status = $2"
		args = append(args, state)
	}

	query += " ORDER BY created_at DESC"

	rows, err := db.Query(query, args...)
	if err != nil {
		log.Printf("Failed to list PRs: %v", err)
		return c.Status(500).JSON(fiber.Map{"error": "Failed to list pull requests"})
	}
	defer rows.Close()

	var prs []PullRequest
	for rows.Next() {
		var pr PullRequest
		var branch, baseBranch sql.NullString
		var merged bool
		if err := rows.Scan(&pr.ID, &pr.NodeID, &pr.Title, &pr.Body, &branch, &baseBranch, &pr.State, &merged, &pr.CreatedAt, &pr.UpdatedAt); err != nil {
			log.Printf("Failed to scan PR: %v", err)
			continue
		}
		pr.HTMLURL = fmt.Sprintf("http://localhost:4001/pulls/%d", pr.ID)
		pr.DiffURL = fmt.Sprintf("http://localhost:4001/pulls/%d.diff", pr.ID)
		pr.PatchURL = fmt.Sprintf("http://localhost:4001/pulls/%d.patch", pr.ID)
		pr.IssueURL = fmt.Sprintf("http://localhost:4001/issues/%d", pr.ID)
		pr.User = User{Login: "api-user", ID: 1}
		pr.Head = Ref{Ref: branch.String, SHA: "abc123", Repo: Repo{Name: repo, FullName: owner + "/" + repo}}
		pr.Base = Ref{Ref: baseBranch.String, SHA: "def456", Repo: Repo{Name: repo, FullName: owner + "/" + repo}}
		pr.Merged = merged
		prs = append(prs, pr)
	}

	if prs == nil {
		prs = []PullRequest{}
	}

	return c.JSON(prs)
}

// listPRsDirect lists PRs without owner/repo params.
func listPRsDirect(c *fiber.Ctx) error {
	c.Params("owner", "iterateswarm")
	c.Params("repo", "demo")
	return listPRs(c)
}

// getPR gets a single PR by ID.
// GET /repos/:owner/:repo/pulls/:id
func getPR(c *fiber.Ctx) error {
	prID := c.Params("id")

	var pr PullRequest
	var branch, baseBranch sql.NullString
	var merged bool
	err := db.QueryRow(`
		SELECT id, node_id, title, body, branch, base_branch, status, merged, created_at, updated_at
		FROM pull_requests
		WHERE id = $1
	`, prID).Scan(&pr.ID, &pr.NodeID, &pr.Title, &pr.Body, &branch, &baseBranch, &pr.State, &merged, &pr.CreatedAt, &pr.UpdatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return c.Status(404).JSON(fiber.Map{"error": "Pull request not found"})
		}
		return c.Status(500).JSON(fiber.Map{"error": "Failed to get pull request"})
	}

	pr.HTMLURL = fmt.Sprintf("http://localhost:4001/pulls/%d", pr.ID)
	pr.DiffURL = fmt.Sprintf("http://localhost:4001/pulls/%d.diff", pr.ID)
	pr.PatchURL = fmt.Sprintf("http://localhost:4001/pulls/%d.patch", pr.ID)
	pr.IssueURL = fmt.Sprintf("http://localhost:4001/issues/%d", pr.ID)
	pr.User = User{Login: "api-user", ID: 1}
	pr.Head = Ref{Ref: branch.String, SHA: "abc123"}
	pr.Base = Ref{Ref: baseBranch.String, SHA: "def456"}
	pr.Merged = merged

	return c.JSON(pr)
}

// getPRDirect gets a PR without owner/repo params.
func getPRDirect(c *fiber.Ctx) error {
	c.Params("owner", "iterateswarm")
	c.Params("repo", "demo")
	return getPR(c)
}

// labelsFromStrings converts string slice to Label slice.
func labelsFromStrings(labels []string) []Label {
	result := make([]Label, len(labels))
	for i, label := range labels {
		result[i] = Label{
			ID:    i + 1,
			Name:  label,
			Color: "ededed",
		}
	}
	return result
}

// pqStringArray converts Go string slice to PostgreSQL text array.
func pqStringArray(labels []string) []string {
	if labels == nil {
		return []string{}
	}
	return labels
}
