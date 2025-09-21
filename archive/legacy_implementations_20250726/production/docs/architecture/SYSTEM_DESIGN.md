# Editorial Scripts System Architecture

*Comprehensive architectural overview and design principles*

## 🏗️ System Overview

The Editorial Scripts system is a production-ready academic manuscript extraction platform designed for automated data collection from journal management systems.

### Design Principles

1. **Security First** - Secure credential management with macOS Keychain integration
2. **Reliability** - Comprehensive error handling and retry mechanisms
3. **Modularity** - Journal-specific extractors with shared core functionality
4. **Testability** - Extensive test coverage with unit and integration tests
5. **Maintainability** - Clear code organization and comprehensive documentation

## 🏢 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ MF Extractor│ │SICON Extract│ │SIFIN Extract│          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                     Core Services                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ Credentials │ │ Browser Mgr │ │ Data Parser │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  Selenium   │ │   macOS     │ │ File System │          │
│  │  WebDriver  │ │  Keychain   │ │   Storage   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Extractor Framework

**Base Pattern:**
```python
class BaseExtractor:
    """Abstract base for all journal extractors."""

    def __init__(self, config, debug=False):
        self.driver = None
        self.config = config
        self.debug = debug

    def login(self) -> bool:
        """Authentication implementation."""
        raise NotImplementedError

    def extract(self, category: str) -> list:
        """Main extraction implementation."""
        raise NotImplementedError
```

**Specialization:**
- `ComprehensiveMFExtractor` - MF journal implementation
- `SiconExtractor` - SICON journal implementation
- `SifinExtractor` - SIFIN journal implementation

### 2. Authentication System

**SecureCredentialManager:**
```python
class SecureCredentialManager:
    """Manages credentials via macOS Keychain."""

    def store_credentials(self, email, password) -> bool
    def load_credentials(self) -> tuple[str, str]
    def setup_environment(self) -> bool
```

**2FA Integration:**
- Gmail API integration for verification code retrieval
- Automatic code parsing and entry
- Fallback manual entry option

### 3. Data Processing Pipeline

**Multi-Pass Extraction Strategy:**

```
Pass 1: Main Pages Forward (1→2→...→n)
├── Extract referees with emails
├── Download manuscripts (PDF)
├── Download cover letters
└── Extract abstracts

Pass 2: Manuscript Info Backward (n→...→2→1)
├── Extract complete author information
├── Extract keywords and classifications
└── Extract detailed metadata

Pass 3: Audit Trail Forward (1→2→...→n)
├── Extract communication timeline
├── Extract editorial decisions
└── Extract status changes
```

### 4. Error Handling Framework

**Retry Strategy:**
```python
@with_retry(max_attempts=3, delay=1.0)
def safe_operation():
    """Automatic retry with exponential backoff."""
    pass
```

**Error Categories:**
1. **Transient Errors** - Network issues, timeouts (retry)
2. **Authentication Errors** - Login failures (abort)
3. **Navigation Errors** - Page structure changes (fallback)
4. **Data Errors** - Missing elements (continue with warnings)

## 🔄 Data Flow

### 1. Initialization Phase
```
User Request → Credential Loading → Browser Setup → Configuration Loading
```

### 2. Authentication Phase
```
Navigate to Login → Enter Credentials → Handle 2FA → Verify Session
```

### 3. Extraction Phase
```
Navigate to Category → Multi-Pass Extraction → Data Validation → Storage
```

### 4. Cleanup Phase
```
Browser Cleanup → Result Aggregation → Report Generation → File Organization
```

## 🗄️ Data Models

### Manuscript Schema
```python
{
    "id": "MAFI-2025-0166",
    "title": "Risk Management in Financial Markets",
    "authors": [
        {
            "name": "Dr. Jane Smith",
            "email": "jane.smith@university.edu",
            "affiliation": "University of Finance",
            "orcid": "0000-0000-0000-0000",
            "corresponding": true
        }
    ],
    "referees": [
        {
            "name": "Prof. John Doe",
            "email": "john.doe@institute.org",
            "affiliation": "Research Institute",
            "status": "Agreed",
            "dates": {
                "invited": "2024-12-01",
                "responded": "2024-12-03"
            }
        }
    ],
    "submission_date": "2024-12-15",
    "last_updated": "2024-12-20",
    "status": "Under Review",
    "category": "Awaiting Reviewer Scores",
    "documents": {
        "pdf": "/downloads/manuscripts/MAFI-2025-0166.pdf",
        "cover_letter": "/downloads/cover_letters/MAFI-2025-0166.pdf",
        "abstract": "This paper presents..."
    },
    "metadata": {
        "keywords": ["risk management", "financial markets"],
        "article_type": "Research Article",
        "special_issue": null,
        "in_review_time": "5 days"
    }
}
```

## 🔧 Configuration Management

### Hierarchical Configuration
```
Default Config → Journal Config → User Config → Runtime Args
```

### Configuration Schema
```json
{
    "browser": {
        "type": "chrome|firefox",
        "headless": true,
        "timeout": 30
    },
    "selectors": {
        "referee_table": "XPath selector",
        "manuscript_id": "XPath selector",
        "navigation": "XPath selectors"
    },
    "extraction": {
        "max_manuscripts": 50,
        "retry_attempts": 3,
        "delay_between_actions": 1.0
    },
    "output": {
        "format": "json",
        "include_metadata": true,
        "timestamp_format": "%Y%m%d_%H%M%S"
    }
}
```

## 🧪 Testing Strategy

### Test Pyramid
```
                    ╱ ╲
                   ╱ E2E ╲
                  ╱_______╲
                 ╱         ╲
                ╱Integration╲
               ╱_____________╲
              ╱               ╲
             ╱   Unit Tests    ╲
            ╱___________________╲
```

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Individual function testing
   - Mock external dependencies
   - Fast execution (~seconds)

2. **Integration Tests** (`tests/integration/`)
   - Component interaction testing
   - Real browser automation
   - Medium execution (~minutes)

3. **End-to-End Tests** (Manual)
   - Complete workflow validation
   - Production environment testing
   - Slow execution (~hours)

## 🚀 Deployment Architecture

### Development Environment
```
Local Machine → Chrome/Firefox → Journal Websites
     ↓
macOS Keychain → Credentials Storage
     ↓
Local File System → Data Storage
```

### Production Considerations
- **Scaling**: Multiple journal support
- **Monitoring**: Error tracking and alerting
- **Backup**: Automated data backup
- **Security**: Credential rotation and audit logs

## 🔐 Security Model

### Credential Security
```
User Input → macOS Keychain → Encrypted Storage → Runtime Access
```

### Data Privacy
- No sensitive data in logs
- Secure file permissions
- Encrypted credential storage
- Audit trail for access

### Browser Security
- Isolated browser profiles
- Automatic cleanup
- No persistent cookies
- Safe navigation patterns

## 📊 Performance Characteristics

### Typical Processing Times
- **Login + 2FA**: 30-60 seconds
- **Per Manuscript**: 30-60 seconds
- **Complete Category**: 5-15 minutes
- **Full Journal Scan**: 30-60 minutes

### Resource Usage
- **Memory**: 200-500 MB (browser + Python)
- **CPU**: Moderate (web automation)
- **Network**: Low-moderate (page loads + downloads)
- **Storage**: Variable (depends on document downloads)

### Scalability Limits
- **Concurrent Sessions**: 1 (per journal)
- **Daily Extractions**: Unlimited
- **Data Volume**: Limited by storage space
- **Rate Limiting**: Respects journal server limits

## 🔧 Maintenance Procedures

### Regular Maintenance
1. **Weekly**: Review error logs and update selectors if needed
2. **Monthly**: Validate extraction accuracy and update test data
3. **Quarterly**: Review and update dependencies
4. **Annually**: Security audit and credential rotation

### Troubleshooting Workflow
1. **Check Logs**: Review extraction logs for errors
2. **Validate Selectors**: Ensure XPath selectors still work
3. **Test Authentication**: Verify credential storage and 2FA
4. **Browser Updates**: Ensure compatibility with latest browsers
5. **Journal Changes**: Adapt to journal website modifications

---

*Last Updated: January 25, 2025*
*Architecture Version: 3.0*
