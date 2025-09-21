# Security Policy

This project processes sensitive academic and personal data. The following guidelines apply to all contributors and deployments.

## Supported Versions

- Active development: main branch (version 2.x)
- Legacy code under `production/` and `editorial_assistant/` is archived and not maintained. Do not deploy it.

## Reporting a Vulnerability

- Email: dylan.possamai@math.ethz.ch
- Please include a minimal reproduction and impacted components.
- We aim to acknowledge reports within 72 hours and provide a remediation plan within 14 days.

## Hardening Checklist (Deployment)

- Set `ECC_ENV=production`
- Set a strong `ECC_SECRET_KEY` (32+ bytes random)
- Use `DATABASE_URL` with least-privileged credentials
- Restrict CORS via `ECC_CORS_ORIGINS`
- Run behind TLS with a reverse proxy
- Run as non-root (Dockerfile does)
- Configure observability endpoints for your environment only
- Rotate API keys regularly (OpenAI, Gmail)

## Secrets Management

- Preferred sources: environment variables, OS keychain (via `keyring`), or HashiCorp Vault
- Never commit secrets or OAuth tokens; files under `config/` are git-ignored where applicable
- For Gmail OAuth, prefer `GMAIL_CREDENTIALS_JSON`/`GMAIL_TOKEN_JSON` via secret store

## Data Protection & PII

- Do not log raw emails, tokens, or passwords
- Use masking helpers where insight is needed (e.g., `j***@example.com`)
- Ensure GDPR-compliant handling for audit logs and exports

## Authentication & Authorization

- JWT tokens signed with `ECC_SECRET_KEY` (HS256)
- Default demo users are for development only; disable in production
- Use `require_roles`/`require_role` guards on sensitive endpoints

## Dependencies & Supply Chain

- Dependencies are pinned via Poetry
- Use `pre-commit` hooks (black, ruff, mypy, detect-secrets)
- Container images are built from `python:3.11-slim` with a non-root user
