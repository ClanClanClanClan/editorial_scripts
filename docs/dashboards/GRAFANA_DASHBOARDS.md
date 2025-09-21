Grafana Dashboards – Suggested Panels & Queries
================================================

Data Sources
- Prometheus (ECC metrics from OpenTelemetry exporter)
- Jaeger (traces; use Tempo if available)

API Service Dashboard
- Requests total by method, endpoint, status: `http_requests_total`
- Request duration p50/p95/p99: `http_request_duration_seconds`
- Error rate by endpoint (4xx/5xx)

Extraction Dashboard
- Sync duration histogram: `manuscript_sync_duration_seconds`
- Adapter errors: `journal_errors_total{journal=~"MF|MOR|FS"}`
- Time since last sync: `time_since_last_sync_seconds`

AI/Enrichment Dashboard
- Analyses total: `ai_analysis_total{analysis_type=~".*"}`
- Agreement counts: `ai_human_agreement_total`
- Average confidence by journal/type (sum(confidence * count)/sum(count)) – build as recording rule

Celery/Worker Dashboard
- Worker throughput (use Prometheus exporter for Celery or indirect stats via task result table)
- In-flight tasks vs. completed vs. failed (derive from task result states)

Tracing/Latency
- Jaeger search: service `ecc-api`; investigate spans with highest latency
- Trace exemplars linked from Prometheus histograms (if enabled)

