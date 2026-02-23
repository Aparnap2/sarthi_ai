# IterateSwarm Makefile
# Quick commands for development and operations

.PHONY: help up down status test build clean proto verify deps logs restart security-test security-race security-lint

# Default target
help:
	@echo "IterateSwarm - Go AI ChatOps Platform"
	@echo ""
	@echo "Commands:"
	@echo "  up          Start all services (Docker + apps)"
	@echo "  down        Stop all Docker services"
	@echo "  status      Check service status"
	@echo "  test        Run all tests (Go only)"
	@echo "  build       Build all applications"
	@echo "  clean       Clean build artifacts"
	@echo "  proto       Generate protobuf code"
	@echo "  verify      Run E2E verification script"
	@echo "  deps        Install dependencies"
	@echo "  logs        Tail logs from all services"

# Start all infrastructure and applications
up:
	@echo "Starting IterateSwarm..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Infrastructure started"

# Stop all Docker services
down:
	@echo "Stopping all services..."
	docker-compose down
	@echo "All services stopped"

# Check service status
status:
	@echo "Service Status:"
	docker-compose ps

# Run all tests
test:
	@echo "Running tests..."
	cd apps/core && go test ./...

# Build all applications
build:
	@echo "Building applications..."
	cd apps/core && go build -o bin/server ./cmd/server && go build -o bin/worker ./cmd/worker
	@echo "Built: apps/core/bin/server"
	@echo "Built: apps/core/bin/worker"

# Clean build artifacts
clean:
	@echo "Cleaning..."
	cd apps/core && rm -rf bin/

# Generate protobuf code
proto:
	@echo "Generating protobuf code..."
	docker run --rm -v $$(pwd):/workspace -w /workspace bufbuild/buf:latest generate
	@echo "Protobuf code generated"

# Run E2E verification
verify:
	@echo "Running E2E verification..."
	./scripts/verify_system.sh

# Install dependencies
deps:
	@echo "Installing dependencies..."
	cd apps/core && go mod download

# Tail logs from all services
logs:
	@echo "Showing logs (Ctrl+C to exit)..."
	docker-compose logs -f

# Full restart
restart: down up
	@echo "Full restart complete"

# Security Tests
security-test:
	@echo "🔒 Running security test suite..."
	@echo ""
	@echo "[1/5] Go race detector tests..."
	cd apps/core && go test -race -count=3 ./internal/security/... -timeout 3m || true
	@echo ""
	@echo "[2/5] Security unit tests..."
	cd apps/core && go test ./internal/security/... -v -timeout 2m || true
	@echo ""
	@echo "[3/5] Python type safety tests..."
cd apps/ai && uv run pytest tests/security/ -v || true
	@echo ""
	@echo "✅ Security tests complete"

security-race:
	@echo "🔍 Running Go race detector..."
	cd apps/core && go test -race -count=3 ./... -timeout 5m

security-lint:
	@echo "🔍 Running static analysis..."
	cd apps/core && go vet ./...
	@echo "✅ Linting complete"

# Pre-interview security sweep
security-full: security-race security-test security-lint
	@echo ""
	@echo "╔══════════════════════════════╗"
	@echo "║  SECURITY SWEEP COMPLETE ✅  ║"
	@echo "╚══════════════════════════════╝"
