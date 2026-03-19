// Package auth provides authentication middleware for Fiber
//
// DEPRECATED: Clerk authentication has been replaced with native JWT + GitHub OAuth.
// Use iterateswarm-core/internal/api.RequireAuth() instead.
// This file is kept for backward compatibility only.
package auth

import (
	"context"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

const (
	// ClerkJWKSURL is the URL to Clerk's JWKS endpoint
	ClerkJWKSURL = "https://%s.clerk.accounts.com/.well-known/jwks.json"
)

// ClerkConfig holds the configuration for Clerk authentication
type ClerkConfig struct {
	// ClerkInstanceID is your Clerk instance ID (e.g., "your-instance")
	ClerkInstanceID string
	// SecretKey is your Clerk secret key (CLERK_SECRET_KEY)
	SecretKey string
	// JWKSURL is the JWKS endpoint URL (optional, auto-generated from ClerkInstanceID)
	JWKSURL string
	// SkipSkipPaths are paths to skip authentication
	SkipSkipPaths []string
}

// ClerkClaims represents the claims in a Clerk JWT
type ClerkClaims struct {
	jwt.RegisteredClaims
	UserID string `json:"sub"`
	Email  string `json:"email"`
	Role   string `json:"role"`
}

// ClerkAuth holds the authentication state
type ClerkAuth struct {
	config   ClerkConfig
	jwks     *JWKS
	jwksMu   sync.RWMutex
	jwksLast time.Time
}

// JWKS represents a JSON Web Key Set
type JWKS struct {
	Keys []JWK `json:"keys"`
}

// JWK represents a JSON Web Key
type JWK struct {
	Kid string `json:"kid"`
	Kty string `json:"kty"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	N   string `json:"n"`
	E   string `json:"e"`
}

// NewClerkAuth creates a new Clerk authentication handler
func NewClerkAuth(config ClerkConfig) *ClerkAuth {
	if config.JWKSURL == "" && config.ClerkInstanceID != "" {
		config.JWKSURL = fmt.Sprintf(ClerkJWKSURL, config.ClerkInstanceID)
	}
	return &ClerkAuth{
		config: config,
	}
}

// Middleware returns a Fiber middleware that validates Clerk JWT tokens
func (c *ClerkAuth) Middleware() fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		// Skip authentication for specified paths
		path := ctx.Path()
		for _, skipPath := range c.config.SkipSkipPaths {
			if strings.HasPrefix(path, skipPath) {
				return ctx.Next()
			}
		}

		// Extract Bearer token from Authorization header
		authHeader := ctx.Get("Authorization")
		if authHeader == "" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(map[string]string{
				"error": "Missing Authorization header",
			})
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(map[string]string{
				"error": "Invalid Authorization header format",
			})
		}

		tokenString := parts[1]

		// Parse and validate the token
		claims, err := c.ValidateToken(tokenString)
		if err != nil {
			return ctx.Status(fiber.StatusUnauthorized).JSON(map[string]string{
				"error": "Invalid token: " + err.Error(),
			})
		}

		// Store claims in context for use by handlers
		ctx.Locals("user_id", claims.UserID)
		ctx.Locals("user_email", claims.Email)
		ctx.Locals("user_role", claims.Role)
		ctx.Locals("claims", claims)

		return ctx.Next()
	}
}

// ValidateToken validates a Clerk JWT token and returns the claims
func (c *ClerkAuth) ValidateToken(tokenString string) (*ClerkClaims, error) {
	// Parse the token header to get the key ID
	token, _, err := new(jwt.Parser).ParseUnverified(tokenString, &ClerkClaims{})
	if err != nil {
		return nil, fmt.Errorf("failed to parse token: %w", err)
	}

	kid, ok := token.Header["kid"].(string)
	if !ok {
		return nil, errors.New("token missing kid header")
	}

	// Get the public key for this token
	publicKey, err := c.getPublicKey(kid)
	if err != nil {
		return nil, fmt.Errorf("failed to get public key: %w", err)
	}

	// Parse and validate the token with the public key
	claims := &ClerkClaims{}
	token, err = jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return publicKey, nil
	}, jwt.WithValidMethods([]string{"RS256", "RS384", "RS512"}))

	if err != nil {
		return nil, fmt.Errorf("token validation failed: %w", err)
	}

	if !token.Valid {
		return nil, errors.New("token is not valid")
	}

	if claims.UserID == "" {
		return nil, errors.New("token missing user ID (sub claim)")
	}

	return claims, nil
}

// getPublicKey retrieves the public key for the given key ID from Clerk's JWKS
func (c *ClerkAuth) getPublicKey(kid string) (*rsa.PublicKey, error) {
	// Cache JWKS for 1 hour
	c.jwksMu.RLock()
	if c.jwks != nil && time.Since(c.jwksLast) < time.Hour {
		key := c.findKey(kid)
		c.jwksMu.RUnlock()
		if key != nil {
			return key, nil
		}
	}
	c.jwksMu.RUnlock()

	// Refresh JWKS
	if err := c.refreshJWKS(); err != nil {
		return nil, err
	}

	c.jwksMu.RLock()
	defer c.jwksMu.RUnlock()
	key := c.findKey(kid)
	if key == nil {
		return nil, fmt.Errorf("key not found in JWKS: %s", kid)
	}
	return key, nil
}

// findKey finds the RSA public key with the given key ID
func (c *ClerkAuth) findKey(kid string) *rsa.PublicKey {
	for _, key := range c.jwks.Keys {
		if key.Kid == kid && key.Kty == "RSA" {
			return jwkToRSAPublicKey(key)
		}
	}
	return nil
}

// refreshJWKS fetches the latest JWKS from Clerk
func (c *ClerkAuth) refreshJWKS() error {
	c.jwksMu.Lock()
	defer c.jwksMu.Unlock()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.config.JWKSURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Add Authorization header with secret key
	if c.config.SecretKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.SecretKey)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to fetch JWKS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("JWKS request failed with status: %d", resp.StatusCode)
	}

	var jwks JWKS
	if err := json.NewDecoder(resp.Body).Decode(&jwks); err != nil {
		return fmt.Errorf("failed to decode JWKS: %w", err)
	}

	c.jwks = &jwks
	c.jwksLast = time.Now()

	return nil
}

// jwkToRSAPublicKey converts a JWK to an RSA public key
func jwkToRSAPublicKey(jwk JWK) *rsa.PublicKey {
	if jwk.N == "" || jwk.E == "" {
		return nil
	}

	// Decode the modulus
	nBytes, err := base64.RawURLEncoding.DecodeString(jwk.N)
	if err != nil {
		log.Printf("Failed to decode modulus: %v", err)
		return nil
	}
	n := new(big.Int).SetBytes(nBytes)

	// Decode the exponent
	eBytes, err := base64.RawURLEncoding.DecodeString(jwk.E)
	if err != nil {
		log.Printf("Failed to decode exponent: %v", err)
		return nil
	}
	e := 0
	for _, b := range eBytes {
		e = e<<8 + int(b)
	}

	return &rsa.PublicKey{
		N: n,
		E: e,
	}
}

// GetUserID retrieves the user ID from the Fiber context
func GetUserID(ctx *fiber.Ctx) string {
	if id, ok := ctx.Locals("user_id").(string); ok {
		return id
	}
	return ""
}

// GetUserEmail retrieves the user email from the Fiber context
func GetUserEmail(ctx *fiber.Ctx) string {
	if email, ok := ctx.Locals("user_email").(string); ok {
		return email
	}
	return ""
}

// GetUserRole retrieves the user role from the Fiber context
func GetUserRole(ctx *fiber.Ctx) string {
	if role, ok := ctx.Locals("user_role").(string); ok {
		return role
	}
	return ""
}

// RequireAuth is a middleware that returns 401 if user is not authenticated
func RequireAuth() fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		userID := GetUserID(ctx)
		if userID == "" {
			return ctx.Status(fiber.StatusUnauthorized).JSON(map[string]string{
				"error": "Authentication required",
			})
		}
		return ctx.Next()
	}
}

// RequireRole is a middleware that returns 403 if user doesn't have required role
func RequireRole(roles ...string) fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		userRole := GetUserRole(ctx)
		if userRole == "" {
			return ctx.Status(fiber.StatusForbidden).JSON(map[string]string{
				"error": "Role verification required",
			})
		}

		for _, role := range roles {
			if userRole == role {
				return ctx.Next()
			}
		}

		return ctx.Status(fiber.StatusForbidden).JSON(map[string]string{
			"error": "Insufficient permissions",
		})
	}
}

// LoadClerkConfig loads Clerk configuration from environment variables
func LoadClerkConfig() ClerkConfig {
	return ClerkConfig{
		ClerkInstanceID: os.Getenv("CLERK_INSTANCE_ID"),
		SecretKey:       os.Getenv("CLERK_SECRET_KEY"),
		JWKSURL:         os.Getenv("CLERK_JWKS_URL"),
		SkipSkipPaths: []string{
			"/health",
			"/health/details",
			"/webhooks",
		},
	}
}
