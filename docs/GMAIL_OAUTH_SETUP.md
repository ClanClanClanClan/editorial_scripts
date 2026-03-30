# Gmail OAuth Setup Guide

**Purpose**: Enable Gmail API access for 2FA code retrieval and FS journal extraction.

## Overview

Editorial Scripts requires Gmail API access for:
1. **2FA Code Retrieval**: Automatically fetch verification codes during MF/MOR ScholarOne login
2. **FS Extraction**: Pull referee reports from Finance & Stochastics emails via `ComprehensiveFSExtractor`

## One-Time Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project (e.g. "Editorial Scripts")
3. Enable Gmail API: `APIs & Services > Library > Search "Gmail API" > Enable`

### Step 2: Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON credentials file

### Step 3: Save Credentials

Rename the downloaded file and move it:

```bash
mv ~/Downloads/client_secret_*.json config/gmail_credentials.json
```

### Step 4: Authorize

```bash
python3 scripts/setup_gmail_oauth.py
```

This opens a browser for Google sign-in. Grant read permission. The token is saved to `config/gmail_token.json`.

## File Structure

After setup:
```
config/
├── gmail_credentials.json   # OAuth client (you create this)
└── gmail_token.json         # Auto-generated on first auth
```

Both files are in `.gitignore` and must never be committed.

## Token Refresh

Tokens auto-refresh on each extraction run. If the token expires or is corrupted:

```bash
python3 scripts/setup_gmail_oauth.py
```

## Verification

```bash
# Quick test: verify Gmail API connection
python3 -c "
from google.oauth2.credentials import Credentials
import json
token = json.load(open('config/gmail_token.json'))
print('Token valid:', bool(token.get('token')))
"
```

Or run the FS extractor which uses Gmail API:
```bash
PYTHONPATH=production/src python3 production/src/extractors/fs_extractor.py
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Credentials not found" | Ensure `config/gmail_credentials.json` exists |
| "Token expired" | Run `python3 scripts/setup_gmail_oauth.py` |
| "Access denied" | Check OAuth consent screen in Google Cloud Console |

**Last Updated**: March 2026
