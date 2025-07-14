# Comprehensive Referee Analytics System

## Overview
A complete referee analytics system has been built that extracts detailed referee timelines, downloads all documents, and cross-references with Gmail for all 4 journals (SICON, SIFIN, MF, MOR).

## Key Features

### 1. Enhanced Referee Data Extraction
The system extracts comprehensive referee information including:
- **Names and emails** of all referees
- **Contact/invitation dates** - when referees were first invited
- **Acceptance dates** - when they agreed to review
- **Decline dates** - when they refused
- **Due dates** - review deadlines
- **Submission dates** - when reports were submitted
- **Email counts** - number of invitations and reminders sent
- **Response times** - days from invitation to response
- **Review times** - days from acceptance to submission

### 2. Complete Document Downloads
The system downloads ALL available documents:
- **Manuscript PDFs** - all versions available
- **Cover letters** - when provided
- **Referee reports** - all submitted reviews
- **Other documents** - any additional PDFs

Documents are organized by:
```
~/.editorial_scripts/documents/
├── manuscripts/[journal]/[manuscript_id]/
│   ├── manuscript_*.pdf
│   ├── cover_letter.pdf
│   └── document_*.pdf
└── referee_reports/[journal]/[manuscript_id]/
    └── referee_report_*.pdf
```

### 3. Gmail Integration & Cross-Checking
The system integrates with Gmail to:
- **Verify email counts** - cross-check invitation/reminder counts
- **Find missing referees** - detect referees only in emails
- **Build complete timelines** - merge email events with scraped data
- **Track communication patterns** - analyze email threads

### 4. Comprehensive Analytics
The system generates detailed analytics including:

#### Overall Statistics
- Total and unique referee counts
- Report submission rates
- Gmail verification status
- Document download totals

#### Journal-Specific Metrics
- Referee acceptance rates
- Completion rates
- Average response times
- Average review times
- Email communication patterns

#### Referee Performance Tracking
- Top performing referees (by completion rate)
- Problem referees (overdue, slow response, many reminders)
- Cross-journal referee participation

## System Components

### Core Analytics Module
`src/core/referee_analytics.py`
- `RefereeTimeline` - Complete timeline for each referee
- `RefereeEvent` - Individual events (invited, accepted, submitted, etc.)
- `RefereeAnalytics` - Analytics aggregator and calculator

### Gmail Integration
`src/infrastructure/gmail_integration.py`
- `GmailRefereeTracker` - Searches and analyzes referee emails
- Pattern matching for referee communications
- Email timeline construction

### Enhanced Extractor
`src/infrastructure/scrapers/enhanced_referee_extractor.py`
- `EnhancedRefereeExtractor` - Detailed timeline extraction
- Document download functionality
- Support for both SIAM and ScholarOne platforms

### Main Runner
`run_comprehensive_referee_analytics.py`
- Orchestrates the complete analysis
- Processes all 4 journals
- Generates comprehensive reports

## Usage

### Prerequisites
1. Install required packages:
   ```bash
   pip install playwright aiohttp aiofiles google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client beautifulsoup4
   ```

2. Set up credentials:
   ```python
   # In environment or script
   os.environ['ORCID_EMAIL'] = 'your_email'
   os.environ['ORCID_PASSWORD'] = 'your_password'
   
   # For MF/MOR (optional)
   os.environ['SCHOLARONE_USER'] = 'your_username'
   os.environ['SCHOLARONE_PASS'] = 'your_password'
   ```

3. (Optional) Set up Gmail integration - see GMAIL_SETUP.md

### Running the Analysis
```bash
python run_comprehensive_referee_analytics.py
```

## Output

### Analytics Reports
Generated in `~/.editorial_scripts/analytics/`:

1. **Main Report** - `referee_analytics_report_[timestamp].json`
   - Overall statistics
   - Journal breakdowns
   - Top/problem referees
   - Document statistics

2. **Detailed Data** - `referee_details_[timestamp].json`
   - Complete referee timelines
   - All events with timestamps
   - Email verification status

3. **Missing Referees** - `missing_referees_from_gmail.json`
   - Referees found only in emails
   - Potential data gaps

### Example Analytics Output
```json
{
  "overall_statistics": {
    "total_referees": 145,
    "unique_referees": 98,
    "total_reports": 87,
    "gmail_verified": 76
  },
  "journal_statistics": {
    "SICON": {
      "total_referees": 42,
      "acceptance_rate": 71.4,
      "completion_rate": 83.3,
      "avg_response_time_days": 3.2,
      "avg_review_time_days": 18.5,
      "avg_invitation_emails": 1.2,
      "avg_reminder_emails": 0.8
    }
  },
  "document_statistics": {
    "total_manuscripts": 156,
    "total_cover_letters": 117,
    "total_referee_reports": 87
  }
}
```

## Key Insights Provided

### Referee Performance
- Who are the most reliable referees?
- Which referees consistently deliver on time?
- Who requires multiple reminders?
- Cross-journal referee participation

### Process Efficiency
- How many emails does it take to get a review?
- What are typical response times?
- Where are the bottlenecks?
- Which journals have better referee engagement?

### Document Completeness
- Are all referee reports being downloaded?
- Which manuscripts have complete documentation?
- Cover letter submission rates

### Data Quality
- How much data is Gmail-verified?
- Are there referees we're missing?
- Timeline completeness

## Advanced Features

### Timeline Reconstruction
The system builds complete referee timelines by:
1. Extracting dates from journal websites
2. Parsing email communications
3. Merging both data sources
4. Identifying gaps and inconsistencies

### Pattern Recognition
- Identifies referee behavior patterns
- Detects systematic issues
- Flags anomalies for investigation

### Cross-Platform Support
- Works with SIAM platform (SICON/SIFIN)
- Works with ScholarOne platform (MF/MOR)
- Unified analytics across platforms

## Maintenance & Updates

### Adding New Patterns
Email patterns can be extended in `GmailRefereeTracker.REFEREE_PATTERNS`

### Customizing Analytics
New metrics can be added to `RefereeAnalytics` class

### Platform Support
New journal platforms can be supported by implementing appropriate methods in `EnhancedRefereeExtractor`

## Limitations

1. **2FA on ScholarOne** - Requires manual intervention
2. **Gmail API Quotas** - Limited to 250 quota units per user per second
3. **Historical Data** - Limited by email retention and journal access
4. **Document Access** - Some documents may require special permissions

## Future Enhancements

1. **Automated 2FA Handling** - Integration with authenticator apps
2. **Real-time Monitoring** - Webhook integration for new submissions
3. **Predictive Analytics** - ML models for referee behavior prediction
4. **Dashboard UI** - Web interface for analytics visualization
5. **Automated Reporting** - Scheduled reports and alerts

## Conclusion

This comprehensive system provides unprecedented visibility into the referee process across all journals, enabling data-driven decisions for:
- Referee selection
- Process optimization  
- Performance management
- Quality improvement

The combination of web scraping, document management, and email integration creates a complete picture of the editorial process that was previously impossible to obtain.