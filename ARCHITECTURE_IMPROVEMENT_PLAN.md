# 🏗️ Architecture Improvement Plan
**Date**: July 14, 2025  
**Objective**: Create a single, working, maintainable extraction system

---

## 🎯 Core Principles

1. **KISS** - Keep It Stupidly Simple
2. **One Source of Truth** - Single implementation per journal
3. **Fix First, Optimize Later** - Get it working, then improve
4. **Test with Real Data** - No mocks, real extractions

---

## 📐 Proposed Architecture

### Simplified Structure
```
editorial_scripts/
├── extractors/                    # All extraction code
│   ├── base.py                   # Simple base class
│   ├── siam/                     # SIAM journals
│   │   ├── sicon.py             # SICON extractor
│   │   └── sifin.py             # SIFIN extractor  
│   ├── scholarone/               # ScholarOne journals
│   │   ├── mf.py                # MF extractor
│   │   └── mor.py               # MOR extractor
│   └── email/                    # Email-based journals
│       ├── fs.py                # FS extractor
│       └── jota.py              # JOTA extractor
├── core/                         # Shared utilities
│   ├── models.py                # Data models
│   ├── credentials.py           # Credential management
│   └── pdf_manager.py           # PDF downloads
├── output/                      # Extraction results
├── cache/                       # Smart caching
└── run_extraction.py            # Main runner
```

### Key Changes
1. **Flatten structure** - No deep nesting
2. **Clear organization** - By platform type
3. **Minimal dependencies** - Each extractor self-contained
4. **Direct execution** - Simple run script

---

## 🔧 Implementation Details

### 1. Base Extractor (Minimal)
```python
class BaseExtractor:
    """Minimal base for all extractors"""
    
    async def extract(self, username: str, password: str) -> dict:
        """Standard interface"""
        await self.login(username, password)
        manuscripts = await self.get_manuscripts()
        
        for ms in manuscripts:
            await self.get_referee_details(ms)
            await self.download_pdfs(ms)
            
        return self.format_results(manuscripts)
```

### 2. SICON Extractor (Fixed)
```python
class SICONExtractor(BaseExtractor):
    """SICON specific implementation"""
    
    async def parse_manuscript(self, html: str) -> Manuscript:
        """Parse HTML BEFORE creating object"""
        # Extract data from table
        soup = BeautifulSoup(html, 'html.parser')
        
        # Parse all fields FIRST
        title = self._extract_title(soup)
        authors = self._extract_authors(soup)
        
        # THEN create manuscript
        return Manuscript(
            title=title,
            authors=authors,
            # ... other fields
        )
```

### 3. Credential Management (Simple)
```python
class CredentialManager:
    """Simple credential handling"""
    
    def get_credentials(self, journal: str) -> dict:
        # 1. Try 1Password
        # 2. Fall back to .env
        # 3. Prompt user
        return {"username": "...", "password": "..."}
```

### 4. PDF Manager (Direct)
```python
class PDFManager:
    """Simple PDF downloads"""
    
    async def download(self, url: str, page: Page) -> Path:
        """Just download the PDF"""
        response = await page.goto(url)
        content = await response.body()
        
        path = Path(f"output/pdfs/{filename}")
        path.write_bytes(content)
        
        return path if self._is_valid_pdf(path) else None
```

---

## 📋 Migration Plan

### Step 1: Create New Structure (1 hour)
```bash
mkdir -p extractors/{siam,scholarone,email}
mkdir -p core
mkdir -p {output,cache}
```

### Step 2: Port Working Code (2 hours)
1. Take SICON code from July 11 (it worked!)
2. Fix the metadata bug
3. Simplify PDF downloads
4. Remove unnecessary complexity

### Step 3: Test Thoroughly (1 hour)
1. Run SICON extraction
2. Verify metadata populated
3. Check PDFs downloaded
4. Compare with July 11 results

### Step 4: Archive Old Code (30 min)
```bash
mkdir -p archive/old_implementations_$(date +%Y%m%d)
mv src/ unified_system/ legacy_* archive/old_implementations_$(date +%Y%m%d)/
```

---

## 🎯 Success Metrics

### Minimum Viable Product
- [ ] SICON extracts 4 manuscripts
- [ ] All manuscripts have titles/authors
- [ ] PDFs download successfully
- [ ] Results match July 11 extraction

### Complete Success
- [ ] All 6 journals working
- [ ] Consistent data format
- [ ] Smart caching operational
- [ ] Gmail integration for reminders

---

## ⚡ Quick Wins

1. **Use July 11 code** - It worked perfectly
2. **Fix one bug** - Empty metadata
3. **Simplify structure** - Flatten directories
4. **Delete duplicates** - One implementation only

---

## 🚫 What NOT to Do

1. **Don't over-engineer** - Simple is better
2. **Don't optimize early** - Fix first
3. **Don't create abstractions** - Direct code
4. **Don't mock data** - Test with real journals

---

## 📝 Final Note

The system is 90% there. The extraction logic works, authentication works, and data discovery works. We just need to:
1. Fix the metadata parsing order
2. Simplify the PDF download
3. Choose one implementation

This is a 1-day fix, not a rewrite.