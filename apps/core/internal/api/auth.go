package api

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/github"
)

// AuthHandler handles GitHub OAuth authentication
type AuthHandler struct {
	db     *sql.DB
	oauth  *oauth2.Config
	secret []byte
}

// NewAuthHandler creates a new AuthHandler
func NewAuthHandler(db *sql.DB) *AuthHandler {
	appURL := os.Getenv("APP_URL")
	if appURL == "" {
		appURL = "http://localhost:3000"
	}
	return &AuthHandler{
		db:     db,
		secret: []byte(os.Getenv("JWT_SECRET")),
		oauth: &oauth2.Config{
			ClientID:     os.Getenv("GITHUB_CLIENT_ID"),
			ClientSecret: os.Getenv("GITHUB_CLIENT_SECRET"),
			Endpoint:     github.Endpoint,
			Scopes:       []string{"read:user", "user:email"},
			RedirectURL:  appURL + "/auth/github/callback",
		},
	}
}

// Login initiates the GitHub OAuth flow
func (h *AuthHandler) Login(c *fiber.Ctx) error {
	url := h.oauth.AuthCodeURL("state-token", oauth2.AccessTypeOnline)
	return c.Redirect(url, http.StatusTemporaryRedirect)
}

// Callback handles the GitHub OAuth callback
func (h *AuthHandler) Callback(c *fiber.Ctx) error {
	code := c.Query("code")
	if code == "" {
		return c.Status(400).SendString("Code missing")
	}

	token, err := h.oauth.Exchange(context.Background(), code)
	if err != nil {
		return c.Status(400).SendString("Token exchange failed: " + err.Error())
	}

	client := h.oauth.Client(context.Background(), token)
	resp, err := client.Get("https://api.github.com/user")
	if err != nil {
		return c.Status(500).SendString("GitHub API failed: " + err.Error())
	}
	defer resp.Body.Close()

	var ghUser struct {
		ID        int    `json:"id"`
		Login     string `json:"login"`
		Email     string `json:"email"`
		AvatarURL string `json:"avatar_url"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&ghUser); err != nil {
		return c.Status(500).SendString("Failed to decode GitHub user: " + err.Error())
	}

	// Upsert user in database
	var userID string
	err = h.db.QueryRow(`
		INSERT INTO users (github_id, username, email, avatar_url, last_login) 
		VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP) 
		ON CONFLICT (github_id) DO UPDATE 
		SET username = EXCLUDED.username, email = EXCLUDED.email, 
		    avatar_url = EXCLUDED.avatar_url, last_login = CURRENT_TIMESTAMP 
		RETURNING id`,
		fmt.Sprintf("%d", ghUser.ID), ghUser.Login, ghUser.Email, ghUser.AvatarURL,
	).Scan(&userID)
	if err != nil {
		return c.Status(500).SendString("DB error: " + err.Error())
	}

	// Generate JWT token
	jwtToken := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":      userID,
		"username": ghUser.Login,
		"exp":      time.Now().Add(24 * time.Hour * 7).Unix(),
	})
	signedString, err := jwtToken.SignedString(h.secret)
	if err != nil {
		return c.Status(500).SendString("JWT error: " + err.Error())
	}

	// Set HTTP-only cookie
	c.Cookie(&fiber.Cookie{
		Name:     "auth_token",
		Value:    signedString,
		Expires:  time.Now().Add(24 * time.Hour * 7),
		HTTPOnly: true,
		Secure:   os.Getenv("DEV_MODE") != "true",
		SameSite: "Lax",
		Path:     "/",
	})

	return c.Redirect("/admin", http.StatusTemporaryRedirect)
}

// Logout clears the auth cookie
func (h *AuthHandler) Logout(c *fiber.Ctx) error {
	c.Cookie(&fiber.Cookie{Name: "auth_token", Expires: time.Now().Add(-1 * time.Hour)})
	return c.Redirect("/admin", http.StatusTemporaryRedirect)
}
