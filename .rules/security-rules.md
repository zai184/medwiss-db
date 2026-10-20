# Security Rules

## Authentication
- never store auth tokens in localStorage
- use httpOnly secure cookies for sessions
- rotate secrets regularly
- enforce session expiration
- require server-side authorization checks

## Secrets
- source API keys from shell environment
- never commit `.env` files
- never log secrets
- never expose secrets to client bundles
- use separate secrets per environment

## Input Validation
- validate all external input
- sanitize user-provided HTML
- reject unknown schema fields where appropriate
- enforce file upload limits

## Database
- never disable RLS
- use parameterized queries only
- use least-privilege database accounts
- enforce migrations through version control
- encrypt sensitive data at rest when applicable

## APIs
- rate limit public endpoints
- enforce request size limits
- apply timeouts to outbound requests
- require authentication by default
- audit external integrations

## Frontend
- avoid dangerouslySetInnerHTML unless sanitized
- never trust client-side validation alone
- avoid exposing internal implementation details
- use CSP headers where possible

## Infrastructure
- pin dependency versions
- scan dependencies for vulnerabilities
- keep containers minimal
- avoid running services as root
- isolate development and production credentials

## Logging & Monitoring
- log security-relevant events
- avoid logging PII unless necessary
- monitor authentication failures
- track privilege escalation attempts
- ensure audit logs are immutable where required

## AI Safety
- treat AI-generated code as untrusted until reviewed
- review generated authentication logic manually
- review generated SQL manually
- review generated infrastructure configs manually
- never auto-execute generated shell commands blindly
