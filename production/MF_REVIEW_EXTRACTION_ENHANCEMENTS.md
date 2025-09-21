# MF Review Extraction Enhancements

## Current Implementation Status ✅

### What We Already Extract:
1. **Review Reports** via `extract_referee_report_from_link()`:
   - Comments to Editor (confidential)
   - Comments to Author
   - PDF attachments (referee reports)
   - Basic recommendation text

2. **Review Popup Content** via `extract_review_popup_content()`:
   - Full review text
   - Review scores/ratings
   - Recommendation
   - Review dates
   - Status history

3. **Structured Recommendations** via `parse_recommendation_from_popup()`:
   - Maps text to: accept/minor/major/reject
   - Searches both recommendation field and review text

## Enhancements Needed for Complete Review Extraction

### 1. Enhanced Status Parsing
When a review is received, the status cell shows "Review Received and Complete". We need to:

```python
def parse_referee_status_details(self, status_text):
    """Parse detailed status information from referee status cell."""
    status_info = {
        'status': status_text,
        'review_received': False,
        'review_complete': False,
        'invited_date': None,
        'agreed_date': None,
        'submitted_date': None,
        'review_score': None,
        'recommendation': None
    }

    # Check if review is received
    if 'Review Received' in status_text:
        status_info['review_received'] = True
        status_info['review_complete'] = 'Complete' in status_text

    # Extract dates from status cell or history
    # This would parse the detailed timeline

    return status_info
```

### 2. Review Score Extraction
MF may show review scores in the format:
- Overall Rating: 4/5
- Technical Quality: Excellent
- Originality: Good
- Clarity: Fair

```python
def extract_review_scores(self, review_content):
    """Extract structured review scores from review content."""
    scores = {
        'overall_rating': None,
        'technical_quality': None,
        'originality': None,
        'clarity': None,
        'significance': None
    }

    # Pattern matching for scores
    score_patterns = {
        'overall': r'Overall\s*Rating:\s*(\d+)[/\\](\d+)',
        'technical': r'Technical\s*Quality:\s*(\w+)',
        'originality': r'Originality:\s*(\w+)',
        'clarity': r'Clarity:\s*(\w+)'
    }

    for key, pattern in score_patterns.items():
        match = re.search(pattern, review_content, re.IGNORECASE)
        if match:
            scores[key] = match.group(1)

    return scores
```

### 3. Decision Extraction from Review Text
Enhanced parsing to extract specific editorial decisions:

```python
def extract_editorial_decision(self, review_text):
    """Extract specific editorial decision from review text."""
    decision_patterns = {
        'accept_as_is': [
            'accept as is',
            'ready for publication',
            'no changes needed',
            'publish without revision'
        ],
        'minor_revision': [
            'minor revision',
            'minor changes',
            'small corrections',
            'light revision'
        ],
        'major_revision': [
            'major revision',
            'substantial changes',
            'significant revision',
            'extensive revision'
        ],
        'reject': [
            'reject',
            'not suitable',
            'do not publish',
            'recommend against publication'
        ],
        'reject_with_resubmission': [
            'reject but encourage resubmission',
            'reject with invitation to resubmit',
            'too preliminary'
        ]
    }

    text_lower = review_text.lower()

    for decision, patterns in decision_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                return decision

    return 'unclear'
```

### 4. Review Timeline Extraction
Extract the complete review timeline from the history column:

```python
def extract_review_timeline(self, history_cell):
    """Extract complete review timeline with all key dates."""
    timeline = {
        'invitation_sent': None,
        'invitation_viewed': None,
        'agreed_to_review': None,
        'review_submitted': None,
        'review_modified': None,
        'reminder_sent': [],
        'total_days_to_review': None
    }

    # Parse date entries from history
    date_entries = history_cell.find_elements(By.XPATH, ".//tr")

    for entry in date_entries:
        text = entry.text.strip()

        # Match different event types
        if 'Invited:' in text:
            timeline['invitation_sent'] = self.parse_date(text)
        elif 'Agreed:' in text:
            timeline['agreed_to_review'] = self.parse_date(text)
        elif 'Review Submitted:' in text:
            timeline['review_submitted'] = self.parse_date(text)
        elif 'Reminder' in text:
            timeline['reminder_sent'].append(self.parse_date(text))

    # Calculate review duration
    if timeline['agreed_to_review'] and timeline['review_submitted']:
        delta = timeline['review_submitted'] - timeline['agreed_to_review']
        timeline['total_days_to_review'] = delta.days

    return timeline
```

### 5. Enhanced Report PDF Processing
Extract text from downloaded referee report PDFs:

```python
def extract_text_from_referee_pdf(self, pdf_path):
    """Extract text content from referee report PDF."""
    try:
        import PyPDF2

        text_content = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            for page in pdf_reader.pages:
                text_content.append(page.extract_text())

        full_text = '\n'.join(text_content)

        # Extract key sections
        sections = {
            'summary': self.extract_section(full_text, 'Summary'),
            'major_comments': self.extract_section(full_text, 'Major Comments'),
            'minor_comments': self.extract_section(full_text, 'Minor Comments'),
            'recommendation': self.extract_section(full_text, 'Recommendation')
        }

        return sections

    except Exception as e:
        print(f"Could not extract PDF text: {e}")
        return None
```

### 6. Complete Review Data Structure
The enhanced review extraction would produce:

```json
{
  "referee": {
    "name": "John Smith",
    "email": "john.smith@university.edu",
    "affiliation": "University of Example",
    "status": "Review Received and Complete",
    "review_data": {
      "received": true,
      "submitted_date": "2025-01-15",
      "recommendation": "minor_revision",
      "scores": {
        "overall_rating": "4/5",
        "technical_quality": "Excellent",
        "originality": "Good",
        "clarity": "Good"
      },
      "comments_to_editor": "The paper is well-written...",
      "comments_to_author": "This is a solid contribution...",
      "timeline": {
        "invitation_sent": "2024-12-01",
        "agreed_to_review": "2024-12-05",
        "review_submitted": "2025-01-15",
        "total_days_to_review": 41
      },
      "pdf_reports": [
        {
          "name": "referee_report_1.pdf",
          "path": "downloads/referee_reports/M123_smith_report.pdf",
          "extracted_text": {
            "summary": "...",
            "major_comments": "...",
            "minor_comments": "..."
          }
        }
      ]
    }
  }
}
```

## Implementation Priority

1. **High Priority** (Already mostly implemented):
   - ✅ Basic review extraction
   - ✅ Popup content parsing
   - ✅ PDF download
   - ✅ Recommendation parsing

2. **Medium Priority** (Enhance existing):
   - 🔧 Enhanced status parsing (detect "Review Received")
   - 🔧 Score extraction from structured fields
   - 🔧 Complete timeline extraction

3. **Low Priority** (Nice to have):
   - 📄 PDF text extraction
   - 📊 Advanced analytics (review times, etc.)
   - 🤖 ML-based recommendation detection

## Testing Without Live Reviews

Since you don't have reviews received at the moment, the implementation is designed to:
1. Gracefully handle "no review" cases
2. Extract all available pre-review data (invitations, agreements)
3. Be ready to extract full review data when available
4. Use the HTML patterns you've documented for future reviews
