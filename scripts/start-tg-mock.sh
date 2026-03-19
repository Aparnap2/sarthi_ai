#!/usr/bin/env bash
# Start tg-mock for Telegram Bot API mocking
# Usage: bash scripts/start-tg-mock.sh
# Stop:  bash scripts/stop-tg-mock.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

stop_existing() {
    if docker ps -q --filter name=sarthi-tg-mock | grep -q .; then
        echo "Stopping existing tg-mock container..."
        docker stop sarthi-tg-mock >/dev/null 2>&1
        docker rm sarthi-tg-mock >/dev/null 2>&1
    fi
}

start_mock() {
    echo "Starting tg-mock..."
    
    docker run -d \
      --name sarthi-tg-mock \
      -p 8081:8081 \
      -v "${PROJECT_ROOT}/config/tg-mock.yaml:/config.yaml:ro" \
      -v tg-mock-storage:/tmp/tg-mock-files \
      ghcr.io/watzon/tg-mock:latest \
      --config /config.yaml \
      --verbose
    
    echo "Waiting for tg-mock to start..."
    sleep 5
    
    # Register scenarios via control API
    echo "Registering test scenarios..."
    
    # Rate limit scenario (429) - unlimited times
    curl -sf -X POST http://localhost:8081/__control/scenarios \
      -H "Content-Type: application/json" \
      -d '{
        "method": "sendMessage",
        "match": {"chat_id": 999},
        "times": -1,
        "response": {
          "error_code": 429,
          "description": "Too Many Requests: retry after 30",
          "retry_after": 30
        }
      }' >/dev/null 2>&1 || true
    
    # Chat not found scenario (400) - unlimited times
    curl -sf -X POST http://localhost:8081/__control/scenarios \
      -H "Content-Type: application/json" \
      -d '{
        "method": "sendMessage",
        "match": {"chat_id": 888},
        "times": -1,
        "response": {
          "error_code": 400,
          "description": "Bad Request: chat not found"
        }
      }' >/dev/null 2>&1 || true
    
    # Health check
    if curl -sf "http://localhost:8081/bot987654321:ZYX-cba/getMe" >/dev/null 2>&1; then
        echo "✅ tg-mock started successfully on port 8081"
        echo ""
        echo "Test it:"
        echo "  curl -sf http://localhost:8081/bot987654321:ZYX-cba/getMe | python3 -m json.tool"
        echo ""
        echo "Environment variables for tests:"
        echo "  export TELEGRAM_API_BASE=http://localhost:8081"
        echo "  export TELEGRAM_BOT_TOKEN=987654321:ZYX-cba"
        echo "  export TELEGRAM_TEST_CHAT_ID=111222333"
    else
        echo "❌ tg-mock failed to start. Check logs:"
        docker logs sarthi-tg-mock
        exit 1
    fi
}

stop_existing
start_mock
