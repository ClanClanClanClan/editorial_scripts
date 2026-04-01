# CLAUDE.md - Editorial Scripts AI Assistant Guide

## CRITICAL: CREDENTIALS ARE ALREADY STORED
**DO NOT ASK FOR CREDENTIALS - They are permanently stored in macOS Keychain**
- **Test with:** `python3 verify_all_credentials.py`
- **Auto-loaded via:** `~/.zshrc` -> `~/.editorial_scripts/load_all_credentials.sh`

---

## Project Overview

Dylan Possamai's end-to-end editorial management system for 8 academic journals.
- **Purpose**: Extract referee reports, manuscripts, and metadata; detect state changes; recommend referees; generate AE decision reports
- **Architecture**: Extraction (Selenium + Gmail API) → Event System (state detection) → ML Pipeline (referee recommendation) → Dashboard (Flask + HTML)
- **Status**: 8 extractors working, event-driven pipeline operational, dashboard with referee intelligence

### System Architecture

```
Extractors (8 journals)
    ↓ JSON outputs
State Store (SQLite) → Event Dispatcher
    ↓ typed events (NEW_MANUSCRIPT, ALL_REPORTS_IN, STATUS_CHANGED)
Event Processor
    ├── NEW_MANUSCRIPT → Referee Pipeline (desk rejection + candidate search)
    └── ALL_REPORTS_IN → AE Report Generator (Claude API / clipboard)
    ↓
Dashboard Server (Flask :8421) ← API endpoints
    ↓
Dashboard HTML (referee intelligence, action items, inline AE reports)
```

### Project Structure
```
editorial_scripts/
├── production/src/extractors/     # 8 journal extractors
│   ├── mf_extractor.py           # MF - ScholarOne (ComprehensiveMFExtractor)
│   ├── mor_extractor.py          # MOR - ScholarOne (MORExtractor)
│   ├── fs_extractor.py           # FS - Gmail API (ComprehensiveFSExtractor)
│   ├── jota_extractor.py         # JOTA - Editorial Manager (JOTAExtractor)
│   ├── mafe_extractor.py         # MAFE - Editorial Manager (MAFEExtractor)
│   ├── sicon_extractor.py        # SICON - SIAM (SICONExtractor)
│   ├── sifin_extractor.py        # SIFIN - SIAM (SIFINExtractor)
│   ├── naco_extractor.py         # NACO - EditFlow/MSP (NACOExtractor)
│   └── generate_fs_timeline_report.py
├── production/src/core/           # Shared utilities & event system
│   ├── scholarone_base.py        # ScholarOne base class (MF, MOR)
│   ├── em_base.py                # Editorial Manager base class (JOTA, MAFE)
│   ├── siam_base.py              # SIAM base class (SICON, SIFIN)
│   ├── event_dispatcher.py       # State change detection → typed events
│   ├── event_processor.py        # Event handler (AE reports, pipeline trigger)
│   ├── state_store.py            # SQLite manuscript state tracking
│   ├── cache_manager.py          # SQLite persistent cache
│   ├── cache_integration.py      # CachedExtractorMixin
│   ├── academic_apis.py          # AcademicProfileEnricher (S2, OpenAlex)
│   ├── web_enrichment.py         # ORCID + CrossRef + S2 + OpenAlex enrichment
│   ├── orcid_lookup.py           # ORCID API client with SQLite cache
│   ├── output_schema.py          # Canonical output schema normalization
│   ├── gmail_search.py           # Gmail timeline integration
│   ├── gmail_verification.py     # 2FA code fetching
│   └── scholarone_utils.py       # with_retry decorator, exponential backoff
├── production/src/pipeline/       # ML pipeline & referee recommendation
│   ├── __init__.py               # Constants: JOURNALS, OUTPUTS_DIR, MODELS_DIR, H_INDEX_CAP
│   ├── referee_pipeline.py       # 5-step orchestrator
│   ├── desk_rejection.py         # Heuristic + model + optional LLM assessment
│   ├── referee_finder.py         # Candidate sourcing (OpenAlex, S2, historical, FAISS)
│   ├── conflict_checker.py       # Institution, coauthorship, opposed, editor conflicts
│   ├── embeddings.py             # SPECTER2 / MiniLM / TF-IDF embeddings + FAISS
│   ├── training.py               # ModelTrainer: trains all 3 ML models
│   ├── report_quality.py         # 6-dimension report quality scoring
│   ├── ae_report.py              # AE recommendation report generator
│   ├── ae_prompt_template.py     # Claude/ChatGPT prompt builder for AE reports
│   ├── referee_db.py             # SQLite referee performance DB with learning
│   ├── referee_db_backfill.py    # Populate referee DB from extraction history
│   └── models/                   # Trained ML model artifacts
│       ├── expertise_index.py    # FAISS semantic referee search
│       ├── response_predictor.py # P(accept) and P(complete) prediction
│       └── outcome_predictor.py  # P(manuscript_accepted) prediction
├── production/src/reporting/      # Action items & cross-journal reports
│   ├── action_items.py           # Priority-based editorial action computation
│   └── cross_journal_report.py   # Cross-journal statistics aggregation
├── production/outputs/            # All output data
│   ├── {journal}/                # Extraction JSONs per journal (8 dirs)
│   ├── {journal}/ae_reports/     # Generated AE recommendation reports
│   ├── {journal}/recommendations/ # Referee recommendation reports
│   └── dashboard.html            # Generated dashboard
├── production/events/             # Event queue (JSONL)
│   ├── pending.jsonl             # Unprocessed events
│   └── processed.jsonl           # Processed event history
├── production/models/             # ML model artifacts + referee DB
│   ├── referee_profiles.db       # SQLite referee performance database
│   ├── referee_index.faiss       # FAISS expertise index
│   ├── referee_metadata.json     # Expertise index metadata
│   ├── response_predictor.joblib # Trained response predictor
│   ├── outcome_predictor.joblib  # Trained outcome predictor
│   ├── training_metadata.json    # Model training metadata
│   └── feedback/                 # Editorial decision feedback (JSONL)
├── production/downloads/          # Downloaded manuscript documents
├── production/cache/              # SQLite cache databases
├── scripts/                       # Operational scripts
│   ├── dashboard_server.py       # Flask API server (port 8421)
│   ├── generate_dashboard.py     # Static HTML dashboard generator
│   ├── send_digest.py            # Weekly editorial digest email
│   ├── weekly_run.sh             # Cron-triggered weekly extraction
│   ├── setup_gmail_oauth.py      # Gmail OAuth token refresh
│   └── admin/                    # LaunchAgent configs for auto-start
├── config/                        # Gmail OAuth tokens, journal configs
├── tests/                         # 703 tests (pytest)
├── run_extractors.py              # Extraction orchestrator
└── run_pipeline.py                # Pipeline + AE report CLI
```

---

## Event-Driven Pipeline

### Architecture

After each extraction, the system detects state changes and emits typed events:

1. **State Store** (`production/src/core/state_store.py`): SQLite DB at `production/cache/manuscript_state.db` tracks manuscript hashes
2. **Event Dispatcher** (`production/src/core/event_dispatcher.py`): Compares new extraction to stored state, emits events to `production/events/pending.jsonl`
3. **Event Processor** (`production/src/core/event_processor.py`): Reads pending events and dispatches actions

### Event Types

| Event | Trigger | Action |
|-------|---------|--------|
| `NEW_MANUSCRIPT` | First time a manuscript ID appears | Auto-run referee pipeline (desk rejection + candidate search) |
| `ALL_REPORTS_IN` | All assigned referees submitted reports | Auto-generate AE recommendation report |
| `STATUS_CHANGED` | New reports, acceptances, declines, or status change | Notification |

### How State Detection Works

1. Each manuscript is hashed: `SHA256(JSON(status + referees[name, status, dates, recommendation]))`
2. Hash stored in SQLite (`production/cache/manuscript_state.db`) keyed by `(journal, manuscript_id)`
3. On extraction, new hash compared to stored → if different, classify the change type
4. NEW_MANUSCRIPT: no prior entry exists
5. ALL_REPORTS_IN: all active (non-declined) referees have `returned` date or `report_submitted` status
6. STATUS_CHANGED: hash differs but doesn't match ALL_REPORTS_IN criteria

### Auto-Actions on Events

- **NEW_MANUSCRIPT** → `RefereePipeline.run_single(journal, ms_id)` — runs desk rejection assessment + referee candidate search. Output saved to `production/outputs/{journal}/recommendations/`
- **ALL_REPORTS_IN** → `ae_report.generate(journal, ms_id)` — assembles referee reports, calls Claude API (or copies prompt to clipboard). Output saved to `production/outputs/{journal}/ae_reports/`
- **STATUS_CHANGED** → macOS notification only (no auto-action)

### Quick Commands
```bash
# Events are auto-dispatched by run_extractors.py after extraction
# Manual processing:
PYTHONPATH=production/src python3 -c "from core.event_processor import process_all; process_all()"
```

---

## ML Pipeline & Referee Recommendation

### 5-Step Pipeline (`production/src/pipeline/referee_pipeline.py`)

For each manuscript awaiting referee assignment:
1. **Report Quality** → 6-dimension scoring (thoroughness, specificity, constructiveness, engagement, consistency, timeliness)
2. **Desk Rejection** → Heuristic signals + optional outcome predictor + optional LLM (Claude Sonnet)
3. **Referee Search** → FAISS expertise index + OpenAlex + Semantic Scholar + historical cross-journal + author-suggested
4. **Conflict Check** → Institution match, coauthorship, opposed list, editor overlap
5. **Ranking** → Weighted relevance score + track record bonuses:
   - `0.30 * topic_similarity` (FAISS cosine distance to manuscript abstract)
   - `0.25 * publication_similarity` (overlap in research keywords/topics)
   - `0.15 * seniority_score` (h-index normalized, capped at H_INDEX_CAP=50)
   - `0.15 * source_trust` (historical > OpenAlex > Semantic Scholar > author-suggested)
   - `0.15 * recency_score` (recent publications weighted higher)
   - Track record bonuses: journal-specific acceptance rate (+0.05), top-quartile quality (+0.03), trending quality (+0.02)
   - Penalties: overdue rate >0.5 (-0.05), chronic decliner (-0.10)

### 3 ML Models

| Model | File | Purpose | Features |
|-------|------|---------|----------|
| **Expertise Index** | `models/expertise_index.py` | FAISS semantic search over referee profiles | SPECTER2 embeddings of referee publications + topics |
| **Response Predictor** | `models/response_predictor.py` | P(accept) and P(complete\|accepted) | h-index, acceptance rate, past reviews, journal match, expertise similarity, turnaround, load, institution distance |
| **Outcome Predictor** | `models/outcome_predictor.py` | P(manuscript accepted) | Scope similarity, abstract length, keywords, author h-index, freemail, keyword overlap, article type |

### Embeddings (`production/src/pipeline/embeddings.py`)
- Primary: `allenai/specter2_base` (768-dim scientific embeddings)
- Fallback: `all-MiniLM-L6-v2` (384-dim)
- Fallback-fallback: TF-IDF (768-dim sklearn)

### Referee Performance DB (`production/src/pipeline/referee_db.py`)

SQLite database tracking referee behavior across all journals:

**Tables:**
- `referee_profiles`: Aggregated stats (acceptance rate, avg review days, quality, overdue rate, percentiles, trends)
- `referee_assignments`: Per-assignment tracking (dates, response, quality score, was_overdue)
- `referee_journal_stats`: Per-journal breakdown of referee performance

**Learning Features:**
- `overdue_count` / `overdue_rate`: tracks chronic lateness
- `quality_trend` / `response_trend`: last 5 values for detecting improvement/decline
- `percentile_response` / `percentile_quality` / `percentile_speed`: global ranking vs all referees
- `referee_journal_stats`: per-journal breakdown (a referee may accept for SICON but decline for MF)
- Feedback loop: `record_feedback(name, journal, ms_id, was_used, score)` tracks whether recommendations were followed

**Key Methods:** `get_track_record()`, `get_journal_stats()`, `search_referees()`, `get_overdue_repeat_offenders()`, `compute_percentiles()`, `get_quality_trend()`, `get_referee_assignments()`, `record_feedback()`

### AE Report Generation (`production/src/pipeline/ae_report.py`)

Assembles referee reports + manuscript data, generates AE recommendation via:
- **Claude API**: Direct API call (requires `ANTHROPIC_API_KEY`)
- **Clipboard**: Copies prompt for manual paste into ChatGPT Pro

Output: JSON + Markdown in `production/outputs/{journal}/ae_reports/`

### Quick Commands
```bash
# Run referee pipeline
python3 run_pipeline.py -j sicon --pending
python3 run_pipeline.py -j sicon -m M178221 --llm

# Train ML models
python3 run_pipeline.py --train
python3 run_pipeline.py --rebuild-index

# AE reports
python3 run_pipeline.py --ae-report -j sicon -m M178221
python3 run_pipeline.py --ae-auto
python3 run_pipeline.py --ae-list

# Feedback loop
python3 run_pipeline.py --record-outcome -j sicon -m M178221 --decision accept
python3 run_pipeline.py --feedback-stats

# Backfill referee DB
PYTHONPATH=production/src python3 production/src/pipeline/referee_db_backfill.py
```

---

## Dashboard

### Server (`scripts/dashboard_server.py`)
```bash
python3 scripts/dashboard_server.py          # Start on port 8421
python3 scripts/dashboard_server.py --port 9000
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve dashboard HTML |
| `/api/ae-report` | POST | Generate AE report `{journal, manuscript_id}` |
| `/api/ae-reports/<j>/<ms>` | GET | Retrieve saved AE report |
| `/api/ae-list` | GET | List manuscripts needing AE reports |
| `/api/refresh-dashboard` | POST | Regenerate dashboard HTML |
| `/api/run-extraction` | POST | Trigger extractor `{journal}` |
| `/api/referee/<name>` | GET | Referee profile + recent assignments |
| `/api/referee/search?q=` | GET | Search referees by name/email/institution |
| `/api/referee/<name>/assignments` | GET | Assignment history |
| `/api/referee/<name>/journal-stats` | GET | Per-journal stats |
| `/api/referee/top` | GET | Top performers |
| `/api/referee/decliners` | GET | Chronic decliners (>70% decline rate) |
| `/api/referee/overdue` | GET | Repeat overdue offenders |
| `/api/pipeline/run` | POST | Trigger referee pipeline `{journal, manuscript_id}` |
| `/api/pipeline/recommendations/<j>/<ms>` | GET | Get recommendation |
| `/api/manuscripts/search?q=` | GET | Search manuscripts by ID/title |
| `/api/events` | GET | List pending events |

### API Request/Response Examples

```bash
# Generate AE report
curl -X POST localhost:8421/api/ae-report -H 'Content-Type: application/json' \
  -d '{"journal":"sicon","manuscript_id":"M181987"}'
# → {"recommendation":"Minor Revision","confidence":0.85,"summary":"...","revision_points":[...]}

# Search referees
curl 'localhost:8421/api/referee/search?q=smith'
# → [{"referee_key":"smith_john","display_name":"John Smith","institution":"MIT",...}]

# Trigger pipeline
curl -X POST localhost:8421/api/pipeline/run -H 'Content-Type: application/json' \
  -d '{"journal":"sicon","manuscript_id":"M186000"}'
# → {"status":"started","journal":"sicon","manuscript_id":"M186000"}

# Search manuscripts
curl 'localhost:8421/api/manuscripts/search?q=stochastic'
# → [{"journal":"SICON","manuscript_id":"M181987","title":"...","status":"Under Review"}]
```

All error responses: `{"error": "message"}` with appropriate HTTP status code (400/404/500).

### Dashboard Features (`scripts/generate_dashboard.py`)
- Alert bar (critical/high priority action items)
- Action items with priority + journal filters
- Manuscript search across all journals
- Active manuscripts with expandable referee details
- Clickable referee names → track record overlay card
- Per-manuscript desk rejection + recommended referees display
- Inline AE report panel (recommendation badge, confidence, revision points, consensus)
- "Find Referees" and "Generate AE Report" buttons
- Referee Intelligence section (top performers, chronic decliners, overdue offenders)
- Pipeline Recommendations display
- Journal Overview with freshness indicators
- Model Health (collapsed)
- Dark mode support

---

## Extractor Operational Reference

### Platform Groups

| Platform | Journals | Base Class | WebDriver | Auth Method |
|----------|----------|------------|-----------|-------------|
| **ScholarOne** | MF, MOR | `ScholarOneBaseExtractor` | `undetected_chromedriver` | Email/password + Gmail 2FA |
| **Editorial Manager** | JOTA, MAFE | `EMExtractor` | `undetected_chromedriver` | Username/password, role switch |
| **SIAM** | SICON, SIFIN | `SIAMExtractor` | `undetected_chromedriver` | ORCID OAuth, Cloudflare challenge |
| **EditFlow (MSP)** | NACO | standalone | `webdriver-manager` | Username/password (NOT email) |
| **Gmail API** | FS | standalone | None (API only) | OAuth 2.0 token |

### CRITICAL: Cloudflare Bot Protection (ScholarOne + SIAM)

All four extractors (MF, MOR, SICON, SIFIN) run in **off-screen headful mode** with AppleScript window minimization.

**Chrome 146+ compatibility**: `--no-sandbox` and `plugins.always_open_pdf_externally` crash headful UC. Both removed. Window positioned at (-2000,0) via startup arg.

```bash
# ScholarOne (always headful)
PYTHONUNBUFFERED=1 python3 production/src/extractors/mf_extractor.py
PYTHONUNBUFFERED=1 python3 production/src/extractors/mor_extractor.py

# SIAM (must set headful)
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 production/src/extractors/sicon_extractor.py
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 production/src/extractors/sifin_extractor.py
```

### CRITICAL: NACO Uses Username, NOT Email
- Env vars: `NACO_USERNAME`, `NACO_PASSWORD`

### CRITICAL: MOR Uses EMAIL, NOT USERNAME
- Env vars: `MOR_EMAIL`, `MOR_PASSWORD`

---

## Environment Variables

### Credential Env Vars
```bash
MF_EMAIL, MF_PASSWORD                    # ScholarOne
MOR_EMAIL, MOR_PASSWORD                  # ScholarOne
JOTA_USERNAME, JOTA_PASSWORD             # Editorial Manager
MAFE_USERNAME, MAFE_PASSWORD             # Editorial Manager
SICON_EMAIL, SICON_PASSWORD              # SIAM (ORCID)
SIFIN_EMAIL, SIFIN_PASSWORD              # SIAM (ORCID)
NACO_USERNAME, NACO_PASSWORD             # EditFlow (username, NOT email)
ANTHROPIC_API_KEY                        # For Claude API AE reports (optional)
# Gmail: OAuth token at config/gmail_token.json
```

### Runtime Env Vars
```bash
EXTRACTOR_HEADLESS=false  # Required for SICON/SIFIN (Cloudflare)
PYTHONUNBUFFERED=1        # Always set for real-time output
PYTHONPATH=production/src # Required for standalone script execution
```

---

## Quick Commands

```bash
# Extractors
python3 run_extractors.py --status
python3 run_extractors.py --journal mf
python3 run_extractors.py --all

# Pipeline
python3 run_pipeline.py -j sicon --pending
python3 run_pipeline.py --ae-auto
python3 run_pipeline.py --train

# Dashboard
python3 scripts/dashboard_server.py
PYTHONPATH=production/src python3 scripts/generate_dashboard.py

# Referee DB
PYTHONPATH=production/src python3 production/src/pipeline/referee_db_backfill.py

# Tests
python3 -m pytest tests/ -q

# Credentials
python3 verify_all_credentials.py
```

---

## Troubleshooting

### ChromeDriver Quarantine (macOS)
After `kill -9 chromedriver`, binary gets quarantined. Fix:
```bash
rm -f ~/Library/Application\ Support/undetected_chromedriver/undetected_chromedriver
# UC re-downloads on next run
```

### Chrome 146+ Headful Crash
`--no-sandbox` and `plugins.always_open_pdf_externally` cause instant `NoSuchWindowException` in headful mode. Both already removed from all base classes.

### undetected_chromedriver Binary Contention
Cannot run two UC-based extractors simultaneously. Run sequentially.

### NEVER Kill Google Chrome
```bash
pkill -9 chromedriver          # OK
# pkill "Google Chrome"        # NEVER — kills Dylan's personal browser
```

### Gmail OAuth Token Expired
```bash
python3 scripts/setup_gmail_oauth.py
```

---

## Common Bug Patterns

- `self.self.` double references and `self.safe_array_access(tr, 1)` in XPath — always grep
- `set -eo pipefail` kills on `grep` no match — append `|| true`
- Python 3.12+ local `import re` shadows global `re` → `UnboundLocalError`
- ScholarOne iframe: `driver.back()` resets to `default_content`
- `threading.Lock()` is NOT reentrant — use `threading.RLock()`
- Never mutate timeline events with datetime objects — `json.dumps` needs `default=str`
- Pre-commit: `bandit -ll`, `pip-audit`, MD5 needs `usedforsecurity=False`
- Black reformats on commit — always re-stage after failed commit
- EM split tables: pair `fr0`/`nfr0` by `data-rowindex`, use `lxml` parser

---

## Testing

703 tests across 13 test modules:
```bash
python3 -m pytest tests/ -q                    # All tests
python3 -m pytest tests/test_referee_db.py -v  # Specific module
```

---

## AI Assistant Notes

- **User prefers**: Action over analysis, concise responses, dashboard over CLI
- **Code style**: No comments unless requested
- **Testing**: Always use `dev/` directory for experiments
- **Production**: Handle with care - it works!
- **Process kills**: ONLY kill `chromedriver`, NEVER kill `Google Chrome`
- **Python**: Use `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12` (system python3 is 3.9)

---

**Last Updated**: 2026-03-25
