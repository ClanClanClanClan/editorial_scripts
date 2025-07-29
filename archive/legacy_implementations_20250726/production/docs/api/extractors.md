# Extractor API Reference

*Complete API documentation for editorial script extractors*

## Core Extractors

### ComprehensiveMFExtractor

**File:** `src/extractors/mf_extractor.py`

The comprehensive extractor for Mathematical Finance journal manuscripts.

#### Class: `ComprehensiveMFExtractor`

```python
class ComprehensiveMFExtractor:
    """
    Production-ready extractor for Mathematical Finance journal.
    
    Features:
    - Multi-pass extraction strategy
    - Secure credential management
    - Comprehensive error handling
    - Academic profile enrichment
    """
```

#### Key Methods

##### `__init__(self, config_path=None, debug=False, headless=True)`
Initializes the extractor with configuration.

**Parameters:**
- `config_path` (str, optional): Path to custom configuration file
- `debug` (bool): Enable debug mode with detailed logging
- `headless` (bool): Run browser in headless mode

**Example:**
```python
extractor = ComprehensiveMFExtractor(
    config_path="config/mf_config.json",
    debug=True,
    headless=False
)
```

##### `login(self) -> bool`
Handles authentication including 2FA.

**Returns:** `bool` - Success status

**Features:**
- Secure credential loading from macOS Keychain
- Cookie banner handling
- Session state verification
- Manual 2FA code entry when required

##### `extract_from_category(self, category_name: str) -> None`
Extracts manuscripts from a specific category.

**Parameters:**
- `category_name` (str): Category to extract from (e.g., "Awaiting Reviewer Scores")

**Process:**
1. Navigate to Associate Editor Center
2. Select specified category
3. Execute 3-pass extraction strategy
4. Save results and generate reports

##### `extract_main_pages_forward(self, manuscript_count, manuscript_data, manuscript_order)`
**Pass 1:** Extract referees, abstracts, and documents going forward (1→2→...→n).

**Extracts:**
- Referee details with emails
- Abstract text
- PDF manuscripts
- Cover letters
- Basic metadata

##### `extract_manuscript_info_backward(self, manuscript_count, manuscript_data, manuscript_order)`
**Pass 2:** Extract authors and detailed metadata going backward (n→...→2→1).

**Extracts:**
- Complete author information
- Keywords and classifications
- Detailed submission metadata
- Editorial assignments

##### `extract_audit_trail_forward(self, manuscript_count, manuscript_data, manuscript_order)`
**Pass 3:** Extract communication timeline going forward (1→2→...→n).

**Extracts:**
- Complete audit trail
- Communication history
- Status change timeline
- Editorial decisions

#### Referee Extraction

##### `extract_referees_comprehensive(self, manuscript) -> None`
Comprehensive referee extraction with email retrieval.

**Process:**
1. Identify referee table rows using XPath selectors
2. Filter out editorial staff and authors
3. Click referee names to open email popups
4. Extract emails from `EMAIL_TEMPLATE_TO` fields
5. Parse referee status and metadata

**Data Structure:**
```python
{
    "name": "Prof. John Doe",
    "email": "john.doe@university.edu",
    "affiliation": "University of Research",
    "orcid": "0000-0000-0000-0000",
    "status": "Agreed|Declined|Unavailable",
    "dates": {
        "invited": "2024-12-01",
        "responded": "2024-12-03"
    },
    "report": None  # Populated if available
}
```

#### Document Handling

##### `download_manuscript_pdf(self, pdf_link, manuscript_id) -> str`
Downloads manuscript PDF with proper error handling.

##### `download_cover_letter(self, cover_link, manuscript_id) -> str`
Downloads cover letter, handling various formats (PDF, DOCX, TXT).

##### `extract_abstract(self, manuscript) -> None`
Extracts abstract text from manuscript page.

#### Academic Enrichment

##### `enrich_referee_profiles(self, manuscript) -> None`
Enriches referee data with ORCID and academic information.

**Features:**
- ORCID profile lookup
- Publication counting
- Affiliation verification
- Country/institution mapping

#### Configuration

The extractor uses `config/mf_config.json` for settings:

```json
{
    "selectors": {
        "referee_table": "//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]",
        "manuscript_id": "//span[contains(@class,'manuscriptId')]",
        "abstract": "//div[@class='abstract-content']"
    },
    "timeouts": {
        "login": 30,
        "navigation": 10,
        "popup": 5
    },
    "downloads": {
        "base_path": "downloads/",
        "manuscripts": "manuscripts/",
        "cover_letters": "cover_letters/"
    }
}
```

---

### SiconExtractor

**File:** `src/extractors/sicon_extractor.py`

SIAM Journal on Control and Optimization extractor.

#### Key Features
- ORCID authentication integration
- Category-specific extraction
- Email-based manuscript identification

---

### SifinExtractor  

**File:** `src/extractors/sifin_extractor.py`

SIAM Journal on Financial Mathematics extractor.

#### Key Features
- Firefox-based automation (cross-browser compatibility)
- Email processing and verification
- Robust error handling

---

## Utility Classes

### SecureCredentialManager

**File:** `src/core/secure_credentials.py`

Manages secure credential storage using macOS Keychain.

#### Methods

##### `store_credentials(self, email=None, password=None) -> bool`
Stores credentials securely in Keychain.

##### `load_credentials(self) -> tuple[str, str]`
Loads credentials from Keychain.

##### `setup_environment(self) -> bool`
Sets up environment variables with stored credentials.

---

## Error Handling Patterns

### SafeExecution Decorator

```python
@with_retry(max_attempts=3, delay=1.0)
def safe_operation():
    """Operation with automatic retry logic."""
    pass
```

### Exception Categories

1. **Authentication Errors**: Login, 2FA, session management
2. **Navigation Errors**: Page loading, element location
3. **Extraction Errors**: Data parsing, field access
4. **Download Errors**: File retrieval, storage issues

---

## Testing API

### Test Structure

```python
def test_extractor_functionality():
    """Standard test pattern for extractor testing."""
    extractor = MathematicalFinanceExtractor(debug=True)
    
    # Test login
    assert extractor.login()
    
    # Test extraction
    extractor.extract_from_category("Test Category")
    
    # Validate results
    assert len(extractor.manuscripts) > 0
```

---

## Data Validation

### Manuscript Schema

```python
{
    "id": str,              # Required: MAFI-YYYY-NNNN
    "title": str,           # Required: Manuscript title
    "authors": list,        # Required: Author information
    "referees": list,       # Required: Referee details
    "submission_date": str, # Required: ISO date format
    "status": str,          # Required: Current status
    "documents": dict,      # Optional: File paths
    "metadata": dict        # Optional: Additional data
}
```

---

*Last Updated: January 25, 2025*  
*API Version: 3.0*