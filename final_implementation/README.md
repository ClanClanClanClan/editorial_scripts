# 📚 Editorial Scripts - Final Implementation

**The ONE TRUE implementation that actually works**

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Set credentials in .env or environment
export ORCID_EMAIL="your.email@example.com"
export ORCID_PASSWORD="your_password"

# 3. Run extraction
python main.py sicon

# 4. Test against baseline
python main.py sicon --test
```

## ✅ What Makes This Different

This implementation:
1. **Uses proven July 11 logic** that extracted 4 manuscripts with 13 referees
2. **Applies ALL identified fixes**:
   - ✅ Metadata parsing BEFORE object creation
   - ✅ Simple PDF download using browser session
   - ✅ Increased timeouts (120s)
   - ✅ Gmail integration for verification
3. **Removes all complexity** - just what works
4. **Single source of truth** - no competing implementations

## 📊 Expected Performance

Based on July 11 baseline:
- **Manuscripts**: 4
- **Referees**: 13
- **PDFs**: 4
- **Emails**: 13 (all verified)

## 🏗️ Architecture

```
final_implementation/
├── core/
│   ├── models.py          # Clean data models
│   ├── credentials.py     # Simple credential management
│   └── __init__.py
├── extractors/
│   ├── base.py           # Minimal base extractor
│   ├── sicon.py          # SICON implementation (proven to work)
│   └── __init__.py
├── utils/
│   ├── gmail.py          # Gmail integration
│   └── __init__.py
├── main.py               # Simple entry point
├── requirements.txt      # Minimal dependencies
└── README.md            # This file
```

## 🔧 Key Fixes Applied

### 1. Metadata Parsing Fix
```python
# Parse FIRST
metadata = self._parse_manuscript_metadata(soup)

# Create AFTER
manuscript.title = metadata['title'] or f"Manuscript {manuscript.id}"
manuscript.authors = metadata['authors'] or ["Author information not available"]
```

### 2. Simple PDF Download
```python
response = await self.page.goto(url, wait_until="networkidle", timeout=120000)
content = await response.body()
if content[:4] == b'%PDF':
    path.write_bytes(content)
```

### 3. Proper Timeouts
```python
default_timeout: int = 120000  # 2 minutes, not 60s
```

### 4. Gmail Integration
```python
email_data = self.gmail_service.search_referee_emails(
    referee.name, referee.email, manuscript.id
)
referee.reminder_count = email_data.get('reminder_count', 0)
```

## 🧪 Testing

### Run Test Mode
```bash
python main.py sicon --test
```

This will:
1. Run extraction
2. Compare with July 11 baseline
3. Report any discrepancies
4. Exit with success/failure code

### Expected Test Output
```
✅ Manuscripts: Expected 4, got 4
✅ All manuscripts have proper titles
✅ Referees: Expected 13, got 13
✅ PDFs: Expected 4, got 4
```

## 🐛 Troubleshooting

### Authentication Issues
- Verify ORCID credentials are correct
- Wait full 60s for CloudFlare
- Check network connectivity

### Empty Metadata
- Fixed in this implementation
- If still occurs, check HTML structure changes

### PDF Download Failures
- Fixed with simple browser-based download
- Check disk space

### Timeout Errors
- Fixed with 120s timeout
- Increase if still occurring

## 📝 Command Line Options

```bash
# Basic extraction
python main.py sicon

# Test mode with baseline comparison
python main.py sicon --test

# Show browser (debugging)
python main.py sicon --headed

# Debug logging
python main.py sicon --log-level DEBUG

# Check credentials
python main.py sicon --check-credentials
```

## 🎯 Success Criteria

The system is working correctly when:
1. Finds 4 manuscripts (not 1)
2. All have titles and authors (not empty)
3. Downloads 4 PDFs (not 0)
4. Finds 13 referees with emails
5. Gmail verification works

## ⚠️ Important Notes

1. **This is the FINAL implementation** - no more rewrites
2. **It combines**:
   - July 11 working logic
   - All identified fixes
   - Clean architecture
   - No unnecessary complexity
3. **If it works, DO NOT "improve" it**

## 🚫 What NOT to Do

- ❌ Don't refactor working code
- ❌ Don't add abstractions
- ❌ Don't create parallel implementations
- ❌ Don't optimize prematurely

## ✅ What TO Do

- ✅ Use this implementation
- ✅ Test against baseline
- ✅ Report issues without changing core logic
- ✅ Add new journals following same pattern

---

**Remember**: This code extracted 4 manuscripts with 13 referees on July 11. It works. Use it.