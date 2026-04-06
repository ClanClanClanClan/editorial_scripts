# Wiley ScienceConnect / Research Exchange Review — Platform Analysis

## URLs
- Login: `https://wiley.scienceconnect.io/login` (CONNECT SSO)
- Dashboard: `https://review.wiley.com/`
- Manuscript detail: `https://review.wiley.com/details/{uuid}/{uuid}`
- ORCID OAuth: `/api/oauth/2/orcid/start?authToken=`

## Authentication
- Login page at `wiley.scienceconnect.io` uses CONNECT SSO
- Auth methods: Google, ORCID, Microsoft, WeChat, Apple, email+password, passkey
- ORCID button: `button[aria-label="ORCID button"]`
- Email input: `#email-input`
- After login, redirects to `review.wiley.com` dashboard

## Cloudflare Protection
- Both `wiley.scienceconnect.io` and `review.wiley.com` have Cloudflare Turnstile
- Requires human checkbox click ("Verify you are human")
- `undetected_chromedriver` alone does NOT bypass it (headful mode required + manual click)
- Cookie-based: once passed, subsequent navigations within same session work

## Tech Stack
- Login page: React + Material UI (MUI), Vite-bundled (`/assets/index-ajLMNs8O.js`)
- Dashboard: React + Ant Design, different app from login
- SPA: client-side routing

## Dashboard Structure (`review.wiley.com/`)

### Left Panel — Filters
- `[data-test-id="journal-filter-select"]` — Journal filter
- `[data-test-id="bins-card-priority"]` — Priority bins:
  - `[data-test-id="bin-radio-actionrequired"]` — Action required (count in `bin-total-actionrequired`)
  - `[data-test-id="bin-radio-inprogress"]` — In progress
  - `[data-test-id="bin-radio-finalized"]` — Finalized
  - `[data-test-id="bin-radio-all"]` — All
- `[data-test-id="status-select-items-container"]` — Status filter
- `[data-test-id="article-type-select-select-items-container"]` — Article type filter

### Manuscript Cards
- `[data-test-id="manuscript-card{ID}"]` — Card container (ID = numeric)
- `[data-test-id="custom-id"]` — Manuscript ID (e.g., "1384665")
- `[data-test-id="manuscript-status"]` — Status (e.g., "Under Review")
- `[data-test-id="manuscript-current-version"]` — Version (e.g., "v1")
- `[data-test-id="manuscript-title"]` — Title (H3, wrapped in `<a>` to detail page)
- `[data-test-id="author-tag-list"]` — Authors container
- `[data-test-id="author-name-{email}"]` — Author name (data-test-id contains email!)
- `[data-test-id="article-type"]` — Article type
- `[data-test-id="AE-{email}"]` — Associate Editor
- `[data-test-id="manuscript-reviewer-section"]` — Reviewer summary
- `[data-test-id="journal-name"]` — Journal name

### Manuscript Card — Reviewer Summary
- Text format: "Reviewer invitation statuses: 2 Accepted, 1 Pending, 0 Declined, 2 Expired, 0 Revoked"
- "Reviewer reports: 0 Used of 0 Submitted, 0 Overdue, 0 Invalidated"
- "Required reviewers for accept decision: 0 of 1"

## Manuscript Detail Page (`review.wiley.com/details/{uuid}/{uuid}`)

### Header
- `[data-test-id="manuscript-id"]` — "ID 1384665"
- `[data-test-id="manuscript-status"]` — "Under Review"
- `[data-test-id="manuscript-current-version"]` — "v1"
- `[data-test-id="manuscript-title"]` — Title
- `[data-test-id="author-tag-list"]` — Authors
- `[data-test-id="author-name-{email}"]` — Author name (email in attribute)
- `[data-test-id="article-type"]` — Article type
- `[data-test-id="journal-title"]` — Journal name
- `[data-test-id="manuscript-keywords"]` — Keywords (semicolon-separated)
- `[data-test-id="version-select"]` — Version selector

### Editors
- `[data-test-id="editor-label-{email}"]` — Editor name (email in attribute)
  - Format: "Editor-in-Chief:Name" or "Associate Editor:Name"

### Files
- `[data-test-id="files-collapsible"]` — Collapsible files panel
- Contains: Reviewer PDF, Main document (LaTeX PDF, MS Word) with sizes

### Reviewer Panel
- `[data-test-id="reviewer-invitation-panel"]` — Main reviewer section
- `[data-test-id="reviewer-invitation-log-card"]` — One per reviewer (5 in this manuscript)

#### Per-Reviewer Card
- `[data-test-id="reviewer-name-{uuid}"]` — Prefixed with source: `reviewerInvitedManually-`, `reviewerSuggestions-`, `reviewerSearch-`
- `[data-test-id="aff-{uuid}"]` — Affiliation
- `[data-test-id="reviewer-email"]` — Email
- `[data-test-id="reviewer-card-status"]` — Status: "Invitation accepted", "Pending response", "Invitation expired"
- `[data-test-id="extend-deadline-button"]` — Present for accepted reviewers
- `[data-test-id="footer-keywords-list"]` — Reviewer keywords
- `[data-test-id="more-details-button"]` — Expand to see dates

#### Reviewer Dates (after expanding "More Details")
- Format: `Invited:Mar 29, 2026`, `Accepted:Apr 03, 2026`, `Expired:Mar 25, 2026`
- `Time left to submit:2 months` (for accepted)
- `Time left to respond:7 days` (for pending)

### Reviewer Invitation Tabs
- `[data-test-id="active-reviewer-invite-info-tab"]` — Active invitations
- `[data-test-id="reviewer-invite-suggested-tab"]` — Suggested reviewers
- `[data-test-id="reviewer-invite-searched-tab"]` — Search results
- `[data-test-id="reviewer-invite-manual-tab"]` — Manual invite
- `[data-test-id="browse-suggestions"]` — Browse suggestions button
- `[data-test-id="search-in-database"]` — Search database button
- `[data-test-id="invite-manually"]` — Manual invite button

### Editorial Recommendation
- `[data-test-id="editorial-recommendation-panel"]` — Recommendation panel
- `[data-test-id="no-editorial-decision"]` — Shows when no decision yet

### Activity
- `[data-test-id="activity-log-section"]` — Activity logs and emails

## Sample Extracted Data

### Manuscript
```json
{
  "manuscript_id": "1384665",
  "title": "Dynamic Asset Pricing with \u03b1-MEU Model",
  "status": "Under Review",
  "version": "v1",
  "article_type": "Original Article",
  "journal": "Mathematical Finance",
  "keywords": "capital asset pricing model; economics; risk premium; arbitrage pricing theory; microeconomics; expected utility hypothesis; endowment",
  "submission_date": "Feb 25, 2026"
}
```

### Authors
```json
[
  {"name": "Jiacheng Fan", "email": "jiacheng.fan@polyu.edu.hk"},
  {"name": "Xue Dong He", "email": "xdhe@se.cuhk.edu.hk"},
  {"name": "Ruocheng Wu", "email": "rcwu11@link.cuhk.edu.hk"}
]
```

### Editors
```json
[
  {"role": "Editor-in-Chief", "name": "Editor in Chief", "email": "mathfin.journal@maths.ox.ac.uk"},
  {"role": "Associate Editor", "name": "Dylan Possamai", "email": "dylan.possamai@math.ethz.ch"}
]
```

### Reviewers
```json
[
  {"name": "Peng Luo", "email": "peng.luo@sjtu.edu.cn", "institution": "SJTU", "status": "Invitation accepted", "invited": "Mar 29, 2026", "accepted": "Apr 03, 2026", "source": "InvitedManually"},
  {"name": "Traian Pirvu", "email": "tpirvu@math.mcmaster.ca", "institution": "McMaster University", "status": "Invitation accepted", "invited": "Mar 13, 2026", "accepted": "Mar 17, 2026", "source": "Suggestions"},
  {"name": "Shaolin Ji", "email": "jsl@sdu.edu.cn", "institution": "Shandong University", "status": "Pending response", "invited": "Mar 24, 2026", "source": "Suggestions"},
  {"name": "Paolo Guasoni", "email": "paolo.guasoni@dcu.ie", "institution": "Dublin City University", "status": "Invitation expired", "invited": "Mar 04, 2026", "expired": "Mar 25, 2026", "source": "Search"},
  {"name": "Beissner, Patrick", "email": "patrick.beissner@uni-bielefeld.de", "institution": "Universitat Bielefeld", "status": "Invitation expired", "invited": "Mar 04, 2026", "expired": "Mar 25, 2026", "source": "Search"}
]
```

### Files
- Reviewer PDF (1.53 MB)
- Main document - LaTeX PDF (1.24 MB)
- Main document - MS Word (1.81 MB)

## Key Differences from Other Platforms

| Feature | ScholarOne | Editorial Manager | Wiley Rex |
|---------|------------|-------------------|-----------|
| Auth | Email/password + 2FA | Username/password | ORCID/Google/etc via CONNECT SSO |
| Cloudflare | Yes (bypassed by UC) | No | Yes (Turnstile, harder) |
| Tech | Server-rendered HTML | Server-rendered + iframes | React SPA (Ant Design) |
| IDs | Alphanumeric (MF-2024-001) | Numeric (JOTA-D-24-00123) | Numeric (1384665) + UUID |
| Reviewer source | Not tracked | Not tracked | Tracked (Manual/Suggested/Search) |
| Date format | Various | Various | "Mon DD, YYYY" (e.g., "Mar 29, 2026") |
| Manuscript URL | Category-based | ID-based | UUID-based |

## Extractor Strategy

1. **Login**: Use `undetected_chromedriver` headful + pyautogui for Cloudflare Turnstile checkbox
   - OR: pre-seed cookies from a manual session
2. **Dashboard**: Click "In progress" or "All" radio, extract manuscript cards
3. **Detail**: Navigate to each `review.wiley.com/details/{uuid}/{uuid}`
4. **Reviewers**: Parse `reviewer-invitation-log-card` elements, expand "More details" for dates
5. **Normalize**: Map to canonical schema via `output_schema.py`
