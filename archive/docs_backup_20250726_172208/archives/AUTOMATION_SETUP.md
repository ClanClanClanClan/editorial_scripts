# Full Automation Setup Guide

## Problem Solved: Credential Persistence for Automation

**Issue**: Previous sessions required manual password entry, breaking automation.

**Solution**: Environment variable priority system for seamless automation.

## Quick Setup (Recommended)

Run the automated setup script:

```bash
./setup_automation.sh
```

This script will:
- ✅ Collect your credentials securely
- ✅ Add them to your shell profile
- ✅ Set proper file permissions
- ✅ Enable fully automated extractions

## Manual Setup

If you prefer manual configuration:

### 1. ORCID Credentials (for SICON/SIFIN)

```bash
export ORCID_EMAIL="your@orcid.org"
export ORCID_PASSWORD="your_password"
```

### 2. ScholarOne Credentials (for MF/MOR)

```bash
export SCHOLARONE_EMAIL="your@email.com"
export SCHOLARONE_PASSWORD="your_password"
```

### 3. Make Permanent

Add to your shell profile:

```bash
echo 'export ORCID_EMAIL="your@orcid.org"' >> ~/.zshrc
echo 'export ORCID_PASSWORD="your_password"' >> ~/.zshrc
echo 'export SCHOLARONE_EMAIL="your@email.com"' >> ~/.zshrc
echo 'export SCHOLARONE_PASSWORD="your_password"' >> ~/.zshrc
source ~/.zshrc
```

## How It Works

The credential manager now uses this priority order:

1. **Environment Variables** (highest priority) ← Perfect for automation
2. **Settings file** (if available)
3. **Secure credential storage** (only if master password available)

This ensures:
- ✅ **Zero prompts** when environment variables are set
- ✅ **Full automation** capability
- ✅ **Backward compatibility** with existing secure storage
- ✅ **No manual intervention** required

## Testing Your Setup

Verify automation works:

```bash
python3 test_credential_fix.py
```

Expected output for successful automation:
```
🔑 ORCID email in env: YES
🔑 ORCID password in env: YES
✅ SICON credentials found: your@orcid.org
```

## Running Automated Extractions

Now you can run extractions without any prompts:

```bash
# SICON extraction
python3 run_unified_extraction.py --journal sicon

# All journals
python3 run_unified_extraction.py --all-journals
```

## Security Considerations

✅ **Secure**: Environment variables are only accessible to your user account
✅ **Isolated**: Each terminal session has independent access
✅ **Permissions**: Shell profile files are secured with 600 permissions
✅ **Fallback**: Secure encrypted storage still available as backup

## Alternative: CI/CD Environment

For continuous integration or scheduled runs:

```bash
# Set in CI environment
ORCID_EMAIL="your@orcid.org"
ORCID_PASSWORD="your_password"
SCHOLARONE_EMAIL="your@email.com"
SCHOLARONE_PASSWORD="your_password"
```

## Troubleshooting

### "No credentials found" error

1. Check environment variables:
   ```bash
   echo $ORCID_EMAIL
   echo $SCHOLARONE_EMAIL
   ```

2. Reload shell profile:
   ```bash
   source ~/.zshrc
   ```

3. Re-run setup:
   ```bash
   ./setup_automation.sh
   ```

### Still getting password prompts

Make sure you're not using the old secure credential manager directly. The updated credential manager prioritizes environment variables.

## Benefits

- 🚀 **Zero manual intervention**
- 🔄 **Perfect for scheduled runs**
- 🛡️ **Secure credential handling**
- 📊 **Ready for production automation**
- ⚡ **Immediate availability after setup**

Your automation is now fully self-contained and will work across terminal sessions, reboots, and scheduled executions!
