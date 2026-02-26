package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/redis/go-redis/v9"

	"iterateswarm-core/internal/api"
	"iterateswarm-core/internal/auth"
	"iterateswarm-core/internal/debug"
	"iterateswarm-core/internal/redpanda"
	"iterateswarm-core/internal/temporal"
	"iterateswarm-core/internal/web"
)

func main() {
	// Command line flags
	redpandaBrokers := flag.String("redpanda", "localhost:9094", "Redpanda brokers")
	temporalAddr := flag.String("temporal", "localhost:7233", "Temporal address")
	namespace := flag.String("namespace", "default", "Temporal namespace")
	port := flag.String("port", "3000", "HTTP server port")
	topic := flag.String("topic", "feedback-events", "Kafka topic")

	flag.Parse()

	log.Println("Starting IterateSwarm Core Server...")

	// Initialize Redpanda client
	redpandaClient, err := redpanda.NewClient([]string{*redpandaBrokers}, *topic)
	if err != nil {
		log.Fatalf("Failed to connect to Redpanda: %v", err)
	}
	defer redpandaClient.Close()
	log.Println("Connected to Redpanda")

	// Initialize Temporal client
	temporalClient, err := temporal.NewClient(*temporalAddr, *namespace)
	if err != nil {
		log.Fatalf("Failed to connect to Temporal: %v", err)
	}
	defer temporalClient.Close()
	log.Println("Connected to Temporal")

	// Initialize Redis client
	redisClient := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})
	if _, err := redisClient.Ping(context.Background()).Result(); err != nil {
		log.Printf("Warning: Redis not available: %v", err)
	} else {
		log.Println("Connected to Redis")
	}
	defer redisClient.Close()

	// Create handler
	handler := api.NewHandler(redpandaClient, temporalClient, nil, redisClient)

	// Initialize Clerk auth
	clerkConfig := auth.LoadClerkConfig()
	clerkAuth := auth.NewClerkAuth(clerkConfig)
	if clerkConfig.ClerkInstanceID != "" {
		log.Println("Clerk auth initialized (instance: " + clerkConfig.ClerkInstanceID + ")")
	} else {
		log.Println("Clerk auth not configured (set CLERK_INSTANCE_ID to enable)")
	}

	// Create Fiber app
	app := fiber.New(fiber.Config{
		AppName:      "IterateSwarm Core",
		ErrorHandler: errorHandler,
	})

	// Middleware
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} - ${method} ${path} (${latency})\n",
	}))
	app.Use(cors.New())

	// Health check routes (no auth required)
	app.Get("/health", handler.HandleHealth)
	app.Get("/health/details", handler.HandleDetailedHealth)

	// Webhook routes (no auth required - they use Discord verification)
	app.Post("/webhooks/discord", handler.HandleDiscordWebhook)
	app.Post("/webhooks/interaction", handler.HandleInteraction)

	// Test route (no auth)
	app.Get("/test/kafka", handler.HandleKafkaTest)

	// Protected routes - require Clerk auth
	protected := app.Group("/api")
	if clerkConfig.ClerkInstanceID != "" {
		protected.Use(clerkAuth.Middleware())
	}

	// Protected API endpoints
	protected.Get("/me", func(ctx *fiber.Ctx) error {
		return ctx.JSON(map[string]interface{}{
			"user_id": auth.GetUserID(ctx),
			"email":   auth.GetUserEmail(ctx),
			"role":    auth.GetUserRole(ctx),
		})
	})

	// Debug routes (LiteDebug Console)
	debugHandler := debug.NewHandler(redpandaClient, temporalClient, "http://localhost:16686")
	debugHandler.RegisterRoutes(app)

	// Web routes (HTMX Admin Dashboard)
	webHandler := web.NewHandler(redisClient)
	webHandler.RegisterRoutes(app)

	// SSE routes (Server-Sent Events for Live Feed)
	sseHandler := web.NewSSEHandler(redisClient)
	app.Get("/api/stream/events", sseHandler.HandleSSE)

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-quit
		log.Println("Shutting down server...")
		if err := app.Shutdown(); err != nil {
			log.Printf("Error during shutdown: %v", err)
		}
	}()

	// Start server
	addr := ":" + *port
	log.Printf("Server listening on %s", addr)
	if err := app.Listen(addr); err != nil {
		log.Printf("Server error: %v", err)
	}
}

func errorHandler(c *fiber.Ctx, err error) error {
	log.Printf("Error: %v", err)
	code := fiber.StatusInternalServerError
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}
	return c.Status(code).JSON(map[string]string{
		"error": err.Error(),
	})
}
