# Authentication Module

This module handles Discord OAuth authentication for both SoDA members and partner organizations.

## Features

### SoDA Member Authentication
- Standard Discord OAuth flow for SoDA officers
- Access and refresh token management
- Session management with officer guild information

### Partner Organization OAuth
- Domain-restricted OAuth for partner organizations
- Callback URL management
- Secure state parameter handling
- Partner member creation and management

## OAuth Flow for Partner Organizations

### 1. Domain Authorization
Partner organizations must have:
- `oauth_enabled = true`
- Valid `oauth_callback_url`
- `allowed_domains` list containing authorized domains

### 2. Authentication Process
1. User visits partner site and clicks login
2. Partner site redirects to `/auth/partner/login/<org_prefix>`
3. System validates origin domain against `allowed_domains`
4. If authorized, redirects to Discord OAuth with encoded state
5. After Discord authentication, user is redirected to partner's callback URL

### 3. State Parameter Security
The OAuth state parameter contains:
- Organization ID
- Origin domain
- Timestamp (for expiration)
- Base64 encoded for URL safety

## API Endpoints

### Partner OAuth
- `GET /auth/partner/login/<org_prefix>` - Initiate partner OAuth
- `GET /auth/callback` - Handle OAuth callback (shared with SoDA auth)

### SoDA Authentication
- `GET /auth/login` - Initiate SoDA OAuth
- `POST /auth/refresh` - Refresh access token
- `POST /auth/revoke` - Revoke refresh token
- `GET /auth/validateToken` - Validate token
- `GET /auth/name` - Get user name from token
- `POST /auth/logout` - Logout user

## URL Utilities

The `url_utils.py` module provides:

- Domain extraction and validation
- Callback URL building with parameters
- OAuth state parameter management
- Origin domain detection from requests

## Security Features

- Domain whitelisting for partner organizations
- OAuth state parameter validation
- Token expiration and refresh
- Secure callback URL handling
- CSRF protection via state parameter

## Configuration

Partner organizations must be configured with:
- `oauth_enabled: true`
- `oauth_callback_url: "https://partner.com/auth/callback"`
- `allowed_domains: ["partner.com", "app.partner.com"]`

## Example Usage

### Partner Site Integration
```javascript
// Redirect user to SoDA OAuth
const loginUrl = `https://api.soda.com/auth/partner/login/myorg`;
window.location.href = loginUrl;
```

### Callback Handling
```javascript
// Partner site receives callback with session token
const urlParams = new URLSearchParams(window.location.search);
const sessionToken = urlParams.get('session_token');
const memberId = urlParams.get('member_id');
const pointsBalance = urlParams.get('points_balance');

// Use session token for authenticated requests
```

## Error Handling

Common error responses:
- `400` - Missing or invalid parameters
- `403` - Domain not authorized
- `404` - Organization not found or OAuth not enabled
- `500` - Internal server error

## Logging

All authentication events are logged with:
- User/organization identification
- Domain validation results
- OAuth flow status
- Error details for debugging 