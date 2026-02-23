# Editorial Scripts

Manuscript extraction system for 8 academic journals. Extracts referee reports, manuscripts, author/referee profiles, audit trails, and documents from editorial platforms.

## Current Status (February 2026)

| Journal | Code | Platform | Extractor | Status |
|---------|------|----------|-----------|--------|
| Mathematical Finance | MF | ScholarOne | `ComprehensiveMFExtractor` | **WORKING** |
| Mathematics of Operations Research | MOR | ScholarOne | `MORExtractor` | **WORKING** |
| Finance and Stochastics | FS | Gmail API | `ComprehensiveFSExtractor` | **WORKING** |
| JOTA | JOTA | Editorial Manager | — | Skeleton |
| MAFE | MAFE | Editorial Manager | — | Skeleton |
| SICON | SICON | SIAM | — | Skeleton |
| SIFIN | SIFIN | SIAM | — | Skeleton |
| NACO | NACO | AIMS Sciences | — | Skeleton |

## Quick Start

```bash
# Verify credentials (stored in macOS Keychain)
python3 verify_all_credentials.py

# Run extractors
cd production/src/extractors
python3 mf_extractor.py
python3 mor_extractor.py
python3 fs_extractor.py

# Orchestrator
python3 run_extractors.py --status
python3 run_extractors.py --journal mf
python3 run_extractors.py --all
```

## Project Structure

```
editorial_scripts/
├── production/src/extractors/     # ALL WORKING CODE
│   ├── mf_extractor.py           # MF - ScholarOne
│   ├── mor_extractor.py          # MOR - ScholarOne
│   └── fs_extractor.py           # FS - Gmail API
├── production/src/core/           # Shared utilities
│   ├── cache_manager.py          # SQLite persistent cache
│   ├── gmail_search.py           # Gmail timeline integration
│   └── gmail_verification.py     # 2FA code fetching
├── production/outputs/            # Extraction JSON results
│   ├── mf/                       # MF outputs
│   └── mor/                      # MOR outputs
├── production/downloads/          # Downloaded documents
│   ├── mf/                       # MF documents
│   └── mor/                      # MOR documents
├── config/                        # Gmail OAuth tokens, journal configs
├── archive/                       # Legacy code + skeleton extractors
├── dev/                           # Development/testing sandbox
├── docs/                          # Documentation & specifications
├── run_extractors.py              # Orchestrator
└── verify_all_credentials.py      # Credential verification
```

## Key Features

- **Multi-pass extraction**: Forward → Backward → Forward navigation (MF: 3-pass, MOR: 6-pass)
- **Web enrichment**: ORCID API + CrossRef API for author/referee publication profiles
- **Gmail integration**: 2FA code fetching + audit trail cross-checking with external emails
- **Session recovery**: Automatic re-login on connection drops
- **Document downloads**: Manuscript PDFs, cover letters, original files, author responses
- **SQLite caching**: Persistent referee/manuscript cache across runs
- **Auto ChromeDriver**: webdriver-manager handles version matching

## Credentials

All credentials are permanently stored in macOS Keychain. Never hardcode them.

```bash
python3 verify_all_credentials.py
source ~/.editorial_scripts/load_all_credentials.sh
```

## Development

Always use `dev/` for testing. Never create test files in project root or production.

```bash
cd dev/mf
python3 run_mf_dev.py
```

## Documentation

- `CLAUDE.md` — AI assistant guide
- `docs/specifications/` — Target architecture and vision
- `docs/extractors/` — Per-extractor documentation
- `docs/workflows/` — Extraction workflows
