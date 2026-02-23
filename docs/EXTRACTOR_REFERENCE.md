# Extractor Operational Reference

Complete operational details for all 8 extractors grouped by platform.

---

## 1. ScholarOne — MF, MOR

**Base class**: `ScholarOneBaseExtractor` in `production/src/core/scholarone_base.py`
**WebDriver**: `webdriver-manager` (selenium.webdriver.Chrome)

### MF — Mathematical Finance

| Field | Value |
|-------|-------|
| Class | `ComprehensiveMFExtractor` |
| File | `production/src/extractors/mf_extractor.py` |
| Login URL | `https://mc.manuscriptcentral.com/mafi` |
| Credentials | `MF_EMAIL`, `MF_PASSWORD` |
| 2FA | Gmail 6-digit code via `fetch_latest_verification_code()`, manual fallback |
| Extraction | 3-pass: Forward → Backward → Forward |
| Output | `production/outputs/mf/` |
| Downloads | `production/downloads/mf/` |
| Window | 800x600, headless only |

### MOR — Mathematics of Operations Research

| Field | Value |
|-------|-------|
| Class | `MORExtractor` |
| File | `production/src/extractors/mor_extractor.py` |
| Login URL | `https://mc.manuscriptcentral.com/mathor` |
| Credentials | `MOR_EMAIL`, `MOR_PASSWORD` (NOT `MOR_USERNAME`) |
| 2FA | Gmail 6-digit code, same as MF |
| Extraction | 6-pass: Referees, authors, metadata, docs, history, audit |
| Output | `production/outputs/mor/` |
| Downloads | `production/downloads/mor/` |
| Window | 800x600, headless only |

### ScholarOne Shared Behavior

- **Bot evasion**: CDP webdriver spoofing, `--disable-blink-features=AutomationControlled`, `excludeSwitches=["enable-automation"]`, custom user-agent
- **Login flow**: Navigate → reject OneTrust cookies → enter email/password → handle 2FA → verify "Associate Editor Center" link
- **Session recovery**: Detects dead session via keyword matching, auto re-login
- **iframe pitfall**: `driver.back()` resets to `default_content`. MOR re-opens category from AE center instead.
- **Email extraction**: MOR extracts from page HTML to avoid ChromeDriver popup crashes. MF uses frameset popup handling.
- **Enrichment**: ORCID API + CrossRef API for author/referee web profiles
- **Gmail integration**: 2FA code fetch + audit trail cross-check + author email backfill

---

## 2. Editorial Manager — JOTA, MAFE

**Base class**: `EMExtractor` in `production/src/core/em_base.py`
**WebDriver**: `undetected_chromedriver`

### JOTA — Journal of Optimization Theory and Applications

| Field | Value |
|-------|-------|
| Class | `JOTAExtractor` |
| File | `production/src/extractors/jota_extractor.py` |
| Login URL | `https://www.editorialmanager.com/jota/default.aspx` |
| Credentials | `JOTA_USERNAME` (or `JOTA_EMAIL`), `JOTA_PASSWORD` |
| 2FA | None |
| Extraction | 5-phase: Details, enrichment, reports, documents, Gmail |
| Output | `production/outputs/jota/` |
| Downloads | `production/downloads/jota/` |

### MAFE — Mathematical and Financial Economics

| Field | Value |
|-------|-------|
| Class | `MAFEExtractor` |
| File | `production/src/extractors/mafe_extractor.py` |
| Login URL | `https://www.editorialmanager.com/mafe/default.aspx` |
| Alt URL | `https://www2.cloud.editorialmanager.com/mafe/default2.aspx` |
| Credentials | `MAFE_USERNAME` (or `MAFE_EMAIL`), `MAFE_PASSWORD` |
| 2FA | None |
| Extraction | 5-phase, same as JOTA |
| Output | `production/outputs/mafe/` |
| Downloads | `production/downloads/mafe/` |

### EM Shared Behavior

- **Driver setup**: Auto-detects Chrome version via subprocess, creates `uc.Chrome(version_main=...)`. Off-screen at (-2000, 0) when headful.
- **Login flow**: Navigate → switch to "content" iframe → switch to "login" iframe → enter credentials → click login → wait 8s → verify "Logout" in page → switch to editor role via `RoleDropdown` JavaScript
- **MAFE fallback**: Tries ALT_URL if primary fails
- **Frame management**: `switch_to_content_frame()` / `switch_to_default()` with `_in_content_frame` state tracking
- **Split tables**: Final Disposition uses Knockout.js with fixed rows (`fr0`, action links) and nonfixed rows (`nfr0`, data). Pair by `data-rowindex`.
- **Column mapping**: Use `data-uniquename` attributes from `colresize-row` header. Column order varies between journals (MAFE has extra "Section" column).
- **HTML parser**: MUST use `lxml`, not `html.parser` (nests unclosed `<td>` tags incorrectly)
- **File inventory**: `PopupFileInventoryWindow` (Final Disposition) is defined in the content iframe, NOT the top frame. Run file inventory LAST after all other popup operations.
- **Document downloads**: JS fetch → Base64 pipeline for reviewer attachments
- **Enrichment**: ORCID + CrossRef via `academic_apis.py`
- **Binary contention**: Two `undetected_chromedriver` instances fighting over the patched binary. Run EM extractors sequentially.

---

## 3. SIAM — SICON, SIFIN

**Base class**: `SIAMExtractor` in `production/src/core/siam_base.py`
**WebDriver**: `undetected_chromedriver`

### SICON — SIAM Journal on Control and Optimization

| Field | Value |
|-------|-------|
| Class | `SICONExtractor` |
| File | `production/src/extractors/sicon_extractor.py` |
| Base URL | `https://sicon.siam.org` |
| Credentials | `SICON_EMAIL`, `SICON_PASSWORD` (ORCID account) |
| Auth | ORCID OAuth login |
| Cloudflare | Yes — 180s timeout, polls every 1s |
| Output | `production/outputs/sicon/` |
| Downloads | `production/downloads/sicon/` |

### SIFIN — SIAM Journal on Financial Mathematics

| Field | Value |
|-------|-------|
| Class | `SIFINExtractor` |
| File | `production/src/extractors/sifin_extractor.py` |
| Base URL | `https://sifin.siam.org` |
| Credentials | `SIFIN_EMAIL`, `SIFIN_PASSWORD` (ORCID account) |
| Auth | ORCID OAuth login |
| Cloudflare | Yes — 180s timeout |
| Output | `production/outputs/sifin/` |
| Downloads | `production/downloads/sifin/` |

### SIAM Shared Behavior

- **MUST run headful**: `EXTRACTOR_HEADLESS=false`. Cloudflare blocks headless Chrome.
- **Window**: Opens at (-2000, 0) off-screen, sized 1200x800, auto-minimizes after dashboard load. Does NOT disturb the user.
- **Cloudflare handling**: `_wait_for_cloudflare()` polls page title until it's no longer "just a moment". Prints status every 15s.
- **ORCID login flow**: Navigate to SIAM site → wait for Cloudflare → if not logged in, redirect to ORCID → enter email/password → click signin → wait for redirect back → handle optional authorization page → verify dashboard
- **Category link formats**: "Under Review" has standard manuscript links. "Awaiting Referee Assignment" uses task-oriented links ("Assign Potential Referee" with internal ms_id) — M-number is in an adjacent table cell, not the link. The extractor falls back to searching the parent `<tr>` row text.
- **Extraction pipeline**: `discover_categories` → `collect_manuscript_ids` → `extract_manuscript_detail`
- **Data locations**: `referee_recommendations` stored in `platform_specific.referee_recommendations` (not top-level)
- **Enrichment**: ORCID + OpenAlex + Semantic Scholar for author/referee web profiles
- **Binary contention**: Same `undetected_chromedriver` issue as EM. Run SIAM extractors sequentially, or after EM extractors finish.

---

## 4. EditFlow (MSP) — NACO

**Standalone extractor** (no base class)
**WebDriver**: `webdriver-manager` (selenium.webdriver.Chrome)

### NACO — Numerical Algebra, Control and Optimization

| Field | Value |
|-------|-------|
| Class | `NACOExtractor` |
| File | `production/src/extractors/naco_extractor.py` |
| Login URL | `https://ef.msp.org/login.php` |
| Credentials | `NACO_USERNAME` (NOT email), `NACO_PASSWORD` |
| 2FA | None |
| Output | `production/outputs/naco/` |
| Downloads | None (NACO doesn't download files) |
| Debug | `production/outputs/naco/debug/` (HTML dumps) |

### NACO Behavior

- **Always headless**: `EXTRACTOR_HEADLESS` env var not checked
- **Username auth**: Login field is `id="login"` — uses a username, NOT an email address
- **Login flow**: Navigate to `ef.msp.org/login.php` → clear + fill username → clear + fill password (0.5s delays) → click submit → wait 3s → verify "Mine" link in page
- **Bot evasion**: Same CDP + automation switch approach as ScholarOne
- **Session recovery**: Keyword-based death detection, auto re-login
- **Page load timeout**: 20s (shorter than other extractors)

---

## 5. Gmail API — FS

**Standalone extractor** (no base class, no browser)

### FS — Finance and Stochastics

| Field | Value |
|-------|-------|
| Class | `ComprehensiveFSExtractor` |
| File | `production/src/extractors/fs_extractor.py` |
| Auth | OAuth 2.0 (`config/gmail_token.json`) |
| Email | `dylansmb@gmail.com` |
| Scopes | `gmail.readonly` |
| Output | `production/outputs/fs/` |
| Downloads | `production/downloads/fs/` |

### FS Behavior

- **No browser**: Uses Gmail API directly. No Selenium, no ChromeDriver.
- **Token refresh**: Token at `config/gmail_token.json` has limited lifetime. Re-authenticate via `python3 scripts/setup_gmail_oauth.py` when expired.
- **Email patterns**: Regex matching for new_submission, revision_request, review_invitation, review_submitted, decision_made
- **Manuscript ID pattern**: `(?:FS|FSTO|fs)[-\s]?(\d{4,})`
- **API retry**: `@with_api_retry(max_attempts=3, delay=1.0, backoff=2.0)` — handles `HttpError`, `ConnectionError`, `TimeoutError`
- **Caching**: Uses `CachedExtractorMixin` with SQLite persistent cache
- **Cache save pitfall**: Can hang on `threading.Lock` or large `json.dumps`. JSON file saved FIRST, cache is secondary with 30s timeout.
