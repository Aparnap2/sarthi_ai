package grpc_test

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"iterateswarm-core/internal/grpc"
)

const pythonGRPCAddr = "localhost:50051"

// skipIfGRPCDown skips if Python gRPC server isn't running.
// Start it first: cd apps/ai && uv run python -m src.grpc_server
func skipIfGRPCDown(t *testing.T) {
	t.Helper()
	c, err := grpc.NewClient(pythonGRPCAddr)
	if err != nil {
		t.Skipf("Python gRPC server not available at %s: %v", pythonGRPCAddr, err)
		return
	}
	defer c.Close()
	// Quick probe
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	_, err = c.AnalyzeFeedback(ctx, "ping", "test", "healthcheck")
	if err != nil {
		st, _ := status.FromError(err)
		// InvalidArgument means server IS up but rejected input — still "up"
		if st.Code() != codes.InvalidArgument && st.Code() != codes.OK {
			t.Skipf("gRPC server up but returned: %v", err)
		}
	}
}

// ─── TEST 1: Happy Path ────────────────────────────────────────────────────────

func TestGRPCClient_HappyPath(t *testing.T) {
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	resp, err := c.AnalyzeFeedback(ctx,
		"App crashes when clicking the login button",
		"discord",
		"test-user-happy")

	require.NoError(t, err)
	require.NotNil(t, resp)
	assert.NotNil(t, resp.Spec)
	assert.NotEmpty(t, resp.Spec.Title, "title must not be empty for a real bug report")
	assert.NotEmpty(t, resp.Reasoning, "reasoning must not be empty")
}

// ─── TEST 2: Server Unavailable ───────────────────────────────────────────────

func TestGRPCClient_ServerUnavailable(t *testing.T) {
	// No skip — this test must work even without a running gRPC server
	c, err := grpc.NewClient("localhost:50099") // nothing here
	require.NoError(t, err)                     // gRPC connection is lazy — no error at dial
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = c.AnalyzeFeedback(ctx, "test feedback", "discord", "test-user")
	assert.Error(t, err, "must return error for unreachable server")
	// Must NOT hang — returns before 5s deadline
}

// ─── TEST 3: Deadline Exceeded ────────────────────────────────────────────────

func TestGRPCClient_DeadlineExceeded(t *testing.T) {
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	// Pre-expire the context
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()
	time.Sleep(5 * time.Millisecond) // ensure already expired

	_, err = c.AnalyzeFeedback(ctx, "deadline test", "discord", "test-user")
	require.Error(t, err)

	st, ok := status.FromError(err)
	if ok {
		// Accept either DeadlineExceeded or Canceled — both valid for expired context
		assert.True(t,
			st.Code() == codes.DeadlineExceeded || st.Code() == codes.Canceled,
			"must return DeadlineExceeded or Canceled, got: %v", st.Code())
	}
}

// ─── TEST 4: Empty Text → InvalidArgument ─────────────────────────────────────

func TestGRPCClient_EmptyText(t *testing.T) {
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err = c.AnalyzeFeedback(ctx, "", "discord", "test-user")
	require.Error(t, err, "empty text must be rejected")

	st, ok := status.FromError(err)
	if ok {
		assert.Equal(t, codes.InvalidArgument, st.Code(),
			"empty text must return InvalidArgument, got: %v", st.Code())
	}
}

// ─── TEST 5: 50 Concurrent Requests — Race-Safe ───────────────────────────────

func TestGRPCClient_Concurrent50Requests(t *testing.T) {
	// go test -race -run TestGRPCClient_Concurrent50Requests
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	var (
		wg      sync.WaitGroup
		mu      sync.Mutex
		errs    []string
		success int32
	)

	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
			defer cancel()

			_, err := c.AnalyzeFeedback(ctx,
				fmt.Sprintf("Concurrent test feedback item number %d in parallel", idx),
				"test",
				fmt.Sprintf("concurrent-user-%d", idx))

			if err != nil {
				mu.Lock()
				errs = append(errs, fmt.Sprintf("goroutine %d: %v", idx, err))
				mu.Unlock()
			} else {
				atomic.AddInt32(&success, 1)
			}
		}(i)
	}

	wg.Wait()

	// Allow up to 5% failure rate for rate-limiting / Azure throttling
	assert.GreaterOrEqual(t, int(atomic.LoadInt32(&success)), 45,
		"at least 45/50 concurrent requests must succeed. Failures: %v", errs)
}

// ─── TEST 6: Unicode + Emoji — No Panic ───────────────────────────────────────

func TestGRPCClient_UnicodeAndEmoji(t *testing.T) {
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	unicodeText := "App crashes 🔥 when typing こんにちは in the 搜索 field — très frustrant! 한국어 test"

	resp, err := c.AnalyzeFeedback(ctx, unicodeText, "discord", "unicode-test-user")
	require.NoError(t, err, "unicode + emoji must not panic or fail with encoding error")
	require.NotNil(t, resp)
}

// ─── TEST 7: Large Payload (8000 chars) ───────────────────────────────────────

func TestGRPCClient_LargePayload(t *testing.T) {
	skipIfGRPCDown(t)

	c, err := grpc.NewClient(pythonGRPCAddr)
	require.NoError(t, err)
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	// Realistic large feedback: 8000 chars, well within gRPC default 4MB limit
	largeText := "User reports critical issue: app crashes on login. " +
		strings.Repeat("Additional context and reproduction steps. Stack trace: ERROR at line 42. ", 100)

	assert.LessOrEqual(t, len(largeText), 8500, "sanity check: test input is ~8000 chars")

	resp, err := c.AnalyzeFeedback(ctx, largeText, "discord", "large-payload-user")
	require.NoError(t, err, "8000-char payload must be handled correctly")
	require.NotNil(t, resp)
	assert.NotEmpty(t, resp.Spec.Title, "large payload must still produce a title")
}
