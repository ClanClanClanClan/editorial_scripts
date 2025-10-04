# Gmail OAuth Setup Guide

**Purpose**: Enable Gmail API access for 2FA code retrieval and FS journal extraction

---

## 📋 Overview

The Editorial Command Center requires Gmail API access for:
1. **2FA Code Retrieval**: Automatically fetch verification codes during MF/MOR login
2. **FS Extraction**: Pull referee reports from Finance & Stochastics emails

---

## 🔧 One-Time Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Editorial Command Center"
3. Enable Gmail API:
   ```
   APIs & Services → Library → Search "Gmail API" → Enable
   ```

### Step 2: Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Name: "ECC Desktop Client"
5. Download JSON credentials

### Step 3: Configure Scopes

Required scopes:
- `https://www.googleapis.com/auth/gmail.readonly` - Read emails
- `https://www.googleapis.com/auth/gmail.send` - Send emails (optional)

### Step 4: Save Credentials

1. Rename downloaded file to `gmail_credentials.json`
2. Move to: `config/gmail_credentials.json`

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "editorial-command-center",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

---

## 🔐 First-Time Authorization

### Run Authorization Script

```bash
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts

# Run Gmail auth helper
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from pathlib import Path

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

creds = None
token_file = Path('config/gmail_token.pickle')

if not token_file.exists():
    flow = InstalledAppFlow.from_client_secrets_file(
        'config/gmail_credentials.json',
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Save credentials
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

    print('✅ Gmail OAuth authorization complete!')
    print(f'   Token saved to: {token_file}')
else:
    print('⚠️  Token already exists. Delete to re-authorize.')
"
```

### What Happens

1. Browser opens to Google sign-in
2. Select your ETH email account
3. Grant permissions to read/send Gmail
4. Token saved to `config/gmail_token.pickle`
5. Future API calls use this token automatically

---

## 🧪 Test Gmail Connection

```python
import asyncio
from src.ecc.adapters.journals.fs import FSAdapter

async def test():
    adapter = FSAdapter()
    # Test connection
    messages = await adapter.fetch_recent_emails(max_results=5)
    print(f"✅ Found {len(messages)} recent emails")
    for msg in messages:
        print(f"  - {msg.get('subject', 'No subject')}")

asyncio.run(test())
```

---

## 📝 File Structure

After setup, you should have:

```
config/
├── gmail_config.json           # Created automatically
├── gmail_credentials.json      # ← YOU CREATE THIS
└── gmail_token.pickle          # ← AUTO-GENERATED ON FIRST RUN
```

---

## 🔄 Token Refresh

Tokens expire after ~7 days but auto-refresh if you:
- Run extraction regularly
- Keep `gmail_credentials.json` in place

Manual refresh:
```bash
rm config/gmail_token.pickle
# Re-run authorization script above
```

---

## 🚨 Troubleshooting

### "Credentials not found"
**Solution**: Ensure `gmail_credentials.json` exists in `config/`

### "Token expired"
**Solution**: Delete `gmail_token.pickle` and re-authorize

### "Access denied"
**Solution**: Check OAuth consent screen in Google Cloud Console

### "Quota exceeded"
**Solution**: Gmail API has 1 billion quota units/day (you won't hit this)

---

## 🔐 Security Notes

- ✅ **DO**: Keep `gmail_credentials.json` and `gmail_token.pickle` private
- ✅ **DO**: Add to `.gitignore` (already done)
- ❌ **DON'T**: Commit OAuth files to version control
- ❌ **DON'T**: Share credentials with others

---

## ✅ Verification Checklist

- [ ] Google Cloud project created
- [ ] Gmail API enabled
- [ ] OAuth credentials downloaded
- [ ] File renamed to `gmail_credentials.json`
- [ ] File moved to `config/`
- [ ] Authorization script run successfully
- [ ] `gmail_token.pickle` created
- [ ] Test script shows recent emails

---

## 📚 Additional Resources

- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)

---

**Last Updated**: October 4, 2025
**Estimated Setup Time**: 15 minutes
