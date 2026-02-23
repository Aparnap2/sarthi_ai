#!/bin/bash

# Live Demo Script for IterateSwarm
# Shows real-time AI processing with visual feedback

set -e

echo "🎬 IterateSwarm Live Demo"
echo "=========================="
echo ""

API_URL="http://localhost:3000"

echo "✅ Checking server health..."
if ! curl -s ${API_URL}/api/health > /dev/null; then
    echo "❌ Server not running. Start it first with:"
    echo "   go run cmd/demo/main.go"
    exit 1
fi
echo "✅ Server is healthy"
echo ""

# Demo 1: Bug Report
echo "🐛 DEMO 1: Bug Report"
echo "---------------------"
echo "Input: 'App crashes when I click login button'"
echo "Processing with Azure AI Foundry..."
echo ""

START_TIME=$(date +%s)
curl -s -X POST ${API_URL}/api/feedback \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "content": "App crashes when I click the login button on mobile",
    "source": "github",
    "user_id": "demo-bug"
  }' | python3 -m json.tool 2>/dev/null | head -20
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "✅ Processing complete in ${DURATION}s"
echo ""

# Demo 2: Feature Request
echo "💡 DEMO 2: Feature Request"
echo "--------------------------"
echo "Input: 'Please add dark mode to settings'"
echo "Processing with Azure AI Foundry..."
echo ""

START_TIME=$(date +%s)
curl -s -X POST ${API_URL}/api/feedback \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "content": "Please add a dark mode toggle to the settings",
    "source": "slack",
    "user_id": "demo-feature"
  }' | python3 -m json.tool 2>/dev/null | head -20
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "✅ Processing complete in ${DURATION}s"
echo ""

# Demo 3: Question
echo "❓ DEMO 3: Question"
echo "-------------------"
echo "Input: 'How do I reset my password?'"
echo "Processing with Azure AI Foundry..."
echo ""

START_TIME=$(date +%s)
curl -s -X POST ${API_URL}/api/feedback \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "content": "How do I reset my password?",
    "source": "discord",
    "user_id": "demo-question"
  }' | python3 -m json.tool 2>/dev/null | head -20
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "✅ Processing complete in ${DURATION}s"
echo ""

# Show system stats
echo "📊 System Stats"
echo "---------------"
curl -s ${API_URL}/api/stats | python3 -m json.tool 2>/dev/null || curl -s ${API_URL}/api/stats
echo ""

echo "🎉 Demo complete!"
echo ""
echo "Open http://localhost:3000 in your browser to see the dashboard"
echo "Or visit ${API_URL}/api/stats for real-time metrics"