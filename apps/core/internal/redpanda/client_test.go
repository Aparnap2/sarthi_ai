package redpanda_test

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"iterateswarm-core/internal/redpanda"
)

// ─── Helpers ─────────────────────────────────────────────────────────────────

func uniqueTopic(t *testing.T) string {
	t.Helper()
	return fmt.Sprintf("test-%s", uuid.New().String()[:8])
}

func skipIfRedpandaDown(t *testing.T) {
	t.Helper()
	c := redpanda.NewClient([]string{"localhost:9094"}, "health-check")
	if c == nil {
		t.Skip("Redpanda client creation failed")
		return
	}
	defer c.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := c.Ping(ctx); err != nil {
		t.Skipf("Redpanda not available: %v", err)
	}
}

// ─── TEST 1: Happy Path ───────────────────────────────────────────────────────

func TestRedpandaPublish_HappyPath(t *testing.T) {
	skipIfRedpandaDown(t)
	topic := uniqueTopic(t)
	c := redpanda.NewClient([]string{"localhost:9094"}, topic)
	require.NotNil(t, c)
	defer c.Close()

	msg := []byte(fmt.Sprintf(`{"task_id":"%s","text":"DB pool exhausted"}`, uuid.New()))
	err := c.Publish(context.Background(), msg)
	require.NoError(t, err)

	received := make(chan []byte, 1)
	go func() {
		consumer := redpanda.NewConsumer([]string{"localhost:9094"}, topic, uuid.New().String())
		defer consumer.Close()
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		_ = consumer.Consume(ctx, func(m []byte) error {
			received <- m
			return nil
		})
	}()

	select {
	case got := <-received:
		assert.JSONEq(t, string(msg), string(got))
	case <-time.After(15 * time.Second):
		t.Fatal("message not received within 15s — Redpanda may be slow to start")
	}
}

// ─── TEST 2: Connection Refused ───────────────────────────────────────────────

func TestRedpandaPublish_ConnectionRefused(t *testing.T) {
	c := redpanda.NewClient([]string{"localhost:19999"}, "test-topic")
	require.NotNil(t, c)
	defer c.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	err := c.Publish(ctx, []byte(`{"test":true}`))
	assert.Error(t, err, "must return error for unreachable broker")
	// Must return within ctx timeout, not hang forever
}

// ─── TEST 3: Message Too Large (12MB > Redpanda's 10MB default) ──────────────

func TestRedpandaPublish_MessageTooLarge(t *testing.T) {
	skipIfRedpandaDown(t)
	c := redpanda.NewClient([]string{"localhost:9094"}, uniqueTopic(t))
	require.NotNil(t, c)
	defer c.Close()

	hugeMsg := []byte(strings.Repeat("x", 12*1024*1024)) // 12MB

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	err := c.Publish(ctx, hugeMsg)
	assert.Error(t, err, "12MB message must be rejected — not panic, not hang")
}

// ─── TEST 4: At-Least-Once Delivery ──────────────────────────────────────────

func TestRedpandaConsume_AtLeastOnceDelivery(t *testing.T) {
	skipIfRedpandaDown(t)
	topic := uniqueTopic(t)
	groupID := "alod-group-" + uuid.New().String()[:6]
	c := redpanda.NewClient([]string{"localhost:9094"}, topic)
	require.NotNil(t, c)
	defer c.Close()

	// Produce 10 messages
	for i := 0; i < 10; i++ {
		require.NoError(t, c.Publish(context.Background(),
			[]byte(fmt.Sprintf(`{"seq":%d}`, i))))
	}
	time.Sleep(500 * time.Millisecond) // let Redpanda commit

	// Consumer 1: consume 5 then cancel WITHOUT committing offsets
	var consumed1 int32
	ctx1, cancel1 := context.WithCancel(context.Background())
	cons1 := redpanda.NewConsumer([]string{"localhost:9094"}, topic, groupID)
	go func() {
		_ = cons1.Consume(ctx1, func(m []byte) error {
			if atomic.AddInt32(&consumed1, 1) >= 5 {
				cancel1() // cancel without committing
			}
			return nil
		})
	}()
	time.Sleep(5 * time.Second)
	cons1.Close()

	// Consumer 2: same group — must re-deliver at least the uncommitted messages
	var redelivered int32
	ctx2, cancel2 := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel2()
	cons2 := redpanda.NewConsumer([]string{"localhost:9094"}, topic, groupID)
	defer cons2.Close()
	_ = cons2.Consume(ctx2, func(_ []byte) error {
		atomic.AddInt32(&redelivered, 1)
		return nil
	})

	assert.GreaterOrEqual(t, atomic.LoadInt32(&redelivered), int32(1),
		"at-least-once: some messages must be re-delivered after uncommitted consumer")
}

// ─── TEST 5: Idempotency Key Deduplication ───────────────────────────────────

func TestRedpandaConsume_DuplicateIdempotency(t *testing.T) {
	skipIfRedpandaDown(t)
	topic := uniqueTopic(t)
	idemKey := "idem-" + uuid.New().String()

	c := redpanda.NewClient([]string{"localhost:9094"}, topic)
	require.NotNil(t, c)
	defer c.Close()

	msg := []byte(fmt.Sprintf(`{"idempotency_key":"%s","text":"hello"}`, idemKey))
	// Produce SAME message twice
	require.NoError(t, c.Publish(context.Background(), msg))
	require.NoError(t, c.Publish(context.Background(), msg))

	rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	defer rdb.Close()

	var processedCount int32
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cons := redpanda.NewConsumer([]string{"localhost:9094"}, topic, uuid.New().String())
	defer cons.Close()
	_ = cons.Consume(ctx, func(m []byte) error {
		var payload map[string]string
		_ = json.Unmarshal(m, &payload)
		key := payload["idempotency_key"]
		if key == "" {
			return nil
		}
		// Redis SETNX — only process if first time seen
		set, _ := rdb.SetNX(ctx, "processed:"+key, "1", 24*time.Hour).Result()
		if set {
			atomic.AddInt32(&processedCount, 1)
		}
		return nil
	})

	time.Sleep(3 * time.Second)
	assert.Equal(t, int32(1), atomic.LoadInt32(&processedCount),
		"same idempotency key must be processed exactly once")

	// Cleanup
	rdb.Del(context.Background(), "processed:"+idemKey)
}

// ─── TEST 6: 10 Concurrent Consumers — No Races ───────────────────────────────

func TestRedpandaConsume_Concurrent10Goroutines(t *testing.T) {
	// go test -race -run TestRedpandaConsume_Concurrent10Goroutines
	skipIfRedpandaDown(t)
	topic := uniqueTopic(t)
	c := redpanda.NewClient([]string{"localhost:9094"}, topic)
	require.NotNil(t, c)
	defer c.Close()

	// Produce 50 messages
	for i := 0; i < 50; i++ {
		require.NoError(t, c.Publish(context.Background(),
			[]byte(fmt.Sprintf(`{"seq":%d}`, i))))
	}

	var (
		wg   sync.WaitGroup
		mu   sync.Mutex
		seen = make(map[int]bool)
	)

	for g := 0; g < 10; g++ {
		wg.Add(1)
		go func(gID int) {
			defer wg.Done()
			ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
			defer cancel()
			cons := redpanda.NewConsumer(
				[]string{"localhost:9094"}, topic,
				fmt.Sprintf("concurrent-group-%d", gID))
			defer cons.Close()
			_ = cons.Consume(ctx, func(m []byte) error {
				var p map[string]int
				_ = json.Unmarshal(m, &p)
				mu.Lock()
				seen[p["seq"]] = true
				mu.Unlock()
				return nil
			})
		}(g)
	}

	wg.Wait()
	mu.Lock()
	defer mu.Unlock()
	assert.GreaterOrEqual(t, len(seen), 40,
		"at least 40/50 messages consumed across 10 goroutines, no data races")
}

// ─── TEST 7: Offset Commit Failure — Messages Not Lost ────────────────────────

func TestRedpandaConsume_OffsetCommitFailure(t *testing.T) {
	skipIfRedpandaDown(t)
	topic := uniqueTopic(t)
	groupID := "offset-fail-" + uuid.New().String()[:6]

	c := redpanda.NewClient([]string{"localhost:9094"}, topic)
	require.NotNil(t, c)
	defer c.Close()
	require.NoError(t, c.Publish(context.Background(),
		[]byte(`{"id":"offset-test"}`)))

	var attempts []string
	var mu sync.Mutex

	// Consumer 1: receives but force-closes WITHOUT committing offset
	ctx1, cancel1 := context.WithCancel(context.Background())
	cons1 := redpanda.NewConsumer([]string{"localhost:9094"}, topic, groupID)
	_ = cons1.Consume(ctx1, func(m []byte) error {
		mu.Lock()
		attempts = append(attempts, "attempt-1")
		mu.Unlock()
		cancel1() // disconnect immediately — offset not committed
		return nil
	})
	cons1.Close()
	time.Sleep(1 * time.Second)

	// Consumer 2: same group ID — must re-receive the message
	ctx2, cancel2 := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel2()
	cons2 := redpanda.NewConsumer([]string{"localhost:9094"}, topic, groupID)
	defer cons2.Close()
	_ = cons2.Consume(ctx2, func(m []byte) error {
		mu.Lock()
		attempts = append(attempts, "attempt-2")
		mu.Unlock()
		return nil
	})

	time.Sleep(5 * time.Second)
	mu.Lock()
	defer mu.Unlock()
	assert.Contains(t, attempts, "attempt-2",
		"message must be reprocessed after offset commit failure (at-least-once guarantee)")
}
