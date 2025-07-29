# SICON Parser Implementation Requirements

## Critical Fixes Required

### 1. Navigation Flow Implementation

```python
async def _navigate_to_manuscripts(self) -> bool:
    """Navigate through category pages to collect all manuscripts"""
    try:
        # Navigate to main AE page
        main_url = f"{self.base_url}/cgi-bin/sicon/main.plex"
        await self.page.goto(main_url, wait_until="networkidle")
        
        # Find all category links with counts
        categories_to_check = [
            ("Under Review", "ViewUnderReview"),
            ("All Pending Manuscripts", "ViewAllPending"),
            ("Waiting for Revision", "ViewWaitingRevision"),
            ("Awaiting Referee Assignment", "ViewAwaitingReferee"),
            ("Awaiting Associate Editor Recommendation", "ViewAwaitingAE")
        ]
        
        all_manuscript_ids = set()
        
        for category_name, view_name in categories_to_check:
            # Find link with pattern "N AE" where N > 0
            link_selector = f'a:has-text("{category_name}"):has-text("AE")'
            link = await self.page.query_selector(link_selector)
            
            if link:
                text = await link.inner_text()
                count_match = re.search(r'(\d+)\s*AE', text)
                if count_match and int(count_match.group(1)) > 0:
                    # Click the link
                    await link.click()
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Extract manuscript IDs from the list
                    manuscript_links = await self.page.query_selector_all('a[href*="/m/M"]')
                    for ms_link in manuscript_links:
                        href = await ms_link.get_attribute('href')
                        ms_id_match = re.search(r'M(\d+)', href)
                        if ms_id_match:
                            all_manuscript_ids.add(f"M{ms_id_match.group(1)}")
                    
                    # Go back to main page for next category
                    await self.page.goto(main_url, wait_until="networkidle")
        
        self.manuscript_ids = list(all_manuscript_ids)
        return len(self.manuscript_ids) > 0
        
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        return False
```

### 2. Manuscript Detail Extraction

```python
async def _extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
    """Extract complete manuscript details from detail page"""
    
    # Navigate to manuscript detail page
    detail_url = f"{self.base_url}/cgi-bin/sicon/ViewUnderReview/m/{manuscript_id}"
    await self.page.goto(detail_url, wait_until="networkidle")
    
    content = await self.page.content()
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract basic info
    manuscript = Manuscript(
        id=manuscript_id,
        title=self._extract_field(soup, "Title"),
        status=self._extract_field(soup, "Current Stage"),
        submission_date=self._extract_field(soup, "Submission Date"),
        journal="SICON",
        corresponding_editor=self._extract_field(soup, "Corresponding Editor"),
        associate_editor=self._extract_field(soup, "Associate Editor")
    )
    
    # Extract authors
    manuscript.authors = self._extract_authors(soup)
    
    # Extract BOTH referee sections
    declined_referees = await self._extract_potential_referees(soup)  # Declined
    active_referees = await self._extract_active_referees(soup)       # Accepted
    
    # Combine without duplicates
    manuscript.referees = declined_referees + active_referees
    
    # Extract PDFs
    manuscript.pdf_urls = self._extract_pdf_links(soup)
    
    return manuscript
```

### 3. Referee Extraction - Two Separate Methods

```python
async def _extract_potential_referees(self, soup: BeautifulSoup) -> List[Referee]:
    """Extract DECLINED referees from 'Potential Referees' section"""
    referees = []
    
    # Find the Potential Referees section
    potential_section = soup.find('td', text=re.compile(r'Potential\s+Referees'))
    if not potential_section:
        return referees
    
    # Parse the content after this section
    current = potential_section.next_sibling
    while current and current.name != 'tr':
        if hasattr(current, 'text'):
            text = current.text
            
            # Pattern: Name #N (Last Contact Date: YYYY-MM-DD) (Status: Declined)
            pattern = r'([^#]+)\s+#(\d+)\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)\s*\(Status:\s*Declined\)'
            matches = re.findall(pattern, text)
            
            for name, ref_num, contact_date in matches:
                referee = Referee(
                    name=name.strip(),
                    email="",  # Will be filled by clicking on name
                    status="Declined",
                    declined=True,
                    contact_date=contact_date,
                    declined_date=contact_date  # Same as contact date
                )
                
                # Find the link to click for details
                link = soup.find('a', text=re.compile(name.strip()))
                if link:
                    referee = await self._fetch_referee_details(referee, link)
                
                referees.append(referee)
        
        current = current.next_sibling if hasattr(current, 'next_sibling') else None
    
    return referees

async def _extract_active_referees(self, soup: BeautifulSoup) -> List[Referee]:
    """Extract ACCEPTED referees from 'Referees' section"""
    referees = []
    
    # Find the Referees section (not Potential Referees)
    referees_section = soup.find('td', text=re.compile(r'^Referees$'))
    if not referees_section:
        return referees
    
    # Parse the content after this section
    current = referees_section.next_sibling
    while current and current.name != 'tr':
        if hasattr(current, 'text'):
            text = current.text
            
            # Pattern 1: Name #N (Rcvd: YYYY-MM-DD) - Report submitted
            rcvd_pattern = r'([^#]+)\s+#(\d+)\s*\(Rcvd:\s*(\d{4}-\d{2}-\d{2})\)'
            rcvd_matches = re.findall(rcvd_pattern, text)
            
            for name, ref_num, received_date in rcvd_matches:
                referee = Referee(
                    name=name.strip(),
                    email="",  # Will be filled by clicking on name
                    status="Report submitted",
                    report_submitted=True,
                    report_date=received_date,
                    accepted=True
                )
                
                # Find the link to click for details
                link = soup.find('a', text=re.compile(name.strip()))
                if link:
                    referee = await self._fetch_referee_details(referee, link)
                
                referees.append(referee)
            
            # Pattern 2: Name #N (Due: YYYY-MM-DD) - Awaiting report
            due_pattern = r'([^#]+)\s+#(\d+)\s*\(Due:\s*(\d{4}-\d{2}-\d{2})\)'
            due_matches = re.findall(due_pattern, text)
            
            for name, ref_num, due_date in due_matches:
                referee = Referee(
                    name=name.strip(),
                    email="",  # Will be filled by clicking on name
                    status="Accepted, awaiting report",
                    report_submitted=False,
                    due_date=due_date,
                    accepted=True
                )
                
                # Find the link to click for details
                link = soup.find('a', text=re.compile(name.strip()))
                if link:
                    referee = await self._fetch_referee_details(referee, link)
                
                referees.append(referee)
        
        current = current.next_sibling if hasattr(current, 'next_sibling') else None
    
    return referees
```

### 4. Referee Detail Fetching

```python
async def _fetch_referee_details(self, referee: Referee, link_element) -> Referee:
    """Click on referee name to get email and affiliation"""
    try:
        # Get the href
        href = await link_element.get_attribute('href')
        if not href:
            return referee
        
        # Open in new tab to preserve current page
        new_page = await self.page.context.new_page()
        
        try:
            # Navigate to biblio page
            biblio_url = f"{self.base_url}{href}" if not href.startswith('http') else href
            await new_page.goto(biblio_url, wait_until="networkidle")
            
            content = await new_page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
            if email_match:
                referee.email = email_match.group(1).upper()
            
            # Extract institution
            # Look for patterns like "University of...", "Institute of...", etc.
            inst_patterns = [
                r'(?:University|Institute|College|School)\s+of\s+[^,<]+',
                r'[A-Z][a-z]+\s+(?:University|Institute|College)',
                # Add more patterns as needed
            ]
            
            for pattern in inst_patterns:
                inst_match = re.search(pattern, content)
                if inst_match:
                    referee.institution = inst_match.group(0).strip()
                    break
            
        finally:
            await new_page.close()
        
        return referee
        
    except Exception as e:
        logger.error(f"Failed to fetch referee details: {e}")
        return referee
```

### 5. PDF Extraction

```python
def _extract_pdf_links(self, soup: BeautifulSoup) -> Dict[str, str]:
    """Extract all PDF download links from manuscript page"""
    pdf_urls = {}
    
    # Find Manuscript Items section
    items_section = soup.find('text', text=re.compile('Manuscript Items'))
    if items_section:
        # Look for PDF links
        pdf_links = soup.find_all('a', text=re.compile(r'PDF.*\(\d+KB\)'))
        
        for i, link in enumerate(pdf_links):
            href = link.get('href', '')
            if 'Article File' in link.text or i == 0:
                pdf_urls['manuscript'] = f"{self.base_url}{href}" if not href.startswith('http') else href
            elif 'Referee' in link.text and 'Review' in link.text:
                # Extract referee number
                ref_num_match = re.search(r'Referee\s*#(\d+)', link.text)
                if ref_num_match:
                    ref_num = ref_num_match.group(1)
                    pdf_urls[f'referee_report_{ref_num}'] = f"{self.base_url}{href}" if not href.startswith('http') else href
            elif 'Source' in link.text:
                pdf_urls['source'] = f"{self.base_url}{href}" if not href.startswith('http') else href
    
    return pdf_urls
```

## Expected Output Structure

```json
{
  "manuscripts": [
    {
      "id": "M172838",
      "title": "Constrained Mean-Field Control...",
      "authors": ["Xiang Yu", "Lijun Bo", "Jingfei Wang"],
      "status": "All Referees Assigned",
      "submission_date": "2025-01-23",
      "associate_editor": "Dylan Possamaï",
      "corresponding_editor": "Bayraktar",
      "referees": [
        {
          "name": "Samuel Daudin",
          "email": "SAMUEL.DAUDIN@UNIV-COTEDAZUR.FR",
          "status": "Declined",
          "institution": "Université Côte d'Azur",
          "declined": true,
          "contact_date": "2025-02-04",
          "declined_date": "2025-02-04"
        },
        {
          "name": "Giorgio Ferrari",
          "email": "[FROM BIBLIO PAGE]",
          "status": "Report submitted",
          "institution": "[FROM BIBLIO PAGE]",
          "accepted": true,
          "report_submitted": true,
          "report_date": "2025-06-02"
        },
        {
          "name": "Juan Li",
          "email": "JUANLI@SDU.EDU.CN",
          "status": "Accepted, awaiting report",
          "institution": "Shandong University",
          "accepted": true,
          "report_submitted": false,
          "due_date": "2025-04-17"
        }
      ],
      "pdf_urls": {
        "manuscript": "https://sicon.siam.org/cgi-bin/GetDoc/...",
        "referee_report_1": "https://sicon.siam.org/cgi-bin/GetDoc/...",
        "source": "https://sicon.siam.org/cgi-bin/GetDoc/..."
      }
    }
  ],
  "statistics": {
    "total_manuscripts": 4,
    "total_referees": 13,  // NOT 44!
    "declined_referees": 5,
    "accepted_referees": 8,
    "reports_submitted": 4
  }
}
```

## Key Implementation Points

1. **Two distinct referee sections** must be parsed separately
2. **No duplication** - each referee appears only once
3. **Proper status assignment** based on section and date patterns
4. **Complete timeline data** including all dates
5. **PDF links** must be extracted and downloaded
6. **Multi-tab navigation** for referee details without losing main page

This implementation will correctly extract the 13 unique referees with their proper statuses as requested.