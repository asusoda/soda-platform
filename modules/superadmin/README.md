# SuperAdmin Module

This module provides superadmin functionality for managing organizations, OAuth configurations, and system-wide settings.

## Features

### Organization Management
- Add/remove Discord guilds as organizations
- Configure officer roles for each organization
- Manage organization settings and configurations

### OAuth Configuration Management
- Enable/disable OAuth for partner organizations
- Configure callback URLs for OAuth flows
- Manage allowed domains for authentication
- Test OAuth configurations

### System Monitoring
- Dashboard with organization overview
- OAuth status summary across all organizations
- Guild role management

## API Endpoints

### Dashboard and Overview
- `GET /superadmin/check` - Verify superadmin privileges
- `GET /superadmin/dashboard` - Get superadmin dashboard data
- `GET /superadmin/organizations/oauth/summary` - Get OAuth summary across all organizations

### Organization Management
- `POST /superadmin/add_org/<guild_id>` - Add new organization from Discord guild
- `DELETE /superadmin/remove_org/<int:org_id>` - Remove organization
- `GET /superadmin/guild_roles/<guild_id>` - Get roles from Discord guild
- `PUT /superadmin/update_officer_role/<int:org_id>` - Update officer role for organization

### OAuth Configuration
- `PUT /superadmin/organizations/<int:org_id>/oauth` - Update OAuth settings
- `GET /superadmin/organizations/<int:org_id>/oauth` - Get OAuth settings
- `PUT /superadmin/organizations/<int:org_id>/domains` - Update allowed domains
- `PUT /superadmin/organizations/<int:org_id>/callback` - Update callback URL
- `POST /superadmin/organizations/<int:org_id>/oauth/test` - Test OAuth configuration

## OAuth Configuration

### Required Fields
When enabling OAuth for an organization, the following fields are required:

```json
{
  "oauth_enabled": true,
  "oauth_callback_url": "https://partner.com/auth/callback",
  "allowed_domains": ["partner.com", "app.partner.com"]
}
```

### Domain Management
- Domains are automatically sanitized and validated
- Subdomain matching is supported (e.g., `app.partner.com` matches `partner.com`)
- Invalid domains are filtered out during updates

### Callback URL Validation
- Must include scheme (http:// or https://)
- Must have valid domain format
- Only HTTP and HTTPS schemes are allowed

## Usage Examples

### Enable OAuth for Organization
```bash
curl -X PUT "https://api.soda.com/superadmin/organizations/1/oauth" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_enabled": true,
    "oauth_callback_url": "https://myapp.com/auth/callback",
    "allowed_domains": ["myapp.com", "app.myapp.com"]
  }'
```

### Update Allowed Domains
```bash
curl -X PUT "https://api.soda.com/superadmin/organizations/1/domains" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_domains": ["newdomain.com", "api.newdomain.com"]
  }'
```

### Test OAuth Configuration
```bash
curl -X POST "https://api.soda.com/superadmin/organizations/1/oauth/test" \
  -H "Authorization: Bearer <token>"
```

## Response Formats

### OAuth Settings Response
```json
{
  "oauth_enabled": true,
  "oauth_callback_url": "https://partner.com/auth/callback",
  "allowed_domains": ["partner.com", "app.partner.com"],
  "oauth_state_secret": "generated_secret_token"
}
```

### OAuth Test Response
```json
{
  "organization": "Partner Org",
  "oauth_config": {
    "oauth_enabled": true,
    "has_callback_url": true,
    "has_allowed_domains": true,
    "domains_count": 2,
    "has_state_secret": true,
    "callback_url_valid": true,
    "valid_domains": ["partner.com", "app.partner.com"],
    "invalid_domains": [],
    "all_domains_valid": true
  }
}
```

### OAuth Summary Response
```json
{
  "total_organizations": 5,
  "oauth_enabled_count": 3,
  "oauth_configured_count": 2,
  "organizations_with_domains": 2,
  "organizations_with_callbacks": 2,
  "organizations_details": [...]
}
```

## Security Features

- Superadmin privilege verification
- Input validation and sanitization
- Secure OAuth state secret generation
- Domain format validation
- Callback URL security checks

## Error Handling

Common error responses:
- `400` - Invalid request data or validation errors
- `401` - Unauthorized (not superadmin)
- `404` - Organization not found
- `500` - Internal server error

## Logging

All superadmin actions are logged with:
- User identification
- Action performed
- Organization affected
- Success/failure status
- Error details for debugging

## Dependencies

- Flask Blueprint for routing
- SQLAlchemy for database operations
- Discord.py for guild management
- Custom authentication decorators
- URL validation utilities

