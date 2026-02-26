package api

import (
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
)

func TestRequireAuth_TEST_MODE_Bypass(t *testing.T) {
	// Set TEST_MODE to true
	os.Setenv("TEST_MODE", "true")
	os.Setenv("DEV_MODE", "false")
	defer os.Unsetenv("TEST_MODE")
	defer os.Unsetenv("DEV_MODE")

	app := fiber.New()
	app.Get("/test", RequireAuth(), func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"user_id":  GetUserID(c),
			"username": GetUsername(c),
		})
	})

	resp, err := app.Test(httptest.NewRequest("GET", "/test", nil))
	assert.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode)

	// Verify test user context was set
	// The response should contain test-user-id
}

func TestRequireAuth_DEV_MODE_Bypass(t *testing.T) {
	// Set DEV_MODE to true
	os.Setenv("TEST_MODE", "false")
	os.Setenv("DEV_MODE", "true")
	defer os.Unsetenv("TEST_MODE")
	defer os.Unsetenv("DEV_MODE")

	app := fiber.New()
	app.Get("/test", RequireAuth(), func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"user_id":  GetUserID(c),
			"username": GetUsername(c),
		})
	})

	resp, err := app.Test(httptest.NewRequest("GET", "/test", nil))
	assert.NoError(t, err)
	assert.Equal(t, 200, resp.StatusCode)
}

func TestRequireAuth_NoToken_ProductionMode(t *testing.T) {
	// Set both modes to false (production)
	os.Setenv("TEST_MODE", "false")
	os.Setenv("DEV_MODE", "false")
	defer os.Unsetenv("TEST_MODE")
	defer os.Unsetenv("DEV_MODE")
	os.Setenv("JWT_SECRET", "test-secret")

	app := fiber.New()
	app.Get("/api/test", RequireAuth(), func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	resp, err := app.Test(httptest.NewRequest("GET", "/api/test", nil))
	assert.NoError(t, err)
	assert.Equal(t, 401, resp.StatusCode)
}

func TestGetUserID_Empty(t *testing.T) {
	app := fiber.New()
	app.Get("/test", func(c *fiber.Ctx) error {
		userID := GetUserID(c)
		assert.Empty(t, userID)
		return c.SendString(userID)
	})

	_, err := app.Test(httptest.NewRequest("GET", "/test", nil))
	assert.NoError(t, err)
}

func TestGetUsername_Empty(t *testing.T) {
	app := fiber.New()
	app.Get("/test", func(c *fiber.Ctx) error {
		username := GetUsername(c)
		assert.Empty(t, username)
		return c.SendString(username)
	})

	_, err := app.Test(httptest.NewRequest("GET", "/test", nil))
	assert.NoError(t, err)
}
