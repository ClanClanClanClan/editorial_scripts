# Editorial Scripts

End-to-end editorial management system for 8 academic journals. Extracts referee reports, manuscripts, and metadata; detects state changes; recommends referees via ML pipeline; generates AE decision reports; serves an interactive dashboard.

## Current Status (March 2026)

| Journal | Code | Platform | Extractor | Status |
|---------|------|----------|-----------|--------|
| Mathematical Finance | MF | ScholarOne | `ComprehensiveMFExtractor` | **WORKING** |
| Mathematics of Operations Research | MOR | ScholarOne | `MORExtractor` | **WORKING** |
| Finance and Stochastics | FS | Gmail API | `ComprehensiveFSExtractor` | **WORKING** |
| J. Optimization Theory & Applications | JOTA | Editorial Manager | `JOTAExtractor` | **WORKING** |
| Mathematical & Financial Economics | MAFE | Editorial Manager | `MAFEExtractor` | **WORKING** |
| SIAM J. Control & Optimization | SICON | SIAM | `SICONExtractor` | **WORKING** |
| SIAM J. Financial Mathematics | SIFIN | SIAM | `SIFINExtractor` | **WORKING** |
| Numerical Algorithms & Computation | NACO | EditFlow/MSP | `NACOExtractor` | **WORKING** |

682 tests passing. Python 3.12 required.

## Quick Start

```bash
# Verify credentials (stored in macOS Keychain)
python3 verify_all_credentials.py

# Run extractors
python3 run_extractors.py --status
python3 run_extractors.py --journal mf
python3 run_extractors.py --all

# Referee pipeline
python3 run_pipeline.py -j sicon --pending
python3 run_pipeline.py --ae-auto

# Dashboard
python3 scripts/dashboard_server.py   # http://localhost:8421
```

## Architecture

```
Extractors (8 journals) → JSON outputs
    ↓
State Store → Event Dispatcher (NEW_MANUSCRIPT, ALL_REPORTS_IN, STATUS_CHANGED)
    ↓
Event Processor → Referee Pipeline (desk rejection + candidate search)
                → AE Report Generator (Claude API / clipboard)
    ↓
Dashboard Server (Flask :8421) → Interactive HTML dashboard
```

## Key Components

- **Extractors** (`production/src/extractors/`): Selenium WebDriver + Gmail API extraction
- **Event System** (`production/src/core/`): State change detection, typed events, auto-actions
- **ML Pipeline** (`production/src/pipeline/`): 3 models (expertise FAISS index, response predictor, outcome predictor), desk rejection, referee finding, conflict checking
- **Referee DB** (`production/src/pipeline/referee_db.py`): SQLite performance tracking with learning (acceptance rates, quality trends, percentiles)
- **AE Reports** (`production/src/pipeline/ae_report.py`): Assembles referee reports, generates recommendations via Claude API
- **Dashboard** (`scripts/dashboard_server.py`): Flask server with 18 API endpoints, referee intelligence, inline AE reports

## Documentation

See `CLAUDE.md` for comprehensive operational reference including all commands, API endpoints, troubleshooting, and architecture details.
