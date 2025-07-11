# Referee Extraction System - COMPLETE ✅

## What Has Been Built

A fully automated weekly extraction system that:

1. **Extracts all referee data** from ScholarOne Manuscripts for MF and MOR journals
2. **Downloads PDFs intelligently** - only downloads new PDFs, tracks what's already downloaded
3. **Creates weekly digests** for email updates
4. **Runs automatically** via cron job (optional)

## How to Use It

### Run Weekly Extraction (This is all you need!)
```bash
python3 run_weekly_extraction.py
```

This single command will:
- Extract all referee data for both journals
- Download any new PDFs (manuscripts and referee reports)
- Create an email digest
- Save everything organized by week
- Clean up old data (keeps last 4 weeks)

### Check What's Been Downloaded
```bash
python3 run_weekly_extraction.py --check-only
```

### Set Up Automatic Weekly Runs
```bash
./setup_weekly_cron.sh
# Then follow the instructions to add to crontab
```

## What You Get

### 1. Referee Information ✅
- Names, emails, institutions
- All dates (invited, agreed, due, review returned)
- Status tracking (active vs completed)
- Email dates from Gmail
- Time in review

### 2. Manuscript Information ✅
- IDs, titles, due dates
- Submission status
- Completed review decisions

### 3. PDFs (When Available)
- Manuscript PDFs
- Referee report PDFs
- Smart tracking to avoid re-downloads

### 4. Weekly Email Digest
Located at: `weekly_extractions/[YEAR]_week_[WEEK]/email_digest.txt`

Perfect for copying into your weekly email updates!

## Key Features

- **Once per week is enough**: The system is designed for weekly runs
- **PDFs downloaded once**: The system tracks what's been downloaded
- **Organized storage**: Everything is organized by week and type
- **Automatic cleanup**: Old extraction data is cleaned up automatically
- **Resilient**: If something fails, it continues with what it can do

## File Locations

- **This week's results**: `weekly_extractions/2025_week_28/`
- **Email digest**: `weekly_extractions/2025_week_28/email_digest.txt`
- **All PDFs**: `referee_pdfs/`
- **Download history**: `weekly_extractions/download_tracker.json`

## Important Notes

1. **First run will take longer** as it downloads all PDFs
2. **Subsequent runs are faster** as they only download new PDFs
3. **PDFs are permanent** - they're never automatically deleted
4. **Extraction data is temporary** - kept for 4 weeks only

The system is now complete and ready for use! 🎉