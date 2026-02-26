package api

import (
	"os"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

// RequireAuth is a middleware that validates JWT tokens from cookies.
// CRITICAL: TEST_MODE and DEV_MODE bypass authentication for E2E tests.
func RequireAuth() fiber.Handler {
	secret := []byte(os.Getenv("JWT_SECRET"))
	return func(c *fiber.Ctx) error {
		// CRITICAL: Bypass for E2E tests and development
		// This allows tests to run without real authentication
		if os.Getenv("TEST_MODE") == "true" || os.Getenv("DEV_MODE") == "true" {
			c.Locals("user_id", "test-user-id")
			c.Locals("username", "test-user")
			c.Locals("email", "test@example.com")
			return c.Next()
		}

		// Get token from cookie
		tokenStr := c.Cookies("auth_token")
		if tokenStr == "" {
			// For API routes, return JSON error
			if strings.HasPrefix(c.Path(), "/api/") {
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
					"error": "unauthorized",
				})
			}
			// For web routes, redirect to login
			return c.Redirect("/auth/github/login")
		}

		// Parse and validate the token
		token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
			// Validate signing method
			if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fiber.ErrUnauthorized
			}
			return secret, nil
		})

		if err != nil || !token.Valid {
			// Clear invalid cookie
			c.Cookie(&fiber.Cookie{Name: "auth_token", Expires: time.Now().Add(-1 * time.Hour)})
			if strings.HasPrefix(c.Path(), "/api/") {
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
					"error": "invalid token",
				})
			}
			return c.Redirect("/auth/github/login")
		}

		// Extract claims
		claims, ok := token.Claims.(jwt.MapClaims)
		if !ok {
			c.Cookie(&fiber.Cookie{Name: "auth_token", Expires: time.Now().Add(-1 * time.Hour)})
			return c.Redirect("/auth/github/login")
		}

		// Store user info in context
		if userID, ok := claims["sub"].(string); ok {
			c.Locals("user_id", userID)
		}
		if username, ok := claims["username"].(string); ok {
			c.Locals("username", username)
		}

		return c.Next()
	}
}

// GetUserID retrieves the user ID from the Fiber context
func GetUserID(c *fiber.Ctx) string {
	if id, ok := c.Locals("user_id").(string); ok {
		return id
	}
	return ""
}

// GetUsername retrieves the username from the Fiber context
func GetUsername(c *fiber.Ctx) string {
	if username, ok := c.Locals("username").(string); ok {
		return username
	}
	return ""
}

// RequireAdmin is a middleware that checks if the user has admin access.
// For now, all authenticated users are considered admins.
// This can be extended to check specific roles in the future.
func RequireAdmin() fiber.Handler {
	return func(c *fiber.Ctx) error {
		userID := GetUserID(c)
		if userID == "" {
			if strings.HasPrefix(c.Path(), "/api/") {
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
					"error": "admin access required",
				})
			}
			return c.Redirect("/auth/github/login")
		}
		return c.Next()
	}
}
