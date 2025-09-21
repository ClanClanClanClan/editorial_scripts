# Contributing

Welcome! This repository uses Python 3.11 + Poetry with pre-commit hooks and tiered type checking.

## Setup

- Prerequisites: Python 3.11, Git
- Install deps: `make install`
- Install hooks: `make hooks`

## Common commands

- Lint: `make lint` (ruff + black --check)
- Auto-fix: `make fix` (ruff --fix + black)
- Type check (enforced): `make type` (API/DB/main; plus monitoring/tasks/storage via PRs)
- Type check (all ECC): `make type-all` (may fail until coverage improves)
- Tests: `make test`
- Security (local best-effort): `make security` (artifacts in artifacts/security)
- Secrets check: `make secrets`
- CI-like bundle: `make ci`

## Security hooks (configurable)

Pre-commit includes a single security hook wrapper for bandit + pip-audit.
Choose enforcement stage via `.precommit-security.yaml`:

```
mode: commit   # or push or both
```

Additional controls:
- Bandit severity via env: `BANDIT_LEVEL=HIGH|MEDIUM|LOW` (default HIGH)
- Allowlist files: `.security/bandit-allowlist.txt`, `.security/pip-audit-allowlist.txt`

## CI security artifacts

Workflows upload JSON artifacts for bandit and pip-audit; summaries are posted to the job summary. Retention: 14 days.

## Tiered mypy

- Enforced tier includes: API/DB/main, and via dedicated PRs monitoring/tasks/storage
- Manual mypy hook exists for full src/ecc. Expand coverage directory-by-directory.

## Branch protection (approve-required)

To require PR reviews on `main`/`master`, run (admin):

```
REPO=owner/repo BRANCH=main bash scripts/admin/enable_branch_protection.sh
```

This uses GitHub CLI or curl (requires `GITHUB_TOKEN`).

## PRs

- Use descriptive titles; keep changes small and focused.
- For large style-only churn, isolate in a separate branch/PR (see style-sweep).

Thanks for contributing!

