# Secrets & Credentials Setup

This project uses environment variables, optional OS keychain, and an optional Vault backend to manage secrets. This guide shows how to configure credentials for local development and production.

## Overview

- Primary sources of secrets: environment variables, macOS Keychain (via `keyring`), HashiCorp Vault (if configured).
- Code references
  - Secrets provider: `src/ecc/infrastructure/secrets/provider.py`
  - API server: `src/ecc/main.py`
  - OpenAI client: `src/ecc/adapters/ai/openai_client.py`
  - ORCID client: `src/core/orcid_client.py`
  - Gmail access: `src/core/gmail_manager.py`, `src/core/gmail_verification.py`, `src/ecc/adapters/messaging/email_client.py`

## Required Secrets

### ECC App Secret

- `ECC_SECRET_KEY`: a strong, random secret used to sign JWTs.
- Required in production. The server will refuse to start if the default is set.

Generate a strong key (hex):

```
python - << 'PY'
import secrets
print(secrets.token_hex(32))
PY
```

Set as env or store in your secret backend.

### Database

Provide one of the following:

- `DATABASE_URL` (preferred): `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DBNAME`
- or individual parts (Vault/env): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

The app constructs the URL if all parts are present; otherwise falls back to `DATABASE_URL`.

### OpenAI

- `OPENAI_API_KEY`: required to enable AI endpoints.
- Optional: `OPENAI_ORG`

The AI API is only invoked when the `/api/ai/analyze` endpoint is used. If no key is configured, the endpoint returns `503`.

### ORCID API

- `ORCID_CLIENT_ID`
- `ORCID_CLIENT_SECRET`

Used by `src/core/orcid_client.py` for public API access to enrich profiles.

### Gmail OAuth (for verification codes and email extraction)

Two options:

1) File-based (ignored by git; recommended for local dev)

- Place Google OAuth client credentials at `config/gmail_credentials.json`.
- The first OAuth flow will create `config/gmail_token.json`.

2) Secrets-injected JSON

- Provide base64 or raw JSON via secret provider under keys:
  - `GMAIL_CREDENTIALS_JSON`
  - `GMAIL_TOKEN_JSON`

The code will write these to `config/gmail_credentials.json` and `config/gmail_token.json` if files are absent.

Scopes used:
- Read-only access for reading verification codes: `https://www.googleapis.com/auth/gmail.readonly`
- Optional send capability for notifications: `https://www.googleapis.com/auth/gmail.send`

Test/CI stub for 2FA:
- `ECC_GMAIL_2FA_CODE`: a 6-digit code. If set, it bypasses Gmail retrieval in test contexts.

## macOS Keychain (optional)

If `keyring` is installed, the secrets provider will attempt to read from the OS keychain with service name `ecc` by default (override via `ECC_KEYCHAIN_SERVICE`).

## HashiCorp Vault (optional)

If `VAULT_ADDR` and `VAULT_TOKEN` are set, the Vault provider will attempt to read keys from KV v2 using:

- Base path: `ECC_SECRETS_BASE_PATH` (default: `secret/data/ecc`)
- Environment: `ECC_ENV` (e.g. `development`, `staging`, `production`)
- Namespace: `ECC_SECRET_NAMESPACE` (default: `default`)

Lookup order:
1. `<base>`
2. `<base>/<env>`
3. `<base>/<env>/<namespace>`

This allows layering common + environment + per-namespace secrets.

## Environment Matrix (examples)

```
# Core
ECC_ENV=development
ECC_SECRET_KEY=<random-64-hex>

# Database (prefer a single DATABASE_URL)
DATABASE_URL=postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG=org_...

# ORCID
ORCID_CLIENT_ID=...
ORCID_CLIENT_SECRET=...

# Gmail (file-based or injected)
# GMAIL_CREDENTIALS_JSON='{"installed":{...}}'
# GMAIL_TOKEN_JSON='{"token": "..."}'
```

## Notes

- Git ignores credentials and token files under `config/`.
- Production startup fails if `ECC_ENV=production` and `ECC_SECRET_KEY` is not set to a strong value.
- For 2FA during automation, the app looks for `ECC_GMAIL_2FA_CODE`; otherwise it will fetch from Gmail if configured.

