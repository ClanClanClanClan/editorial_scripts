# 🌐 Multi-Platform Editorial Extraction Framework

**Architecture design for 8 journal extractors across 5 platforms**

## 📊 Target Journal Ecosystem

| Platform | Journals | Count | Authentication |
|----------|----------|-------|----------------|
| **ScholarOne** | MF, MOR | 2 | Email/Password + 2FA |
| **SIAM** | SICON, SIFIN | 2 | ORCID OAuth |
| **Email-Based** | Finance & Stochastics | 1 | Gmail API Only |
| **Springer** | JOTA, MAFE | 2 | Username/Password |
| **TBD Platform** | NACO | 1 | TBD |
| **TOTAL** | | **8** | Multiple Methods |

## 🏗️ Proposed Architecture

### Core Framework Structure

```
editorial_extractors/
├── core/                           # Shared framework
│   ├── base_extractor.py          # Abstract base class
│   ├── browser_manager.py         # Selenium utilities
│   ├── credential_manager.py      # Multi-platform auth
│   ├── email_processor.py         # Email/popup handling
│   ├── document_downloader.py     # File management
│   ├── output_formatter.py        # JSON standardization
│   └── cache_manager.py          # Performance caching
├── platforms/                     # Platform-specific bases
│   ├── scholarone.py             # ScholarOne base class
│   ├── siam.py                   # SIAM base class  
│   ├── email_based.py            # Email-only base class
│   ├── springer.py               # Springer base class
│   └── unknown.py                # Extensible base
├── extractors/                   # Journal-specific implementations
│   ├── mf_extractor.py          # Mathematical Finance
│   ├── mor_extractor.py         # Math Operations Research
│   ├── sicon_extractor.py       # SIAM Control & Optimization
│   ├── sifin_extractor.py       # SIAM Financial Mathematics
│   ├── fs_extractor.py          # Finance & Stochastics (email)
│   ├── jota_extractor.py        # Journal Optimization Theory
│   ├── mafe_extractor.py        # Mathematical Finance Europe
│   └── naco_extractor.py        # Numerical Algebra/Computing
├── config/                       # Configuration management
│   ├── journals.yaml            # Journal definitions
│   ├── platforms.yaml           # Platform settings
│   └── credentials.yaml         # Auth configuration
└── tests/                       # Testing infrastructure
    ├── unit/                    # Component tests
    ├── integration/             # Full extraction tests
    └── fixtures/                # Test data
```

## 🔧 Platform-Specific Architectures

### 1. ScholarOne Platform (MF, MOR)
```python
class ScholarOneExtractor(BaseExtractor):
    """Base for ScholarOne Manuscripts platform"""
    
    def authenticate(self):
        # Email/password + 2FA via Gmail
    
    def navigate_to_ae_center(self):
        # Common ScholarOne navigation
    
    def extract_popup_emails(self, javascript_url):
        # Shared popup email extraction
    
    def get_manuscript_categories(self):
        # Common category detection
```

### 2. SIAM Platform (SICON, SIFIN)  
```python
class SIAMExtractor(BaseExtractor):
    """Base for SIAM journals"""
    
    def authenticate(self):
        # ORCID OAuth flow
    
    def navigate_to_dashboard(self):
        # SIAM-specific navigation
    
    def extract_reviewer_data(self):
        # SIAM reviewer system
```

### 3. Email-Based Platform (Finance & Stochastics)
```python
class EmailExtractor(BaseExtractor):
    """Base for email-only extraction"""
    
    def authenticate(self):
        # Gmail API only
    
    def extract_from_email_threads(self):
        # Email parsing and thread analysis
    
    def build_manuscript_from_emails(self):
        # Reconstruct submission data from email
```

### 4. Springer Platform (JOTA, MAFE)
```python
class SpringerExtractor(BaseExtractor):
    """Base for Springer journals"""
    
    def authenticate(self):
        # Username/password
    
    def navigate_to_editorial_dashboard(self):
        # Springer-specific interface
```

## 📊 Standardized Data Model

All extractors output consistent JSON structure:

```python
{
    "platform": "ScholarOne",           # Platform identifier
    "journal": "Mathematical Finance",   # Journal name  
    "extractor_version": "2.0.0",       # Version tracking
    "extraction_date": "2025-08-22",    # When extracted
    "manuscripts": [
        {
            "id": "MAFI-2025-0212",     # Platform-specific ID
            "canonical_id": "uuid-...", # Framework-generated UUID
            "title": "Paper Title",
            "status": "under_review",    # Standardized status
            "authors": [...],            # Standardized author objects
            "referees": [...],           # Standardized referee objects  
            "documents": [...],          # Standardized document objects
            "timeline": [...],           # Standardized event timeline
            "platform_specific": {      # Platform-unique fields
                "scholarone_audit_trail": [...],
                "siam_oauth_data": [...],
                "springer_workflow": [...]
            }
        }
    ]
}
```

## 🔒 Authentication Strategy

### Credential Management
```python
class MultiPlatformCredentialManager:
    """Manages credentials across all platforms"""
    
    platforms = {
        'scholarone': KeychainCredentials,
        'siam': OAuthCredentials, 
        'email': GmailAPICredentials,
        'springer': BasicCredentials
    }
```

### Security Features
- **Platform Isolation:** Each platform has separate credential storage
- **Encrypted Storage:** All credentials in macOS Keychain
- **OAuth Support:** ORCID, Gmail, platform-specific OAuth
- **Auto-refresh:** Token refresh for OAuth platforms

## 🚀 Implementation Strategy

### Phase 1: Framework Foundation (Safe)
1. **Extract Common Utilities:** From existing MF/MOR extractors
2. **Create Base Classes:** Abstract platform bases
3. **Standardize Output:** Common JSON structure
4. **Credential Framework:** Multi-platform auth

### Phase 2: Platform Bases (Medium Risk)
1. **ScholarOneExtractor:** Refactor MF/MOR to inherit from this
2. **SIAMExtractor:** New base for ORCID-based platforms
3. **EmailExtractor:** Gmail API-based extraction
4. **SpringerExtractor:** Traditional web forms

### Phase 3: New Extractors (Low Risk)
1. **SICON/SIFIN:** Inherit from SIAMExtractor
2. **Finance & Stochastics:** Inherit from EmailExtractor  
3. **JOTA/MAFE:** Inherit from SpringerExtractor
4. **NACO:** TBD based on platform discovery

## 📈 Benefits of This Architecture

### Code Reuse
- **Common functionality** shared across all extractors
- **Platform-specific logic** isolated and reusable
- **Consistent output format** regardless of platform

### Maintainability
- **Single change** propagates to all relevant extractors
- **Platform updates** contained to base classes
- **New journals** easy to add with minimal code

### Testing  
- **Platform-level tests** cover multiple journals
- **Common utilities** tested once, used everywhere
- **Mock platforms** for development testing

### Scalability
- **Easy addition** of new journals/platforms
- **Configuration-driven** journal definitions
- **Hot-swappable** credential systems

## 🎯 Migration Strategy

### Current → Framework (Safe)
1. **Keep existing MF/MOR working** during migration
2. **Extract utilities gradually** without breaking functionality  
3. **Test extensively** at each step
4. **Parallel development** of new platform bases

### Validation Approach
- **Side-by-side comparison** of old vs new extraction
- **Automated testing** of output equivalence
- **Gradual rollout** with fallback to existing extractors

---

**Framework Status:** Design Phase  
**Current Extractors:** Preserved and Working  
**Next Steps:** Extract common utilities safely