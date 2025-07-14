# Gmail Integration Setup Guide

## Overview
The comprehensive referee analytics system can cross-check referee data with your Gmail emails to:
- Verify invitation and reminder counts
- Find missing referees not captured by scraping
- Build complete communication timelines
- Track email response patterns

## Setup Steps

### 1. Enable Gmail API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and press "Enable"

### 2. Create Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields (app name, email)
   - Add your email to test users
4. For Application type, choose "Desktop app"
5. Name it "Editorial Scripts Gmail Integration"
6. Download the credentials JSON file
7. Save it as `credentials.json` in the editorial_scripts directory

### 3. First Run Authorization
When you first run the analytics with Gmail integration:
1. A browser window will open
2. Log in to your Gmail account
3. Grant permissions to read emails
4. The script will save `token.json` for future use

## What Gets Analyzed

The system searches for referee-related emails using these patterns:
- **Invitations**: "invitation to review", "referee invitation", "would you review"
- **Reminders**: "reminder", "review reminder", "overdue review"
- **Acceptances**: "agreed to review", "accepted to review"
- **Declines**: "declined to review", "unable to review"
- **Submissions**: "submitted review", "completed review"

## Privacy & Security

- The system only reads emails (no modification/deletion)
- Credentials are stored locally
- Only referee-related emails are processed
- Email content is analyzed but not stored permanently
- You can revoke access anytime from Google Account settings

## Search Scope

By default, the system searches:
- Last 6 months of emails
- To/From referee email addresses
- Containing manuscript IDs or journal codes
- Matching referee communication patterns

## Troubleshooting

### "Credentials not found" error
- Ensure `credentials.json` is in the correct directory
- Check file permissions

### "Token expired" error
- Delete `token.json` and re-authenticate
- The system will prompt for new authorization

### No emails found
- Check if referee emails are in Gmail
- Verify the email addresses match
- Ensure emails are within the date range

## Running Without Gmail

The system works without Gmail integration, you'll just miss:
- Email count verification
- Missing referee detection
- Gmail-based timeline events

To run without Gmail, simply don't include the `credentials.json` file.