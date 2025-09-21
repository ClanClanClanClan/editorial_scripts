# 📧 Gmail API Setup Guide for Editorial Scripts

**Status**: Ready for implementation
**Purpose**: Enable email-based extraction for FS and JOTA journals
**Estimated Time**: 15-30 minutes

---

## 🎯 **Overview**

This guide sets up Gmail API access to enable email-based journal extraction for:
- **Finance and Stochastics (FS)** - Email-based manuscript tracking
- **Journal of Optimization Theory and Applications (JOTA)** - Email-based referee management

---

## 🚀 **Quick Setup (Automated)**

### **Option 1: Run Setup Script**
```bash
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts
python setup_gmail_api.py
```

The script will:
1. ✅ Guide you through Google Cloud Console setup
2. ✅ Handle OAuth2 authentication flow
3. ✅ Test Gmail API access
4. ✅ Analyze existing editorial email patterns
5. ✅ Create configuration files
6. ✅ Validate scraper-specific queries

---

## 📋 **Manual Setup (Step-by-Step)**

### **Step 1: Google Cloud Console Setup**

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Gmail account (the one with editorial emails)

2. **Create or Select Project**
   ```
   - Click "Select Project" → "New Project"
   - Name: "Editorial Scripts Gmail API"
   - Click "Create"
   ```

3. **Enable Gmail API**
   ```
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Gmail API" → "Enable"
   ```

4. **Create OAuth2 Credentials**
   ```
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop application"
   - Name: "Editorial Scripts"
   - Click "Create"
   ```

5. **Download Credentials**
   ```
   - Click "Download JSON" on the created OAuth client
   - Save as: credentials.json
   - Move to: /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/credentials.json
   ```

### **Step 2: Authentication**

```bash
# Run authentication flow
python setup_gmail_api.py
```

This will:
- ✅ Open browser for OAuth consent
- ✅ Generate `token.json` file
- ✅ Test basic Gmail access

### **Step 3: Verify Setup**

```bash
# Test Gmail service
python -c "
import asyncio
from src.infrastructure.services.gmail_service import test_gmail_connection
asyncio.run(test_gmail_connection())
"
```

Expected output:
```
✅ Connected to Gmail: your-email@gmail.com
📊 Total messages: 12,345
```

---

## 🔍 **Email Pattern Analysis**

### **Required Email Types**

#### **Finance and Stochastics (FS)**:
- **Weekly Overview**: `subject:"Finance and Stochastics - Weekly Overview"`
- **Flagged Emails**: `is:starred subject:(Finance Stochastics)`
- **General**: `from:finance-stochastics OR subject:"Finance and Stochastics"`

#### **JOTA**:
- **Weekly Overview**: `subject:"JOTA - Weekly Overview Of Your Assignments"`
- **Flagged Emails**: `is:starred subject:(JOTA)`
- **Invitations**: `subject:"Reviewer Invitation for"`
- **Acceptances**: `subject:"Reviewer has agreed to review"`

### **Email Preparation**

1. **Star Important Emails**
   ```
   - Open Gmail
   - Search for journal-specific emails
   - Star emails you want to include in "flagged" extractions
   ```

2. **Verify Email Access**
   ```
   - Ensure editorial emails are in the Gmail account being used
   - Check if emails are forwarded/filtered to this account
   - Verify recent email activity for both journals
   ```

---

## ⚙️ **Configuration Files**

### **Generated Files**:

1. **`credentials.json`** - Google OAuth2 credentials
2. **`token.json`** - Authentication token (auto-generated)
3. **`gmail_config.json`** - Scraper configuration

### **Configuration Structure**:
```json
{
  "gmail_api": {
    "credentials_file": "credentials.json",
    "token_file": "token.json",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
    "status": "configured"
  },
  "journals": {
    "FS": {
      "email_queries": {
        "weekly_overview": "subject:\"Finance and Stochastics - Weekly Overview\"",
        "flagged": "is:starred subject:(Finance Stochastics)"
      }
    },
    "JOTA": {
      "email_queries": {
        "weekly_overview": "subject:\"JOTA - Weekly Overview Of Your Assignments\"",
        "flagged": "is:starred subject:(JOTA)"
      }
    }
  }
}
```

---

## 🧪 **Testing and Validation**

### **Test Individual Scrapers**

```bash
# Test FS scraper
python -c "
import asyncio
from src.infrastructure.scrapers.email_based.fs_scraper import FSScraper
async def test():
    scraper = FSScraper()
    manuscripts = await scraper.extract_manuscripts()
    print(f'FS: {len(manuscripts)} manuscripts found')
asyncio.run(test())
"

# Test JOTA scraper
python -c "
import asyncio
from src.infrastructure.scrapers.email_based.jota_scraper import JOTAScraper
async def test():
    scraper = JOTAScraper()
    manuscripts = await scraper.extract_manuscripts()
    print(f'JOTA: {len(manuscripts)} manuscripts found')
asyncio.run(test())
"
```

### **Test Unified Extraction**

```bash
# Run with email journals enabled
python run_unified_extraction.py --journals FS,JOTA
```

### **Expected Results**:

#### **FS (Finance and Stochastics)**:
- **Manuscripts**: Email-based manuscript tracking
- **Referees**: Extracted from email communications
- **Timeline**: Built from email timestamps
- **Documents**: Email attachments (PDFs)

#### **JOTA**:
- **Manuscripts**: From weekly overview emails
- **Referees**: From invitation/acceptance emails
- **Status Tracking**: Email-based status updates
- **Communication History**: Complete email thread analysis

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. No Editorial Emails Found**
```
Problem: 0 emails found for FS/JOTA
Solution:
- Verify emails are in the correct Gmail account
- Check email forwarding settings
- Ensure recent editorial activity
- Star relevant emails for flagged queries
```

#### **2. Authentication Errors**
```
Problem: OAuth2 authentication fails
Solution:
- Check credentials.json is valid
- Ensure Gmail API is enabled in Google Cloud Console
- Try deleting token.json and re-authenticating
- Verify OAuth consent screen is configured
```

#### **3. Permission Errors**
```
Problem: Insufficient permissions
Solution:
- Check Gmail API scopes include 'readonly'
- Re-run OAuth flow with correct permissions
- Verify Google Cloud Console project has Gmail API enabled
```

#### **4. Empty Email Content**
```
Problem: Emails found but content is empty
Solution:
- Check email format (HTML vs plain text)
- Verify email encoding
- Update email parsing regex patterns
- Test with recent emails
```

---

## 🔐 **Security Considerations**

### **OAuth2 Scopes**:
- ✅ **gmail.readonly** - Read-only access (recommended)
- ❌ **gmail.modify** - Not needed for extraction
- ❌ **gmail.send** - Not needed for extraction

### **Credential Management**:
- 🔒 **credentials.json** - Keep secure, don't commit to git
- 🔒 **token.json** - Auto-generated, keep secure
- ✅ **Config files** - Safe to commit (no secrets)

### **Access Patterns**:
- 📊 **Read-only operations** - No email modification
- 🔍 **Search-based access** - Targeted email retrieval
- ⏱️ **Rate limiting** - Respects Gmail API limits

---

## 📊 **Performance Expectations**

### **Email Volume Estimates**:
- **FS**: 10-50 emails per month
- **JOTA**: 20-100 emails per month
- **Processing Time**: 30-60 seconds per journal
- **API Calls**: 5-20 per extraction session

### **Caching Strategy**:
- **Email IDs**: Cached to avoid re-processing
- **Content Hash**: Smart caching based on email content
- **Timeline Data**: Incremental updates only

---

## 🎯 **Next Steps After Setup**

1. **Test Email Extraction**
   ```bash
   python setup_gmail_api.py
   ```

2. **Run Scrapers Individually**
   ```bash
   # Test each scraper
   python -m src.infrastructure.scrapers.email_based.fs_scraper
   python -m src.infrastructure.scrapers.email_based.jota_scraper
   ```

3. **Integration with Main System**
   ```bash
   # Add to unified extraction
   python run_unified_extraction.py --journals ALL
   ```

4. **Monitor and Optimize**
   - Check email pattern recognition accuracy
   - Adjust regex patterns for better extraction
   - Monitor API usage and rate limits
   - Set up automated runs with caching

---

## ✅ **Success Criteria**

- [ ] Google Cloud Console project created and Gmail API enabled
- [ ] OAuth2 credentials downloaded as `credentials.json`
- [ ] Authentication flow completed successfully
- [ ] Gmail API access verified with test queries
- [ ] Editorial email patterns identified and validated
- [ ] FS scraper finds and parses email-based manuscripts
- [ ] JOTA scraper extracts referee data from emails
- [ ] Configuration files created and validated
- [ ] Integration with unified extraction system working

**🏆 When complete, email-based journals (FS and JOTA) will be fully operational alongside web-based journals (SICON, SIFIN, MF, MOR).**
