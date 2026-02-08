# 🚀 Editorial Scripts - Implementation Plan
**Date**: October 4, 2025
**Goal**: Restore production extractors and complete ECC implementation

---

## 📋 Overview

This plan addresses two parallel tracks:
1. **Track A**: Restore production extractors to working state (1-2 hours)
2. **Track B**: Complete ECC implementation to achieve feature parity (15-20 hours)

---

## 🎯 Track A: Restore Production Extractors

### Current Status
- ✅ **MOR**: Syntax fixed (Oct 4, 2025) - ready to test
- ❌ **MF**: Blocked by Gmail OAuth (not configured)
- ✅ **Syntax**: All IndentationErrors resolved

### Milestone A.1: Gmail OAuth Setup (30-45 minutes)

#### Prerequisites
You need Google Cloud Platform credentials. If you don't have them:

**Option 1: Use Existing Credentials**
```bash
# Check if you have credentials from previous setup
ls -lh config/credentials.json config/client_secret.json

# If found, proceed to Step 2
```

**Option 2: Create New Credentials** (if needed)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Editorial Scripts Gmail API"
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download JSON as `config/client_secret.json`

#### Steps

**Step 1: Place Credentials**
```bash
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts

# Your credentials file should be here:
ls -lh config/client_secret.json
# OR
ls -lh config/credentials.json
```

**Step 2: Run OAuth Setup Script**
```bash
# Check if setup script exists
ls -lh scripts/setup_gmail_oauth.py

# If not found, check production location
ls -lh production/src/core/setup_gmail_auth.py

# Run the appropriate script
python3 scripts/setup_gmail_oauth.py
# OR
python3 production/src/core/setup_gmail_auth.py
```

**Step 3: Authenticate in Browser**
- Script will open browser
- Login to MF email account
- Grant Gmail API access
- Browser will show "Authentication successful"

**Step 4: Verify Tokens Created**
```bash
ls -lh config/gmail_token.json config/token.pickle

# Should see:
# -rw-r--r--  config/gmail_token.json
# -rw-r--r--  config/token.pickle
```

**Expected Output**:
```
✅ Gmail OAuth configured successfully
✅ Token saved to config/gmail_token.json
✅ Credentials cached to config/token.pickle
```

### Milestone A.2: Test MOR Extractor (15 minutes)

**Goal**: Verify MOR syntax fixes work

```bash
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors

# Load credentials from keychain
source ~/.editorial_scripts/load_all_credentials.sh

# Verify credentials loaded
echo "MOR_EMAIL=$MOR_EMAIL (should not be empty)"

# Run MOR extractor
python3 mor_extractor_enhanced.py
```

**Expected Behavior**:
1. ✅ Authentication starts
2. ✅ 2FA prompt appears (enter code manually or Gmail API fetches it)
3. ⚠️ Navigation may work or fail (depends on stub functions)
4. ⚠️ Extraction may return limited data (stub functions return empty)

**Success Criteria**:
- No Python syntax errors
- Authentication completes
- Script runs without crashing

**Known Limitations** (stub functions):
- `extract_referee_report_from_link()` returns None
- `extract_referees_comprehensive()` returns []
- `extract_manuscript_details()` returns {}

**These stubs mean**: MOR will authenticate but may not extract full data. This is expected and will be fixed in Track B if needed.

### Milestone A.3: Test MF Extractor (15 minutes)

**After Gmail OAuth setup**:

```bash
cd production/src/extractors

# Load credentials
source ~/.editorial_scripts/load_all_credentials.sh

# Run MF extractor
python3 mf_extractor_nopopup.py
```

**Expected Behavior**:
1. ✅ Authentication starts
2. ✅ 2FA code fetched automatically from Gmail
3. ✅ Navigates to AE Center
4. ✅ Finds categories
5. ✅ Extracts manuscripts with full data

**Success Criteria**:
- Authentication completes
- Manuscripts extracted
- JSON output file created: `mf_extraction_YYYYMMDD_HHMMSS.json`

**Verify Output**:
```bash
ls -lh production/src/extractors/results/mf/

# Should see new file with today's timestamp
# File should be 50KB-200KB (depending on manuscript count)
```

---

## 🚧 Track B: Complete ECC Implementation

### Current Status
- ✅ **Authentication**: 100% complete (Selenium-based, anti-bot bypass working)
- ❌ **Navigation**: 0% (fails after auth)
- ❌ **Extraction**: 0% (returns empty data)

### Implementation Phases

---

### Phase B.1: Fix Navigation (4-6 hours)

**Goal**: Successfully navigate to AE Center after authentication

**Current Problem**:
Authentication verification has false positives - thinks it's logged in when still on login page.

**Evidence**:
```
Current URL: https://mc.manuscriptcentral.com/mor
Links found: Log In, Create Account, Instructions & Forms
Status: Still on login page!
```

**File to Edit**: `src/ecc/adapters/journals/scholarone_selenium.py`

#### Task B.1.1: Improve Authentication Verification (1 hour)

**Current Code** (lines 194-230):
```python
# Look for role center links (these only appear when logged in)
success_selectors = [
    (By.LINK_TEXT, "Associate Editor Center"),
    (By.LINK_TEXT, "Author"),
    (By.LINK_TEXT, "Reviewer"),
    (By.PARTIAL_LINK_TEXT, "Center"),
    (By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR')]"),
    (By.XPATH, "//a[contains(text(), 'Log Out') or contains(text(), 'Logout')]"),
]
```

**Problem**: Too broad - "Center" matches login page elements

**Fix Strategy**:
1. Check URL changed from login page first
2. Look for specific authenticated indicators only
3. Verify NO login elements present

**Recommended Changes**:
```python
async def authenticate(self) -> bool:
    # ... existing code ...

    # After clicking login/2FA:

    # 1. Wait for page to fully load
    await asyncio.sleep(5)

    # 2. Verify URL changed from login
    current_url = self.driver.current_url
    if "page=LOGIN" in current_url or "/mc/login" in current_url.lower():
        self.logger.error("Still on login page - authentication failed")
        return False

    # 3. Check that login form is GONE
    try:
        self.driver.find_element(By.ID, "USERID")
        self.logger.error("Login form still present - not authenticated")
        return False
    except:
        pass  # Good - login form is gone

    # 4. Look for SPECIFIC authenticated indicators
    wait = WebDriverWait(self.driver, 20)

    # Must find logout link (only present when logged in)
    try:
        logout_link = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href, 'logout') or contains(@href, 'LOGOUT')]")
            )
        )
        self.logger.info("✅ Found logout link - authentication confirmed")
    except TimeoutException:
        self.logger.error("❌ No logout link found - authentication failed")
        return False

    # 5. Verify we see role centers
    try:
        ae_center = self.driver.find_element(
            By.PARTIAL_LINK_TEXT, "Associate Editor"
        )
        self.logger.info("✅ Found AE Center link - ready to navigate")
        return True
    except:
        self.logger.warning("⚠️ Authenticated but no AE Center access")
        return False
```

**Testing**:
```bash
cd /Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts

# Test MOR authentication
python3 -c "
import asyncio
from src.ecc.adapters.journals.mor import MORAdapter

async def test():
    async with MORAdapter(headless=False) as adapter:
        result = await adapter.authenticate()
        print(f'Auth result: {result}')
        print(f'Current URL: {adapter.driver.current_url}')
        input('Press Enter to close browser...')

asyncio.run(test())
"
```

**Success Criteria**:
- Authentication only returns True when actually logged in
- Can see dashboard with role center links
- URL is not login page

#### Task B.1.2: Implement AE Center Navigation (2 hours)

**Current Code** (lines 243-282):
```python
async def navigate_to_ae_center(self) -> bool:
    # Check if already at AE Center
    current_url = self.driver.current_url
    if "ASSOCIATE_EDITOR" in current_url or "AE_HOME" in current_url:
        return True

    # Try to find AE Center link
    # ...
```

**Fix Strategy**:
Port from production MF extractor logic.

**Steps**:

1. **Check if already at AE Center**:
```python
# Look for category links which only appear at AE Center
try:
    self.driver.find_element(
        By.XPATH,
        "//a[contains(text(), 'Awaiting AE Recommendation') or contains(text(), 'Awaiting Reviewer')]"
    )
    self.logger.info("✅ Already at AE Center")
    return True
except:
    pass  # Not at AE Center yet
```

2. **Find and click AE Center link**:
```python
try:
    wait = WebDriverWait(self.driver, 10)
    ae_link = wait.until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "Associate Editor Center")
        )
    )

    self.logger.info("Clicking Associate Editor Center...")
    ae_link.click()
    await asyncio.sleep(3)

except TimeoutException:
    # Try alternative selectors
    try:
        ae_link = self.driver.find_element(
            By.XPATH,
            "//a[contains(text(), 'Associate Editor')]"
        )
        ae_link.click()
        await asyncio.sleep(3)
    except:
        self.logger.error("❌ Cannot find AE Center link")
        return False
```

3. **Verify navigation succeeded**:
```python
# Check we're now at AE Center
current_url = self.driver.current_url
if "ASSOCIATE_EDITOR" not in current_url:
    self.logger.warning(f"⚠️ Unexpected URL after click: {current_url}")

# Verify category links present
try:
    self.driver.find_element(
        By.XPATH,
        "//a[contains(text(), 'Awaiting')]"
    )
    self.logger.info("✅ Successfully navigated to AE Center")
    return True
except:
    self.logger.error("❌ At wrong page - no category links found")
    return False
```

**Testing**:
```python
# test_navigation.py
import asyncio
from src.ecc.adapters.journals.mor import MORAdapter

async def test():
    async with MORAdapter(headless=False) as adapter:
        if await adapter.authenticate():
            print("✅ Authentication successful")

            if await adapter.navigate_to_ae_center():
                print("✅ Navigation successful")
                print(f"Current URL: {adapter.driver.current_url}")

                # Check what's on the page
                page_text = adapter.driver.find_element(By.TAG_NAME, "body").text
                print("\nPage contents preview:")
                print(page_text[:500])
            else:
                print("❌ Navigation failed")
        else:
            print("❌ Authentication failed")

asyncio.run(test())
```

#### Task B.1.3: Implement Category Detection (2 hours)

**Goal**: Find all manuscript categories and their counts

**Current Code** (lines 284-339):
```python
async def get_manuscript_categories(self) -> list[dict]:
    categories = []
    category_names = [
        "Awaiting AE Recommendation",
        "Awaiting Reviewer Reports",
        # ...
    ]

    # Find category links
    for category_name in category_names:
        try:
            category_link = self.driver.find_element(
                By.XPATH, f"//a[contains(text(), '{category_name}')]"
            )
            # ...
```

**Improvements Needed**:

1. **Dynamic category discovery** (don't hardcode names):
```python
# Find all links that look like categories
category_links = self.driver.find_elements(
    By.XPATH,
    "//table[@class='main']//a[contains(@href, 'pg=') or contains(text(), 'Awaiting')]"
)
```

2. **Better count extraction**:
```python
for link in category_links:
    try:
        category_name = link.text.strip()
        if not category_name or len(category_name) < 5:
            continue

        # Get parent row to find count
        row = link.find_element(By.XPATH, "./ancestor::tr[1]")
        cells = row.find_elements(By.TAG_NAME, "td")

        # Count is usually in bold in adjacent cell
        count = 0
        for cell in cells:
            bold = cell.find_elements(By.TAG_NAME, "b")
            if bold:
                count_text = bold[0].text.strip()
                if count_text.isdigit():
                    count = int(count_text)
                    break

        categories.append({
            "name": category_name,
            "count": count,
            "element": link,
        })
    except:
        continue
```

**Testing**:
```python
async def test():
    async with MORAdapter(headless=False) as adapter:
        if await adapter.authenticate():
            if await adapter.navigate_to_ae_center():
                categories = await adapter.get_manuscript_categories()
                print(f"\n✅ Found {len(categories)} categories:")
                for cat in categories:
                    print(f"  - {cat['name']}: {cat['count']} manuscripts")

asyncio.run(test())
```

---

### Phase B.2: Implement Basic Manuscript Fetching (4-6 hours)

**Goal**: Extract list of manuscript IDs from each category

#### Task B.2.1: Click Category and Find Manuscripts (2 hours)

**Current Code** (lines 341-421):
```python
async def fetch_manuscripts(self, categories: list[str]) -> list[Manuscript]:
    # ... navigation ...

    # Click category link
    category["element"].click()
    await asyncio.sleep(3)

    # Find "Take Action" links
    take_action_links = self.driver.find_elements(
        By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]"
    )
```

**This looks correct!** But needs refinement:

1. **Store link references before clicking**:
```python
# Extract all manuscript IDs BEFORE clicking any links
manuscript_ids = []

for link in take_action_links:
    try:
        # Get the row
        row = link.find_element(By.XPATH, "./ancestor::tr[1]")

        # Get cells
        cells = row.find_elements(By.TAG_NAME, "td")
        if not cells:
            continue

        # First cell usually has manuscript ID
        first_cell_text = cells[0].text.strip()

        # Validate ID format
        if re.match(self.manuscript_pattern, first_cell_text):
            manuscript_ids.append({
                "id": first_cell_text,
                "category": category["name"],
            })
    except:
        continue

self.logger.info(f"Found {len(manuscript_ids)} manuscripts in {category['name']}")
```

2. **Click each manuscript to extract details**:
```python
for manuscript_info in manuscript_ids:
    try:
        # Re-navigate to category list
        await self.navigate_to_ae_center()

        # Click category again
        # ... (need to re-find category link) ...

        # Find the manuscript row again
        manuscript_row = self.driver.find_element(
            By.XPATH,
            f"//td[contains(text(), '{manuscript_info['id']}')]/ancestor::tr[1]"
        )

        # Find "Take Action" link in that row
        take_action = manuscript_row.find_element(
            By.XPATH,
            ".//a[.//img[contains(@src, 'check_off.gif')]]"
        )

        take_action.click()
        await asyncio.sleep(3)

        # Now we're on manuscript details page
        manuscript = await self.extract_manuscript_details(manuscript_info["id"])
        manuscripts.append(manuscript)

    except Exception as e:
        self.logger.error(f"Error with {manuscript_info['id']}: {e}")
        continue
```

#### Task B.2.2: Implement Real Detail Extraction (3 hours)

**Current Code** (lines 423-444):
```python
async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
    # Currently returns placeholder
    manuscript = Manuscript(
        journal_id=self.config.journal_id,
        external_id=manuscript_id,
        title=f"Manuscript {manuscript_id}",  # FAKE!
        status=ManuscriptStatus.UNDER_REVIEW,
    )
```

**Need to implement**: Parse actual manuscript details from page

**Production reference**: Look at `production/src/extractors/mf_extractor_nopopup.py` around lines 1500-2000

**Implementation**:
```python
async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
    """Extract real manuscript details from details page."""
    try:
        self.logger.info(f"Extracting details for {manuscript_id}")

        # Wait for page to load
        await asyncio.sleep(2)

        # Extract title
        title = "Unknown"
        try:
            title_elem = self.driver.find_element(
                By.XPATH,
                "//td[contains(text(), 'Title:')]/following-sibling::td[1]"
            )
            title = title_elem.text.strip()
        except:
            # Try alternative selector
            try:
                title_elem = self.driver.find_element(
                    By.XPATH,
                    "//b[contains(text(), 'Title')]/ancestor::tr[1]/td[2]"
                )
                title = title_elem.text.strip()
            except:
                self.logger.warning(f"Could not extract title for {manuscript_id}")

        # Extract submission date
        submission_date = None
        try:
            date_elem = self.driver.find_element(
                By.XPATH,
                "//td[contains(text(), 'Date Submitted:')]/following-sibling::td[1]"
            )
            submission_date = date_elem.text.strip()
        except:
            pass

        # Extract status
        status = ManuscriptStatus.UNDER_REVIEW  # Default
        try:
            status_elem = self.driver.find_element(
                By.XPATH,
                "//td[contains(text(), 'Status:')]/following-sibling::td[1]"
            )
            status_text = status_elem.text.strip().lower()

            # Map to enum
            if "accepted" in status_text:
                status = ManuscriptStatus.ACCEPTED
            elif "rejected" in status_text or "declined" in status_text:
                status = ManuscriptStatus.REJECTED
            elif "revision" in status_text:
                status = ManuscriptStatus.REVISION_REQUESTED
            # else: UNDER_REVIEW (default)
        except:
            pass

        # Extract authors
        authors = []
        try:
            # Find author table/section
            author_elems = self.driver.find_elements(
                By.XPATH,
                "//td[contains(text(), 'Author')]/ancestor::table[1]//tr"
            )

            for author_row in author_elems[1:]:  # Skip header
                cells = author_row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    name = cells[0].text.strip()
                    email = cells[1].text.strip() if len(cells) > 1 else ""

                    if name:
                        authors.append(Author(
                            name=name,
                            email=email if email else None,
                        ))
        except:
            self.logger.warning(f"Could not extract authors for {manuscript_id}")

        # Create manuscript object with real data
        manuscript = Manuscript(
            journal_id=self.config.journal_id,
            external_id=manuscript_id,
            title=title,
            status=status,
            authors=authors,
            submission_date=submission_date,
        )

        self.logger.info(f"✅ Extracted: {title[:50]}...")
        return manuscript

    except Exception as e:
        self.logger.error(f"Error extracting {manuscript_id}: {e}")
        return Manuscript(
            journal_id=self.config.journal_id,
            external_id=manuscript_id,
            title=f"Error extracting {manuscript_id}",
            status=ManuscriptStatus.UNDER_REVIEW,
        )
```

**Testing**:
```python
async def test():
    async with MORAdapter(headless=False) as adapter:
        if await adapter.authenticate() and await adapter.navigate_to_ae_center():
            manuscripts = await adapter.fetch_manuscripts(["Awaiting AE Recommendation"])

            print(f"\n✅ Fetched {len(manuscripts)} manuscripts:")
            for m in manuscripts:
                print(f"\nID: {m.external_id}")
                print(f"Title: {m.title}")
                print(f"Authors: {len(m.authors)}")
                print(f"Status: {m.status}")

asyncio.run(test())
```

---

### Phase B.3: Referee Extraction (4-6 hours)

**Goal**: Extract complete referee data for each manuscript

**This is complex** - requires popup handling, email extraction, status parsing

**Recommended approach**: Port from production `mf_extractor_nopopup.py` lines 2500-3500

**Key steps**:
1. Find referee table on manuscript page
2. For each referee row, extract name, affiliation, status
3. Click email popup links to get emails
4. Parse dates (invited, agreed, due)
5. Extract recommendations/scores

**This is the most time-consuming phase** - estimate 6+ hours

---

### Phase B.4: Report Downloads (3-4 hours)

**Goal**: Download referee report PDFs

**Key steps**:
1. Find report links in referee table
2. Click report link (opens popup)
3. Switch to popup window
4. Find PDF download link
5. Download to `downloads/` directory
6. Switch back to main window

---

## 📊 Time Estimates Summary

| Task | Estimated Time | Complexity |
|------|---------------|------------|
| **Track A: Production Restore** | **1-2 hours** | Low |
| A.1: Gmail OAuth Setup | 30-45 min | Low |
| A.2: Test MOR | 15 min | Low |
| A.3: Test MF | 15 min | Low |
| | | |
| **Track B: ECC Implementation** | **15-20 hours** | High |
| B.1: Navigation | 4-6 hours | Medium |
| B.2: Manuscript Fetching | 4-6 hours | Medium-High |
| B.3: Referee Extraction | 6-8 hours | High |
| B.4: Report Downloads | 3-4 hours | Medium |

---

## 🎯 Success Criteria

### Track A Success
- ✅ Gmail OAuth configured (files created)
- ✅ MOR extractor runs without errors
- ✅ MF extractor extracts manuscripts with data
- ✅ Output JSON files created

### Track B Success
- ✅ Authentication returns True only when logged in
- ✅ Navigation reaches AE Center
- ✅ Categories detected and listed
- ✅ Manuscripts fetched with real data (not placeholders)
- ✅ Referees extracted with emails, status, dates
- ✅ Reports downloaded as PDFs
- ✅ Output matches production format

---

## 📝 Recommended Approach

### Week 1
- ✅ Complete Track A (production restore) - **Priority 1**
- ✅ Phase B.1 (navigation fixes) - **Priority 2**

### Week 2
- Phase B.2 (manuscript fetching)
- Start Phase B.3 (referee extraction)

### Week 3
- Complete Phase B.3
- Phase B.4 (report downloads)
- Testing and validation

---

## 🔄 Incremental Testing Strategy

**After each task**:
1. Write a small test script
2. Run with `headless=False` to watch browser
3. Verify expected behavior
4. Fix issues before moving to next task

**Don't batch multiple tasks** before testing - this makes debugging much harder.

---

## 📌 Important Notes

### For Track A
- Gmail OAuth setup requires browser interaction
- Test extractors with real credentials
- Verify output files are created and contain data

### For Track B
- Use production code as reference (don't rewrite from scratch)
- Test each phase incrementally
- Keep `headless=False` during development to see what's happening
- XPath selectors may differ between MF and MOR - be flexible

---

**Plan Created**: October 4, 2025
**Next Step**: Execute Track A to restore production extractors
**Long-term**: Execute Track B to complete ECC implementation

---

**END OF IMPLEMENTATION PLAN**
