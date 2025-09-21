Secrets & API Security – Implementation Notes
============================================

Secrets Providers
- Code uses a secrets provider abstraction: `src/ecc/infrastructure/secrets/provider.py`
- Order of precedence: Environment → System Keychain (via `keyring`) → (Future) Vault
- Keys in use:
  - ORCID_CLIENT_ID / ORCID_CLIENT_SECRET
  - GMAIL_CREDENTIALS_PATH / GMAIL_TOKEN_PATH
  - OPENAI_API_KEY
  - DATABASE_URL

Production Guidance
- Prefer Vault/Keychain and set environment variables at container start.
- Never commit secrets to VCS. `.gitignore` includes JSON/token files.

API Security
- Security headers added via middleware (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP minimal).
- Rate limiting middleware (IP+path) configurable by env `ECC_RATE_LIMIT_PER_MINUTE` (default 180).
- CORS strict by default in production (`ECC_ENV=production` requires explicit `ECC_CORS_ORIGINS`).
- JWT auth and role checks on mutating endpoints.

Hardening Next Steps
- Replace demo users with a proper user store and password hashing/rotation policies.
- Add request ID and structured logging correlation.
- Add TLS termination and HSTS at ingress level.

