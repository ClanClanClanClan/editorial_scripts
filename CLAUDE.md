# CLAUDE.md - Editorial Scripts AI Assistant Guide

## CRITICAL: CREDENTIALS ARE ALREADY STORED
**DO NOT ASK FOR CREDENTIALS - They are permanently stored in macOS Keychain**
- **Test with:** `python3 verify_all_credentials.py`
- **Auto-loaded via:** `~/.zshrc` -> `~/.editorial_scripts/load_all_credentials.sh`

---

## Project Overview

Dylan Possamai's manuscript extraction system for 8 academic journals.
- **Purpose**: Extract referee reports, manuscripts, and metadata
- **Architecture**: Selenium WebDriver + Gmail API
- **Status**: 8 extractors working (MF, MOR, FS, JOTA, MAFE, SICON, SIFIN, NACO)

### Project Structure
```
editorial_scripts/
├── production/src/extractors/     # ALL WORKING CODE HERE
│   ├── mf_extractor.py           # MF - ScholarOne (ComprehensiveMFExtractor)
│   ├── mor_extractor.py          # MOR - ScholarOne (MORExtractor)
│   ├── fs_extractor.py           # FS - Gmail API (ComprehensiveFSExtractor)
│   ├── jota_extractor.py         # JOTA - Editorial Manager (JOTAExtractor)
│   ├── mafe_extractor.py         # MAFE - Editorial Manager (MAFEExtractor)
│   ├── sicon_extractor.py        # SICON - SIAM (SICONExtractor)
│   ├── sifin_extractor.py        # SIFIN - SIAM (SIFINExtractor)
│   ├── naco_extractor.py         # NACO - EditFlow/MSP (NACOExtractor)
│   └── generate_fs_timeline_report.py  # FS utility
├── production/src/core/           # Shared utilities
│   ├── scholarone_base.py        # ScholarOne base class (MF, MOR)
│   ├── em_base.py                # Editorial Manager base class (JOTA, MAFE)
│   ├── siam_base.py              # SIAM base class (SICON, SIFIN)
│   ├── cache_manager.py          # SQLite persistent cache
│   ├── cache_integration.py      # CachedExtractorMixin
│   ├── gmail_search.py           # Gmail timeline integration
│   └── gmail_verification.py     # 2FA code fetching
├── production/src/pipeline/       # Referee recommendation pipeline
│   ├── referee_pipeline.py       # Orchestrator
│   ├── desk_rejection.py         # Desk-rejection heuristics + optional LLM
│   ├── referee_finder.py         # Candidate sourcing (OpenAlex, S2, historical)
│   └── conflict_checker.py       # Conflict detection
├── production/outputs/            # Extraction JSON results
│   ├── mf/                       # MF outputs
│   ├── mor/                      # MOR outputs
│   ├── jota/                     # JOTA outputs
│   ├── mafe/                     # MAFE outputs
│   ├── sicon/                    # SICON outputs
│   ├── sifin/                    # SIFIN outputs
│   └── naco/                     # NACO outputs
├── production/downloads/          # Downloaded documents
│   ├── mf/                       # MF documents
│   ├── mor/                      # MOR documents
│   ├── jota/                     # JOTA documents
│   └── mafe/                     # MAFE documents
├── production/cache/              # SQLite cache databases
├── config/                        # Gmail OAuth tokens, journal configs
├── archive/                       # Legacy code + skeleton extractors
├── dev/                           # Development/testing sandbox
├── docs/                          # Documentation
├── tests/                         # Test suite
├── run_extractors.py              # Orchestrator for all extractors
└── run_pipeline.py                # Referee recommendation CLI
```

---

## Extractor Operational Reference

### Platform Groups

| Platform | Journals | Base Class | WebDriver | Auth Method |
|----------|----------|------------|-----------|-------------|
| **ScholarOne** | MF, MOR | `ScholarOneBaseExtractor` | `webdriver-manager` | Email/password + Gmail 2FA |
| **Editorial Manager** | JOTA, MAFE | `EMExtractor` | `undetected_chromedriver` | Username/password, role switch |
| **SIAM** | SICON, SIFIN | `SIAMExtractor` | `undetected_chromedriver` | ORCID OAuth, Cloudflare challenge |
| **EditFlow (MSP)** | NACO | standalone | `webdriver-manager` | Username/password (NOT email) |
| **Gmail API** | FS | standalone | None (API only) | OAuth 2.0 token |

### Per-Extractor Details

| Detail | MF | MOR | FS | JOTA | MAFE | SICON | SIFIN | NACO |
|--------|----|----|-----|------|------|-------|-------|------|
| **Login URL** | mc.manuscriptcentral.com/mafi | mc.manuscriptcentral.com/mathor | N/A (API) | editorialmanager.com/jota | editorialmanager.com/mafe | sicon.siam.org | sifin.siam.org | ef.msp.org/login.php |
| **Cred env vars** | `MF_EMAIL` `MF_PASSWORD` | `MOR_EMAIL` `MOR_PASSWORD` | OAuth token | `JOTA_USERNAME` `JOTA_PASSWORD` | `MAFE_USERNAME` `MAFE_PASSWORD` | `SICON_EMAIL` `SICON_PASSWORD` | `SIFIN_EMAIL` `SIFIN_PASSWORD` | `NACO_USERNAME` `NACO_PASSWORD` |
| **2FA** | Gmail code | Gmail code | N/A | None | None | ORCID SSO | ORCID SSO | None |
| **Cloudflare** | No | No | No | No | No | **Yes (180s)** | **Yes (180s)** | No |
| **Downloads** | Yes | Yes | No | Yes | Yes | Yes | Yes | No |
| **Headless default** | Yes | Yes | N/A | Yes | Yes | Yes | Yes | Yes (always) |

### CRITICAL: Running SIAM Extractors (SICON, SIFIN)

SIAM sites use Cloudflare bot detection. These extractors **MUST** run in headful mode:

```bash
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 production/src/extractors/sicon_extractor.py
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 production/src/extractors/sifin_extractor.py
```

**What happens in headful mode:**
1. Browser window opens off-screen at position (-2000, 0) — invisible to you
2. Cloudflare challenge resolves automatically (up to 180s)
3. Window auto-minimizes after dashboard loads
4. You are NOT disturbed — do NOT kill the window

**What goes wrong in headless mode:** Cloudflare blocks headless Chrome. The extractor hangs for 180s then times out.

### CRITICAL: NACO Uses Username, NOT Email

NACO (EditFlow/MSP) authenticates with a **username**, not an email address:
- Env vars: `NACO_USERNAME`, `NACO_PASSWORD`
- Login field: `id="login"` (username field, not email)

### CRITICAL: MOR Uses EMAIL, NOT USERNAME

MOR env vars are `MOR_EMAIL` and `MOR_PASSWORD` (not `MOR_USERNAME`).

---

## Environment Variables

### EXTRACTOR_HEADLESS

Controls browser visibility. Read by all Selenium-based extractors.

```bash
EXTRACTOR_HEADLESS=true   # Default. Headless (invisible) browser.
EXTRACTOR_HEADLESS=false  # Headful. Required for SICON/SIFIN (Cloudflare).
```

**Which extractors need headful mode:**
- **SICON, SIFIN**: MUST be headful (`EXTRACTOR_HEADLESS=false`) — Cloudflare blocks headless
- **All others**: Can run headless (default)
- **FS**: No browser at all (Gmail API)
- **NACO**: Always headless (env var not checked)

### PYTHONUNBUFFERED

Always set when running extractors to see real-time output:
```bash
PYTHONUNBUFFERED=1 python3 extractor.py
```

### Credential Env Vars (Complete List)

```bash
# ScholarOne
MF_EMAIL, MF_PASSWORD
MOR_EMAIL, MOR_PASSWORD

# Editorial Manager (tries USERNAME first, then EMAIL)
JOTA_USERNAME, JOTA_PASSWORD    # or JOTA_EMAIL
MAFE_USERNAME, MAFE_PASSWORD    # or MAFE_EMAIL

# SIAM (ORCID credentials)
SICON_EMAIL, SICON_PASSWORD
SIFIN_EMAIL, SIFIN_PASSWORD

# EditFlow
NACO_USERNAME, NACO_PASSWORD    # USERNAME, not EMAIL

# Gmail API
# No env vars — uses OAuth token at config/gmail_token.json
```

---

## Credentials & Authentication

### NEVER ASK FOR CREDENTIALS - They're Already Stored!

**Storage Locations:**
1. **macOS Keychain** (primary, encrypted)
   - Service names: `editorial-scripts-{journal}`
   - Persistent forever, survives reboots

2. **Shell Environment**
   - Auto-loads via: `~/.zshrc` -> `~/.editorial_scripts/load_all_credentials.sh`

**Verification:**
```bash
python3 verify_all_credentials.py
source ~/.editorial_scripts/load_all_credentials.sh
```

---

## Quick Commands

```bash
# Verify credentials
python3 verify_all_credentials.py

# Run production extractors (from project root)
cd production/src/extractors

# ScholarOne (headless OK)
PYTHONUNBUFFERED=1 python3 mf_extractor.py
PYTHONUNBUFFERED=1 python3 mor_extractor.py

# Gmail API (no browser)
PYTHONUNBUFFERED=1 python3 fs_extractor.py

# Editorial Manager (headless OK)
PYTHONUNBUFFERED=1 python3 jota_extractor.py
PYTHONUNBUFFERED=1 python3 mafe_extractor.py

# SIAM (MUST be headful)
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 sicon_extractor.py
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 sifin_extractor.py

# EditFlow (always headless)
PYTHONUNBUFFERED=1 python3 naco_extractor.py

# Orchestrator
python3 run_extractors.py --status      # Show all extractor status
python3 run_extractors.py --journal mf  # Run specific extractor
python3 run_extractors.py --all         # Run all working extractors

# Referee recommendation pipeline
python3 run_pipeline.py --journal sicon --pending
python3 run_pipeline.py --journal sicon --manuscript M183494
python3 run_pipeline.py --journal sicon --manuscript M183494 --llm

# Development testing (isolated)
cd dev/mf
python3 run_mf_dev.py  # All outputs in dev/mf/
```

---

## Browser & Driver Setup

### WebDriver Types

| Driver | Used By | Manager | Binary Location |
|--------|---------|---------|-----------------|
| `webdriver-manager` | MF, MOR, NACO | Auto-downloads matching ChromeDriver | `~/.wdm/drivers/chromedriver/` |
| `undetected_chromedriver` | JOTA, MAFE, SICON, SIFIN | Patches ChromeDriver to evade detection | `~/Library/Application Support/undetected_chromedriver/` |

### Bot Detection Evasion

**ScholarOne + NACO** (webdriver-manager):
- CDP webdriver spoofing (`navigator.webdriver = undefined`)
- `--disable-blink-features=AutomationControlled`
- `excludeSwitches=["enable-automation"]`, `useAutomationExtension=False`
- Custom user-agent string

**EM + SIAM** (undetected_chromedriver):
- Built-in evasion (patched ChromeDriver binary)
- Auto Chrome version detection via subprocess
- No explicit user-agent override needed

### Window Behavior (Headful Mode)

When `EXTRACTOR_HEADLESS=false`:
- **EM (JOTA, MAFE)**: Window opens at (-2000, 0) off-screen, sized 1400x900
- **SIAM (SICON, SIFIN)**: Window opens at (-2000, 0) off-screen, sized 1200x800, auto-minimizes after dashboard load
- **ScholarOne (MF, MOR)**: Not designed for headful — use headless

---

## Troubleshooting

### ChromeDriver Quarantine (macOS)

**Symptom**: Chrome crashes immediately — "no such window: target window already closed"

**Cause**: After `kill -9 chromedriver`, macOS quarantine attributes corrupt the binary.

**Fix for undetected_chromedriver (JOTA, MAFE, SICON, SIFIN):**
```bash
xattr -c ~/Library/Application\ Support/undetected_chromedriver/undetected_chromedriver
```

**Fix for webdriver-manager (MF, MOR, NACO):**
```bash
rm -rf ~/.wdm/drivers/chromedriver/
# webdriver-manager re-downloads on next run
```

### Cloudflare Timeout (SICON, SIFIN)

**Symptom**: "Cloudflare challenge..." prints every 15s for 180s, then times out.

**Cause**: Running in headless mode. Cloudflare blocks headless Chrome.

**Fix**:
```bash
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 sicon_extractor.py
```

### Gmail OAuth Token Expired

**Symptom**: FS extractor fails; MF/MOR 2FA code fetch fails; Gmail audit trail unavailable.

**Fix**:
```bash
python3 scripts/setup_gmail_oauth.py
```
Token saved to `config/gmail_token.json`. Has limited lifetime (weeks/months).

### Session Death / Connection Drops

All Selenium extractors detect session death via keyword matching:
`"connection refused"`, `"invalid session"`, `"no such window"`, `"chrome not reachable"`, `"target window already closed"`

Recovery is automatic: cleanup → sleep → new driver → re-login.

### NEVER Kill Google Chrome

```bash
pkill -9 chromedriver          # OK — kills chromedriver processes only
# pkill "Google Chrome"        # NEVER — kills Dylan's personal browser
```

### undetected_chromedriver Binary Contention

Running two extractors that use `undetected_chromedriver` simultaneously causes binary contention. Run EM/SIAM extractors sequentially.

### EM Split Tables (JOTA, MAFE)

Editorial Manager "Final Disposition" uses Knockout.js with split fixed/nonfixed tables. Fixed rows (`fr0`) have action links, nonfixed rows (`nfr0`) have data. Must pair by `data-rowindex`. Must use `lxml` HTML parser — `html.parser` nests unclosed `<td>` tags incorrectly.

### Python Output Not Appearing

Always run with `PYTHONUNBUFFERED=1` to disable output buffering:
```bash
PYTHONUNBUFFERED=1 python3 extractor.py
```

---

## Development Rules

### ALWAYS USE dev/ FOR TESTING
```bash
cd dev/mf
python3 run_mf_dev.py  # All outputs contained in dev/mf/
```

**NEVER CREATE:**
- Test files in project root
- Debug files outside dev/
- Temporary scripts outside dev/

---

## Key Features

- **3-Pass Extraction** (MF): Forward -> Backward -> Forward
- **6-Pass Extraction** (MOR): Referees, authors, metadata, docs, history, audit
- **5-Phase Extraction** (JOTA, MAFE): Details, enrichment, reports, documents, Gmail
- **Web Enrichment**: ORCID API + CrossRef API + OpenAlex + Semantic Scholar
- **Gmail Integration**: 2FA codes + FS email extraction + audit trail cross-checking
- **Session Recovery**: Automatic re-login on connection drops
- **Document Downloads**: Manuscript PDFs, cover letters, original files, author responses (with redirect detection)
- **SQLite Caching**: Persistent referee/manuscript cache across runs
- **Auto ChromeDriver**: webdriver-manager / undetected_chromedriver handles version matching
- **Structured Output**: JSON with metadata wrapper in `production/outputs/{journal}/`
- **Referee Pipeline**: Desk-rejection assessment + candidate sourcing + conflict checking

---

## Common Bug Patterns

- `self.self.` double references and `self.safe_array_access(tr, 1)` injected into XPath strings — always grep when reviewing code
- `set -eo pipefail` in shell scripts kills on `grep` returning no matches — append `|| true`
- Python 3.12+ stricter scope: local `import re` inside a function shadows global `re` → `UnboundLocalError`
- ScholarOne iframe context: `driver.back()` resets to `default_content`, losing iframe context. MOR fix: re-open category from AE center
- FS cache save can hang (`threading.Lock` or large `json.dumps`). JSON file saved FIRST, cache secondary with 30s timeout
- `threading.Lock()` is NOT reentrant — use `threading.RLock()` for methods that call each other
- Never mutate timeline events with datetime objects — use a local dict keyed by index. `json.dumps` needs `default=str`
- Pre-commit hooks: security scan targets `production/src`, uses `bandit -ll` and `pip-audit`. MD5 for cache keys needs `usedforsecurity=False`
- Black reformats on commit — always re-stage after failed commit

---

## AI Assistant Notes

- **User prefers**: Action over analysis, concise responses
- **Code style**: No comments unless requested
- **Testing**: Always use `dev/` directory
- **Production**: Handle with care - it works!
- **Process kills**: ONLY kill `chromedriver`, NEVER kill `Google Chrome`

---

**Last Updated**: 2026-02-23
