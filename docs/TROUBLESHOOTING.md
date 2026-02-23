# Troubleshooting Guide

---

## ChromeDriver Crashes

### "no such window: target window already closed"

**Cause**: macOS quarantine attributes on chromedriver binary after `kill -9`.

**Fix (undetected_chromedriver — JOTA, MAFE, SICON, SIFIN):**
```bash
xattr -c ~/Library/Application\ Support/undetected_chromedriver/undetected_chromedriver
```

**Fix (webdriver-manager — MF, MOR, NACO):**
```bash
rm -rf ~/.wdm/drivers/chromedriver/
# Re-downloads automatically on next run
```

### "session not created: This version of ChromeDriver only supports Chrome version X"

**Cause**: Chrome auto-updated but ChromeDriver version is stale.

**Fix (webdriver-manager):** Clears on next run automatically. If not:
```bash
rm -rf ~/.wdm/drivers/chromedriver/
```

**Fix (undetected_chromedriver):**
```bash
rm -rf ~/Library/Application\ Support/undetected_chromedriver/
```

### Two extractors crash when run simultaneously

**Cause**: `undetected_chromedriver` patches a shared binary. Two instances fight over it.

**Fix**: Run EM and SIAM extractors sequentially, never in parallel.

---

## Cloudflare Issues (SICON, SIFIN only)

### Cloudflare challenge hangs for 180s then times out

**Cause**: Running in headless mode. Cloudflare blocks headless Chrome.

**Fix**:
```bash
EXTRACTOR_HEADLESS=false PYTHONUNBUFFERED=1 python3 sicon_extractor.py
```

### Browser window pops up and disturbs me

**It shouldn't.** In headful mode, the window opens at position (-2000, 0) — far off-screen left — and auto-minimizes after the dashboard loads. If you see it:
1. The window positioning code may have failed (rare)
2. Just minimize it manually — do NOT close it

---

## Authentication Failures

### ScholarOne (MF, MOR) — 2FA code not found

**Symptom**: "No verification code found" or timeout waiting for 2FA.

**Cause**: Gmail API token expired, or email delivery delayed.

**Fix**:
```bash
python3 scripts/setup_gmail_oauth.py  # Re-authenticate Gmail
```
If email is just slow, the extractor falls back to manual input prompt.

### Editorial Manager (JOTA, MAFE) — Login fails

**Possible causes**:
1. Primary URL down → extractor auto-tries `ALT_URL` (MAFE only)
2. Role switch failed → JavaScript `RoleDropdown` didn't fire
3. Frame navigation failed → extractor logs the error

**Debug**: Check for "Login successful" or "Login failed" in output.

### SIAM (SICON, SIFIN) — ORCID login fails

**Possible causes**:
1. ORCID credentials changed
2. ORCID authorization page appeared (should auto-click but may fail)
3. Redirect back to SIAM timed out

**Debug**: Run headful and watch the ORCID login flow manually:
```bash
EXTRACTOR_HEADLESS=false python3 sicon_extractor.py
# Move the window from off-screen: resize it from Activity Monitor or use Cmd+Tab
```

### NACO — Login fails with correct credentials

**Check**: NACO uses `NACO_USERNAME` (a username string), NOT `NACO_EMAIL`. Verify:
```bash
echo $NACO_USERNAME  # Should be a username, not an email address
```

---

## Gmail OAuth Token

### Token expired

**Symptom**: Any of:
- FS extractor fails entirely
- MF/MOR 2FA code fetch fails
- Gmail audit trail cross-check returns empty

**Fix**:
```bash
python3 scripts/setup_gmail_oauth.py
```
Token saved to `config/gmail_token.json`. Typical lifetime: weeks to months.

---

## Output Issues

### No output appearing in terminal

**Cause**: Python output buffering.

**Fix**:
```bash
PYTHONUNBUFFERED=1 python3 extractor.py
```

### "Found 0 manuscripts" in a category that should have manuscripts

**Cause**: The category page uses a link format the parser doesn't recognize.

**Debug**: The extractor auto-saves debug HTML to `production/outputs/{journal}/debug_category_{name}.html` when expected > 0 but found 0. Inspect the HTML to understand the link format.

### SIAM "Awaiting Referee Assignment" shows 0 manuscripts

**Cause**: This category uses task-oriented links ("Assign Potential Referee") with internal IDs, not standard manuscript view links. The M-number is in an adjacent table cell.

**Status**: Fixed in `siam_base.py` — falls back to searching parent `<tr>` row text for M-number.

---

## Process Management

### Kill stuck chromedriver
```bash
pkill -9 chromedriver
```

### NEVER kill Google Chrome
```bash
# WRONG — kills Dylan's personal browser with all tabs
pkill "Google Chrome"

# RIGHT — only kills chromedriver processes
pkill -9 chromedriver
```

### Clear quarantine after kill
```bash
# For undetected_chromedriver
xattr -c ~/Library/Application\ Support/undetected_chromedriver/undetected_chromedriver

# For webdriver-manager
rm -rf ~/.wdm/drivers/chromedriver/
```

---

## Cache Issues

### Cache manager deadlock

**Symptom**: Extractor hangs indefinitely during cache operations.

**Cause**: `threading.Lock()` is NOT reentrant. If `update_referee()` acquires lock then calls `get_referee()` which also acquires lock → deadlock.

**Fix**: Already fixed — uses `threading.RLock()` (reentrant lock).

### FS cache save hangs

**Symptom**: FS extractor hangs after extraction completes.

**Cause**: `threading.Lock` or large `json.dumps` blocking.

**Status**: Fixed — JSON file saved FIRST, cache is secondary with 30s timeout.

---

## Pre-commit Hook Failures

### Security scan fails

**Target**: `production/src` (not `src/`)
**Tools**: `bandit -ll`, `pip-audit`

**Common fix**: MD5 for cache keys needs `usedforsecurity=False`:
```python
hashlib.md5(key.encode(), usedforsecurity=False)
```

### Black reformats code

After a failed commit (pre-commit hook), Black may have reformatted files. Always re-stage:
```bash
git add -u
# Then commit again (NEW commit, don't amend)
```
