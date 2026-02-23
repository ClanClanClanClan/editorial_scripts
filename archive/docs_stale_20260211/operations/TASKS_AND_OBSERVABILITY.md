Tasks & Observability – Operations Guide
=======================================

Background Tasking (Celery)
- Celery app: `src/ecc/infrastructure/tasks/celery_app.py`
- Jobs module: `src/ecc/infrastructure/tasks/jobs.py`
- Broker/backend: Redis on `redis://localhost:6380/0` (dev compose)
- Running workers:
  - `celery -A src.ecc.infrastructure.tasks.celery_app.celery_app worker -l info`
- Trigger tasks via API:
  - POST `/api/manuscripts/sync` → schedules extraction
  - POST `/api/manuscripts/enrich` → schedules enrichment
  - GET `/api/manuscripts/sync/{task_id}` → status (uses Celery AsyncResult)

Observability
- OpenTelemetry configured in `src/ecc/infrastructure/monitoring/telemetry.py`
- Enable via env:
  - `ECC_JAEGER_ENDPOINT` (default http://localhost:14268/api/traces)
  - `ECC_PROMETHEUS_PORT` (default 8090)
- Recommended Dashboards (Grafana):
  - API: requests total, request duration p95/p99, status code distribution
  - Extraction: manuscript_sync_duration_seconds, error totals by journal
  - Enrichment: ai_analysis_total, ai_human_agreement_total
  - Tasks: Celery worker throughput (configure Prometheus exporter for Celery)

Security & Secrets
- No default secrets in code.
- Provide via env or a secret provider (Vault/Keychain):
  - ORCID_CLIENT_ID / ORCID_CLIENT_SECRET
  - GMAIL_CREDENTIALS_PATH / GMAIL_TOKEN_PATH
  - OPENAI_API_KEY

Runbook
1) Start Redis & Postgres: `docker-compose -f docker-compose.dev.yml up -d`
2) Start API: `uvicorn src.ecc.main:app --reload`
3) Start worker: as above
4) Trigger a sync: `POST /api/manuscripts/sync {"journal_id":"MOR"}`
5) Track: `GET /api/manuscripts/sync/<task_id>`
6) Inspect downloads under `downloads/<JOURNAL>`

Prometheus scrape for Celery worker
- Exporter is embedded in worker (Prometheus client HTTP). Configure env:
  - `ECC_CELERY_METRICS_PORT=9099`
- Prometheus scrape config example:
```yaml
scrape_configs:
  - job_name: 'ecc-celery'
    static_configs:
      - targets: ['worker-host:9099']
```
Add Grafana dashboards using panels described in `docs/dashboards/GRAFANA_DASHBOARDS.md`.
