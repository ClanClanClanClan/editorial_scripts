# SICON Parser Analysis - Current Issues and Solutions

## What the Parser is Currently Doing Wrong

### 1. **Navigation Issues**
The current parser is trying to go directly to manuscript pages without properly navigating through the category links:
- ❌ Going directly to individual manuscript URLs
- ❌ Missing the main category navigation (Under Review, All Pending, etc.)
- ❌ Not clicking on "number AE" links to get manuscript lists

### 2. **Referee Extraction Problems**

#### Duplication Issue
The parser calls three separate methods that create duplicates:
```python
referees.extend(await self._extract_active_referees_enhanced(soup, content))     # Finding same referees
referees.extend(await self._extract_inactive_referees_enhanced(soup, content))    # Finding same referees again
referees.extend(await self._extract_referee_suggestions_enhanced(soup, content))  # Finding same referees third time
```

Result: Each referee appears 3 times instead of once.

#### Status Parsing Failure
The parser is not distinguishing between two critical sections:
- ❌ Not recognizing "Potential Referees" = DECLINED referees
- ❌ Not recognizing "Referees" = ACCEPTED referees
- ❌ Defaulting everything to "Review pending" status

Current output:
```
All referees show status: "Review pending"
```

Expected output:
```
Potential Referees section → Status: "Declined"
Referees section with "Rcvd:" → Status: "Report submitted"
Referees section with "Due:" → Status: "Accepted, awaiting report"
```

### 3. **Missing Data**
The parser is failing to extract:
- ❌ Contact dates from "Last Contact Date: YYYY-MM-DD"
- ❌ Report received dates from "Rcvd: YYYY-MM-DD"
- ❌ Due dates from "Due: YYYY-MM-DD"
- ❌ Proper status differentiation

### 4. **PDF Download Issues**
- Found 0 PDFs when there should be manuscript PDFs and referee reports
- Not properly parsing the "Manuscript Items" section

## What Needs to Be Fixed

### 1. **Proper Navigation Flow**
```python
# Step 1: Navigate to main page after login
await page.goto(f"{base_url}/cgi-bin/sicon/main.plex")

# Step 2: Find and click category links with count > 0
categories = [
    "Under Review",
    "All Pending Manuscripts",
    "Waiting for Revision"
]

for category in categories:
    link = await page.query_selector(f'a:has-text("{category}"):has-text("AE")')
    if link:
        # Extract count
        text = await link.inner_text()
        count = int(re.search(r'(\d+)\s*AE', text).group(1))
        if count > 0:
            await link.click()
            # Process manuscript list
```

### 2. **Correct Referee Parsing**
```python
# Parse Potential Referees (DECLINED)
potential_referees_section = soup.find('td', text='Potential Referees')
if potential_referees_section:
    # All referees in this section have Status: Declined
    for referee_link in potential_referees_section.find_next_siblings('a'):
        referee = parse_referee(referee_link)
        referee.status = "Declined"
        referee.declined = True

# Parse Active Referees (ACCEPTED)
referees_section = soup.find('td', text='Referees')
if referees_section:
    # Parse based on Rcvd/Due dates
    for referee_entry in referees_section.find_next_siblings():
        if "Rcvd:" in referee_entry.text:
            referee.status = "Report submitted"
            referee.report_submitted = True
            referee.report_date = extract_date("Rcvd:")
        elif "Due:" in referee_entry.text:
            referee.status = "Accepted, awaiting report"
            referee.due_date = extract_date("Due:")
```

### 3. **Deduplication**
Use a single extraction method that properly identifies unique referees:
```python
unique_referees = {}
for referee in all_extracted_referees:
    key = (referee.email.upper(), referee.name)
    if key not in unique_referees:
        unique_referees[key] = referee
```

### 4. **Complete Timeline Extraction**
Extract all temporal data:
- Contact dates from "Last Contact Date: YYYY-MM-DD"
- Decline dates (same as contact date for declined)
- Acceptance dates (when status changes to accepted)
- Due dates from "Due: YYYY-MM-DD"
- Submission dates from "Rcvd: YYYY-MM-DD"

## Expected Results After Fix

For manuscript M172838:
```json
{
  "referees": [
    // Declined referees (from Potential Referees section)
    {
      "name": "Samuel Daudin",
      "email": "SAMUEL.DAUDIN@UNIV-COTEDAZUR.FR",
      "status": "Declined",
      "contact_date": "2025-02-04",
      "declined": true
    },
    // ... 4 more declined referees

    // Accepted referees (from Referees section)
    {
      "name": "Giorgio Ferrari",
      "email": "[extracted from biblio page]",
      "status": "Report submitted",
      "report_submitted": true,
      "report_date": "2025-06-02"
    },
    {
      "name": "Juan Li",
      "email": "JUANLI@SDU.EDU.CN",
      "status": "Accepted, awaiting report",
      "due_date": "2025-04-17",
      "report_submitted": false
    }
  ]
}
```

Total: 7 unique referees (5 declined + 2 accepted), not 44 duplicates!
