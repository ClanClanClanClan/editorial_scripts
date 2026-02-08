# Editorial Manuscript Extractors

Production extractors for academic journal manuscript data.

## Extractors

| File | Journal | Platform | Class | Status |
|------|---------|----------|-------|--------|
| `mf_extractor.py` | Mathematical Finance | ScholarOne | `ComprehensiveMFExtractor` | WORKING |
| `mor_extractor.py` | Mathematics of Operations Research | ScholarOne | `MORExtractor` | WORKING |
| `fs_extractor.py` | Finance and Stochastics | Gmail API | `ComprehensiveFSExtractor` | WORKING |
| `generate_fs_timeline_report.py` | FS utility | - | - | WORKING |

## Quick Start

```bash
cd production/src/extractors
python3 mor_extractor.py  # MOR extraction
python3 mf_extractor.py   # MF extraction
python3 fs_extractor.py   # FS extraction
```

## Prerequisites

- Python 3.11+
- `selenium`, `beautifulsoup4`, `webdriver-manager`, `python-dotenv`
- Google Chrome installed
- Credentials loaded via `source ~/.editorial_scripts/load_all_credentials.sh`
- Gmail OAuth token at `config/gmail_token.json` (for 2FA)

## Output

JSON files in `production/outputs/{journal}/` with manuscripts, referees, authors, metadata, and audit trails.

## 5 skeleton extractors (JOTA, MAFE, SICON, SIFIN, NACO) are in `archive/production_legacy_20251004/`.

---

**Last Updated:** 2026-02-08
