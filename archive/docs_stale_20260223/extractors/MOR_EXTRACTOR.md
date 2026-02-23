MOR Extractor (ScholarOne) – Design, Flow, and Debug Guide
===========================================================

Overview
- Platform: ScholarOne (Manuscript Central)
- Adapter: `src/ecc/adapters/journals/mor.py` (inherits from `ScholarOneAdapter`)
- Browser stack: Playwright (Chromium), async, with retry helpers
- Key capabilities:
  - Login with 2FA via Gmail API (optional, with fallback to manual)
  - Category navigation and manuscript list parsing
  - Manuscript details extraction: basic info, authors, reviewers, metadata
  - Resource downloads via popup (PDF, Original Files)
  - Audit Trail extraction (pagination under the Audit tab)
  - Tracing/snapshots for debugging

Configuration
- Credentials: `MOR_EMAIL`, `MOR_PASSWORD`
- Gmail OAuth: `GMAIL_CREDENTIALS_PATH` (defaults to `config/gmail_credentials.json`), `GMAIL_TOKEN_PATH`
- Tracing/Snapshots: set `ECC_DEBUG_TRACING=1` and/or `ECC_DEBUG_SNAPSHOTS=1`

High‑Level Flow
1) Authenticate
   - Go to `https://mc.manuscriptcentral.com/mor`
   - Fill USERID/PASSWORD, submit
   - If prompted for `#TOKEN_VALUE`, fetch 2FA via Gmail API (search recent verification messages) and submit
2) Category extraction and list view
   - Uses default categories (Awaiting Reviewer Reports, Awaiting AE Recommendation, …)
   - Clicks category via robust row strategy (text match; clicks numeric link or the cell)
   - Parses manuscript rows with tolerant selectors and regex for MOR IDs
3) Manuscript details
   - Title/Keywords/Abstract (opens popup via “Abstract” button)
   - Authors (names + possible email via popup)
   - Referees (Reviewer List):
     - Rows detected by hidden inputs `XIK_RP_ID*` or `ORDER*` selects
     - Name from visible anchor; email via popup
     - Status from 3rd column; Invited/Agreed/Due dates parsed from 4th column
   - Metadata (page/word count if available)
   - Resources
     - PDF Proof: opens a new window; adapter captures network response and writes to disk
     - Original Files: saves the popup HTML list for later parsing
   - Audit Trail
     - Navigates to Audit tab (left tab image or text)
     - Iterates `select[name='page_select']` across pages
     - Parses event rows; extracts letter metadata (To/From/Subject, attachments indicator)
4) Persist
   - The CLI can persist manuscripts to DB via repository upsert by (journal_id, external_id)

Key Selectors and Patterns (MOR)
- Manuscript ID pattern: `MOR-\d{4}-\d{4}`
- Category rows: table rows containing category text; click numeric link or cell
- Reviewer rows: `tr:has(input[name^='XIK_RP_ID'])` (fallback: `tr:has(select[name^='ORDER'])`)
- Status cell: `td:nth-child(3)` in reviewer rows
- Audit Trail:
  - Tab: `a:has(img[src*='lefttabs_audit_trail'])` or `a:has-text('Audit Trail')`
  - Pagination: `select[name='page_select']`
  - Container: XPath from header: `//td[contains(@class,'detailsheaderbg2')][contains(., 'Audit Trail')]/ancestor::table/following::td[@class='tablelines'][1]`

Popups and Downloads
- Many actions open a new window (JS `window.open` or `popWindow`): Abstract, PDF, Original Files, Letters
- Adapter uses `download_from_popup()` to:
  - Capture first matching response by `content-type` or `url_substring`
  - Save byte body to file. If none matches, saves popup HTML as fallback

Debugging and Tracing
- Enable tracing: `ECC_DEBUG_TRACING=1` → saves `trace_MOR.zip` under `downloads/MOR/`
- Enable snapshots: `ECC_DEBUG_SNAPSHOTS=1` → PNG+HTML dumps after key steps (category clicks, parsed lists)
- CLI flags: `--trace`, `--debug-snapshots`

CLI Usage
- Dry‑run without persist:
  - `python -m src.ecc.cli extract manuscript -j mor --headless --dry-run --trace --debug-snapshots`
- Persist to DB:
  - `DATABASE_URL=postgresql+asyncpg://...` then
  - `python -m src.ecc.cli extract manuscript -j mor --headless --persist`

Known Edge Cases
- Dynamic DOM changes may alter the position of Status/Dates; parser falls back to text search
- Audit Trail pagination relies on `onchange` JS; `select_option` triggers it in most cases
- Some PDF responses load inline without `Content-Disposition`; the network response body handler covers this

Extending
- To parse more reviewer details (institutions, departments), expand the nested table scan in the reviewer name cell
- To download individual attachments from letters, open the letter popup and capture its network responses similarly
