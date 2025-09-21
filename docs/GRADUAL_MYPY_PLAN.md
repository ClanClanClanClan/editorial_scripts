# Gradual Mypy Adoption Plan

This codebase mixes modern typed modules with legacy/experimental code. To adopt typing safely, we use a phased plan and keep CI green throughout.

## Phase 1 – Public API (complete)

Scope: `src/ecc/interfaces/**`
- Add function return types and key parameter annotations.
- Use concrete response models or `response_model=None` where endpoints return unions (e.g., CSV text).
- Keep external stubs ignored via pyproject.

CI: run `mypy src/ecc/interfaces` with strict settings; fail on errors.

## Phase 2 – Infrastructure (opt-in modules)

Scope: `src/ecc/infrastructure/**` (database, storage, tasks, monitoring)
- Start with leaf utilities (e.g., `storage/utils.py`) and database models (already typed).
- Add return types to `database/connection.py` public methods.
- For observability and celery stubs, prefer `typing.Any` for third-party surfaces unless stubs exist.
- Where external libs lack stubs, keep `ignore_missing_imports` entries.

CI: informational mypy on selected infra modules; do not fail the job yet.

## Phase 3 – Adapters

Scope: `src/ecc/adapters/**`
- Journal adapters rely on Playwright/Selenium; annotate method surfaces and domain types.
- Add `collections.abc` types for iterables and generators; replace `dict` with `dict[str, Any]`.
- Narrow gradually; skip complex/parsing-heavy functions initially.

CI: once stable, include adapters in informational mypy, then promote to required.

## Phase 4 – Core helpers & examples

Scope: `src/ecc/core/**`, `src/ecc/examples/**`
- Prioritize `core/domain/models.py` (mostly typed), then `audit_normalization.py`.
- Leave experimental example scripts out of CI type checks.

## Tooling & Config

- pyproject already includes:
  - `explicit_package_bases = true`, `packages=["src"]`
  - `ignore_missing_imports` for Playwright, Selenium, Google APIs, passlib, celery, aiosmtplib
- For modules with unavoidable `Any`, add targeted `# type: ignore[rule]` comments rather than blanket ignores.

## Promotion Criteria

- Each module should:
  - Have return type annotations on public functions/methods
  - Avoid `dict`/`list` without generics
  - Replace `Optional[T]` with `T | None`
  - Have ≤ a handful of `Any`s tied to third-party API boundaries

- Once a subpackage meets the criteria, promote it from informational to required in CI.

## Current CI Behavior

- Required: mypy on `src/ecc/interfaces`
- Informational: (was interfaces + infra) now interfaces only required; infra can be enabled when ready
- Security scans: bandit and pip-audit

## Next Steps

- Targeted fixes in `src/ecc/infrastructure/database/connection.py` and `src/ecc/infrastructure/tasks/celery_app.py`
- Add minimal types to `monitoring/middleware.py` response/dispatch surfaces
- If helpful, introduce a mypy config per-directory using `[[tool.mypy.overrides]]` with different flags

