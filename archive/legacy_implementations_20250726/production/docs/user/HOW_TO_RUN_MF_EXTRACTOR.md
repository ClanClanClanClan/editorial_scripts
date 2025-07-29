# How to Run the MF Extractor

## Prerequisites

1. **Secure Credential Storage** (Recommended): Store your MF credentials securely
   ```bash
   python3 ensure_credentials.py
   ```
   This will prompt you for your email and password and store them securely in macOS Keychain.
   You'll never need to enter them again!

2. **Alternative - Environment Variables**: If you prefer manual setup
   ```bash
   export MF_EMAIL="your-email@domain.com"
   export MF_PASSWORD="your-password"
   ```

3. **Python Dependencies**: Ensure you have all required packages
   ```bash
   pip install selenium webdriver-manager python-dotenv pyyaml requests beautifulsoup4
   ```

4. **Chrome Browser**: The extractor uses Chrome WebDriver

## Running the Extractor

### Method 1: Direct Execution (Recommended)
```bash
cd production
python3 mf_extractor.py
```
The extractor automatically loads your secure credentials and runs the extraction.

### Method 2: First-Time Setup
If you haven't stored credentials yet:
```bash
# Store credentials securely (one-time setup)
python3 ensure_credentials.py

# Then run the extractor
python3 mf_extractor.py
```

## What You'll See

The extractor will show detailed progress:

```
🚀 COMPREHENSIVE MF EXTRACTION
============================================================
✅ Configuration loaded from config/mf_config.json
🔐 Logging in...
   ✅ Login successful
🏠 Navigating to Associate Editor Center...
   ✅ Found Associate Editor Center
📊 Finding manuscript categories...
   📋 Found 3 categories with manuscripts

📄 PROCESSING MANUSCRIPT 1/2: MAFI-2025-0166
   📝 Basic Details:
      Title: Optimal investment and consumption under forward utilities...
      Status: Under Review
      Category: Awaiting Reviewer Selection
      
   🔍 Looking for Authors & Institutions section...
      ✅ Navigated to Manuscript Information tab
      ✅ Found 'Authors & Institutions' section
      📊 Found 3 potential author rows
      
      ✅ Author 1: Broux-Quemerais, Guillaume
         📧 Email: guillaume.broux97@gmail.com
         🏛️ Institution: Federation Recherche Mathematiques des Pays de Loire
         🌍 Country: France
         📝 Corresponding: False
         
      ✅ Author 2: Matoussi, Anis
         📧 Email: anis.matoussi@univ-lemans.fr
         🏛️ Institution: Federation Recherche Mathematiques des Pays de Loire
         🌍 Country: France
         🆔 ORCID: https://orcid.org/0000-0002-8814-9402
         📝 Corresponding: True
         
      ✅ Author 3: Zhou, Chao
         📧 Email: zccr333@gmail.com
         🏛️ Institution: National University of Singapore Risk Management Institute
         🌍 Country: Singapore
         📝 Corresponding: False
         
   👥 Extracting referee details from audit trail...
      🔍 Navigating to Audit Trail...
      ✅ Successfully navigated to Audit Trail
      📋 Found 4 reviewer invitation events
      📊 Found 2 reviewer_agreement events
      📊 Found 1 reviewer_decline events
      
      ✅ Processed referee: Dr. John Smith
      ✅ Processed referee: Prof. Jane Doe
      ✅ Processed referee: Dr. Bob Wilson
      ✅ Processed referee: Prof. Alice Johnson
      
      📊 Total referees extracted from audit trail: 4
      
   📁 Document extraction...
      ✅ PDF: downloads/manuscripts/MAFI-2025-0166.pdf (2.4 MB)
      ✅ Cover Letter: downloads/cover_letters/MAFI-2025-0166_cover_letter.pdf
      
📄 PROCESSING MANUSCRIPT 2/2: MAFI-2024-0167
   [Similar detailed output...]

💾 Full data saved to: data/results/mf_comprehensive_20250724_143000.json

🔍 PRECISE RESULTS SUMMARY
================================================================================
📊 MANUSCRIPTS FOUND: 2

📄 MANUSCRIPT 1/2: MAFI-2025-0166
   Title: Optimal investment and consumption under forward utilities...
   Status: Under Review
   Category: Awaiting Reviewer Selection
   👥 Authors (3): Broux-Quemerais Guillaume, Matoussi Anis, Zhou Chao
   🔍 Referees (4):
      • Dr. John Smith (Agreed) - j.smith@university.edu
      • Prof. Jane Doe (Declined) - jane.doe@institute.org
      • Dr. Bob Wilson (Agreed) - b.wilson@college.edu
      • Prof. Alice Johnson (Reviewing) - a.johnson@research.org
   📁 Documents:
      ✅ PDF: downloads/manuscripts/MAFI-2025-0166.pdf (2.4 MB)
      ✅ Cover Letter: downloads/cover_letters/MAFI-2025-0166_cover_letter.pdf

📄 MANUSCRIPT 2/2: MAFI-2024-0167
   Title: [Another manuscript title...]
   Status: Under Review
   Category: With Reviewers
   👥 Authors (2): [Author names...]
   🔍 Referees (2):
      • [Referee details...]
   📁 Documents:
      ✅ PDF: downloads/manuscripts/MAFI-2024-0167.pdf (1.8 MB)

🎯 BASELINE COMPLIANCE CHECK:
   ✅ Expected Manuscripts: 2/2 (100%)
   ✅ Expected Total Referees: 6/6 (100%)
   ✅ Expected PDFs: 2/2 (100%)
   🎉 PERFECT SUCCESS - All data extracted correctly!

✅ No extraction errors detected!
```

## Output Files

The extractor creates:

1. **Main Results**: `data/results/mf_comprehensive_YYYYMMDD_HHMMSS.json`
2. **Downloaded PDFs**: `downloads/manuscripts/MAFI-XXXX-XXXX.pdf`
3. **Cover Letters**: `downloads/cover_letters/MAFI-XXXX-XXXX_cover_letter.pdf`
4. **Debug Files**: If any issues occur

## Troubleshooting

If you see errors:

1. **Login Issues**: Check your credentials
2. **2FA Required**: You may need to manually enter verification codes
3. **Element Not Found**: The HTML structure may have changed
4. **Timeout Issues**: Increase timeouts in `config/mf_config.json`

## Next Steps

After extraction completes:
1. Review the JSON output file
2. Check downloaded documents
3. Verify all expected data was extracted
4. Use the data for your analysis/workflows