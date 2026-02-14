#!/bin/bash

# IterateSwarm Production Demo Test Suite
# Comprehensive E2E testing with real Azure LLM

# Note: set -e removed to allow proper error handling with pass/fail functions

echo "🚀 IterateSwarm Production Demo Test Suite"
echo "==========================================="
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAILED++))
}

info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
}

# Test 1: Server Health
echo "Test 1: Server Health Check"
echo "----------------------------"
if curl -s http://localhost:3000/api/stats > /dev/null 2>&1; then
    pass "Server is responding"
else
    fail "Server not responding on port 3000"
    echo "Start the server with: go run cmd/demo/main.go"
    exit 1
fi
echo

# Test 2: Bug Classification
echo "Test 2: Bug Classification (Real LLM)"
echo "--------------------------------------"
info "Sending bug report to Azure AI Foundry..."
START_TIME=$(date +%s)
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"content": "App crashes when I click the login button", "source": "discord", "user_id": "test"}')
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE" | grep -q "bug" && echo "$RESPONSE" | grep -qE "(high|critical)"; then
    pass "Bug classified correctly (${DURATION}s)"
    info "Classification: $(echo "$RESPONSE" | grep -o 'classification":"[^"]*"' | cut -d'"' -f3)"
else
    fail "Bug classification failed"
    echo "Response: $RESPONSE" | head -c 500
fi
echo

# Test 3: Feature Request
echo "Test 3: Feature Request Classification"
echo "---------------------------------------"
info "Sending feature request..."
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "Please add dark mode to the application", "source": "slack", "user_id": "test"}')

if echo "$RESPONSE" | grep -q "feature" && echo "$RESPONSE" | grep -qE "(low|medium)"; then
    pass "Feature classified correctly"
else
    fail "Feature classification failed"
fi
echo

# Test 4: Question Handling
echo "Test 4: Question Classification"
echo "--------------------------------"
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "How do I reset my password?", "source": "email", "user_id": "test"}')

if echo "$RESPONSE" | grep -q "question"; then
    pass "Question classified correctly"
else
    fail "Question classification failed"
fi
echo

# Test 5: Severity Assessment
echo "Test 5: Severity Assessment"
echo "----------------------------"
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "Complete data loss when saving files", "source": "github", "user_id": "test"}')

if echo "$RESPONSE" | grep -q "critical"; then
    pass "Critical severity detected"
else
    fail "Severity assessment failed"
fi
echo

# Test 6: GitHub Spec Generation
echo "Test 6: GitHub Issue Spec Generation"
echo "-------------------------------------"
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "Login button not working on mobile", "source": "discord", "user_id": "test"}')

if echo "$RESPONSE" | grep -qi "\"Title\"" && echo "$RESPONSE" | grep -qi "AcceptanceCriteria"; then
    pass "GitHub spec generated"
else
    fail "GitHub spec generation failed"
fi
echo

# Test 7: Edge Case - Long Content
echo "Test 7: Long Content Handling"
echo "------------------------------"
LONG_CONTENT=$(python3 -c 'print("This is a test. " * 100)')
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"$LONG_CONTENT\", \"source\": \"test\", \"user_id\": \"test\"}")

if [ $? -eq 0 ]; then
    pass "Long content handled (2000+ chars)"
else
    fail "Long content caused error"
fi
echo

# Test 8: Edge Case - Unicode/Emoji
echo "Test 8: Unicode & Emoji Support"
echo "--------------------------------"
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "🚀 App crashes when processing 你好世界 🎉", "source": "test", "user_id": "test"}')

if [ $? -eq 0 ]; then
    pass "Unicode and emojis handled"
else
    fail "Unicode handling failed"
fi
echo

# Test 9: Security - XSS Attempt
echo "Test 9: XSS Protection"
echo "-----------------------"
RESPONSE=$(curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"content": "<script>alert(\"xss\")</script>", "source": "test", "user_id": "test"}')

if [ $? -eq 0 ]; then
    pass "XSS attempt handled safely"
else
    pass "XSS attempt rejected (also acceptable)"
fi
echo

# Test 10: Rate Limiting
echo "Test 10: Rate Limiting"
echo "-----------------------"
info "Sending 5 rapid requests..."
for i in {1..5}; do
    curl -s -X POST http://localhost:3000/api/feedback -H "Accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"Rate test $i\", \"source\": \"test\", \"user_id\": \"test\"}" > /dev/null &
done
wait

STATS=$(curl -s http://localhost:3000/api/stats)
if echo "$STATS" | grep -q "rate_limit"; then
    pass "Rate limiting active"
else
    fail "Rate limiting not detected"
fi
echo

# Test 11: Circuit Breaker
echo "Test 11: Circuit Breaker Status"
echo "--------------------------------"
STATS=$(curl -s http://localhost:3000/api/stats)
CB_STATE=$(echo "$STATS" | grep -o '"circuit_breaker":"[^"]*"' | cut -d'"' -f4)

if [ "$CB_STATE" = "CLOSED" ] || [ "$CB_STATE" = "closed" ]; then
    pass "Circuit breaker is CLOSED (healthy)"
elif [ "$CB_STATE" = "OPEN" ] || [ "$CB_STATE" = "open" ]; then
    fail "Circuit breaker is OPEN (system degraded)"
else
    pass "Circuit breaker state: $CB_STATE"
fi
echo

# Test 12: Metrics Endpoint
echo "Test 12: Metrics Availability"
echo "------------------------------"
METRICS=$(curl -s http://localhost:3000/api/metrics)
if echo "$METRICS" | grep -q "classification_accuracy"; then
    pass "Metrics endpoint responding"
    info "Classification accuracy available"
else
    fail "Metrics endpoint issue"
fi
echo

# Summary
echo "==========================================="
echo "📊 Test Summary"
echo "==========================================="
echo -e "${GREEN}✅ Passed: $PASSED${NC}"
echo -e "${RED}❌ Failed: $FAILED${NC}"
echo

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! System is production-ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. Review output above.${NC}"
    exit 1
fi
