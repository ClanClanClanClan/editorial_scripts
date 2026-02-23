ECC Implementation Plan – Next 1–2 Weeks
========================================

Scope
- Finish core ECC features for MF/MOR/FS with async adapters, background tasks, observability, and secure configuration.

1) Wire Repository into API Routes
- Manuscripts API (list/get) now queries DB; extend to:
  - POST /api/manuscripts/sync → schedules Celery `ecc.sync_journal`
  - GET /api/manuscripts/sync/{task_id} → returns task status via Redis backend
  - POST /api/manuscripts/enrich → schedules `ecc.sync_journal(enrich=True)`

2) Background Tasks: Redis + Celery
- Celery app: `src/ecc/infrastructure/tasks/celery_app.py`
- Jobs: `src/ecc/infrastructure/tasks/jobs.py`
  - `sync_journal(journal_id, enrich=False, ...)`
  - Runs adapters MF/MOR/FS, enrichment, and persists via repository
- Configure env:
  - `ECC_BROKER_URL` (default `redis://localhost:6380/0`)
  - `ECC_RESULT_BACKEND` (default broker)
- Operations
  - Start Redis (docker-compose.dev.yml)
  - Run worker: `celery -A src.ecc.infrastructure.tasks.celery_app.celery_app worker -l info`

3) Secrets Management
- Remove hard-coded ORCID defaults (done). Use env/Keychain/Vault paths:
  - `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`
  - `GMAIL_CREDENTIALS_PATH`, `GMAIL_TOKEN_PATH`, `OPENAI_API_KEY`
- Next: implement Vault/Keychain fetch in dedicated provider; fall back to env

4) Testing
- Add unit tests for:
  - ORCID client (init without secrets)
  - Celery app config
  - Repository `save_full` basic behavior with an in-memory DB (future)
- Add adapter smoke tests (MOR/MF/FS) under `tests/`

5) Observability
- Confirm OTEL export targets via env:
  - `ECC_JAEGER_ENDPOINT` → Jaeger
  - `ECC_PROMETHEUS_PORT` → Prometheus reader
- Add dashboards (Grafana) for:
  - API availability & latency (p95/p99)
  - Extraction durations & error rates
  - Enrichment volumes & success rates
  - Task throughput (Celery)

Optional (High-Value)
- Letter parsing heuristics
  - Map letters and attachments more precisely (e.g., Decision vs. Report) based on templates and filenames
- Referee metrics
  - Compute response time, overdue counts, acceptance rates from Audit Trail and letter events; persist in `RefereeModel.historical_performance`

Deliverables
- Working Celery tasks + API control plane for sync/enrich
- Secure configuration without default secrets
- Tests coverage improvements
- Runbook + dashboards for ops
