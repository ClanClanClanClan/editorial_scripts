FS Extractor (Email‑Based) – Design, Flow, and Debug Guide
==========================================================

Overview
- Journal: Finance and Stochastics (FS)
- Platform: Email‑based workflow (Gmail API)
- Production implementation: `production/src/extractors/fs_extractor.py`
- Purpose: Track submissions, reviewer interactions, and timelines directly from editorial email accounts

Key Components
- Gmail API (OAuth2): message listing, search queries, message bodies
- Parsing strategies: subjects, standard templates, attachments
- Timeline synthesis: construct manuscript timelines from inbound/outbound messages

Setup
- Credentials JSON: `config/gmail_credentials.json` (or `GMAIL_CREDENTIALS_PATH`)
- Token storage: `config/gmail_token.json` (or `GMAIL_TOKEN_PATH`)
- Scopes: read‑only & send (optional)

Flow
1) Authenticate with Gmail API and get a service client
2) Search threads by manuscript ID and canonical subject patterns
3) Parse messages:
   - Extract recipients/senders, subject, sent date
   - Identify event types (invitation, reminder, acceptance, report received)
   - Detect attachments for reports (PDF/DOCX)
4) Build timeline JSON per manuscript
5) Export to JSON/CSV; optional DB persistence via a repository in ECC (future integration)

Debugging
- Use small time window searches initially (e.g., `newer_than:7d`)
- Verify label filters and subject patterns
- Dump raw message payloads for new or unknown templates

Audit Summary (FS)
- Strength: no dependency on site DOM; robust to platform changes
- Risk: template drift in email content/subjects; mitigated via pattern catalogs and whitelists
- Attachments: use Gmail API attachment endpoints; store with checksum to avoid duplicates

Extending
- Integrate FS results into ECC DB schema (files/reports/timeline tables)
- Normalize ID mapping across FS and ScholarOne journals
