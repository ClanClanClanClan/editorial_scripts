# Weekly Referee Extraction System

A comprehensive system for extracting referee data from ScholarOne Manuscripts and downloading associated PDFs. The system tracks what has been downloaded to avoid re-downloading files.

## Features

- **Automated Weekly Extraction**: Extracts referee data for MF and MOR journals
- **Smart PDF Management**: Only downloads PDFs that haven't been downloaded before
- **Email Integration**: Matches referee acceptance/contact dates from Gmail
- **Progress Tracking**: Maintains history of all downloads
- **Email Digest**: Creates a concise summary for weekly email updates
- **Automatic Cleanup**: Removes old extraction data (keeps last 4 weeks)

## System Components

1. **`run_weekly_extraction.py`** - Main script to run (this is what you execute weekly)
2. **`weekly_extraction_system.py`** - Core extraction orchestration
3. **`final_working_referee_extractor.py`** - Proven referee data extraction
4. **`smart_pdf_downloader.py`** - Intelligent PDF download manager
5. **`setup_weekly_cron.sh`** - Script to set up automated weekly runs

## Directory Structure

```
editorial_scripts/
├── weekly_extractions/         # Weekly extraction results
│   ├── 2025_week_28/          # Results for week 28 of 2025
│   │   ├── mf/                # MF journal data
│   │   ├── mor/               # MOR journal data
│   │   ├── email_digest.txt   # Summary for emailing
│   │   └── final_summary.txt  # Complete summary
│   └── download_tracker.json  # Tracks all downloaded PDFs
├── referee_pdfs/              # Permanent PDF storage
│   ├── manuscript/            # Manuscript PDFs
│   │   └── 2025/07/          # Organized by year/month
│   └── report/                # Referee report PDFs
└── logs/                      # Execution logs
```

## Usage

### Manual Weekly Run

```bash
python3 run_weekly_extraction.py
```

### Check Current Status

```bash
python3 run_weekly_extraction.py --check-only
```

### Set Up Automated Weekly Runs

```bash
./setup_weekly_cron.sh
```

Then add the suggested cron entry to run every Monday at 9 AM.

## What Gets Extracted

### Referee Information
- Name, email, institution
- Status (agreed, declined, completed)
- All dates (invited, agreed, due, review returned)
- Time in review
- Acceptance/contact dates from Gmail
- Review decisions for completed referees

### Manuscript Information
- Manuscript ID and title
- Submission and due dates
- Current status
- Authors (when available)
- Abstract and keywords (when available)

### PDFs
- Manuscript PDFs (when available)
- Referee report PDFs (for completed reviews)

## PDF Download Tracking

The system maintains a `download_tracker.json` file that records:
- Which PDFs have been downloaded
- When they were downloaded
- Where they are stored
- File sizes

This ensures PDFs are only downloaded once, saving time and bandwidth.

## Email Digest

Each week, an `email_digest.txt` file is created containing:
- Active manuscripts with pending reviews
- Referee names and contact information
- Days since referee acceptance
- Due dates

This file is designed to be copied into a weekly email update.

## Troubleshooting

### Login Issues
- Ensure Gmail API credentials are properly configured
- Check that verification emails are being received
- Verify ScholarOne login credentials in journal files

### PDF Download Failures
- PDFs require an active session - they cannot be downloaded separately
- Some PDFs may not be available through the interface
- Check `download_tracker.json` for already downloaded files

### Missing Data
- Authors/abstract/keywords require navigating to "View Submission"
- Not all manuscripts have PDFs available
- Completed referee reports may not always have downloadable PDFs

## Maintenance

- Old extraction directories are automatically cleaned up (keeps last 4 weeks)
- PDFs are stored permanently and never deleted automatically
- Check logs in the `logs/` directory for troubleshooting

## Future Enhancements

- Direct "View Submission" navigation for complete manuscript details
- Automated email sending of weekly digest
- Web dashboard for viewing extraction history
- API endpoint for integration with other systems