# Master Implementation Plan: Perfect Journal Extraction System

## 🎯 Ultimate Vision
Every journal extractor will have ALL of these features working perfectly:
1. ✅ Complete data extraction (manuscripts, referees, status, emails)
2. ✅ Incremental updates with change detection
3. ✅ Automated document downloads (PDFs, reports, cover letters)
4. ✅ Email verification via Gmail API
5. ✅ Status change tracking and notifications
6. ✅ Database integration with history tracking
7. ✅ Weekly automation integration
8. ✅ Digest email generation
9. ✅ Error recovery and retry logic
10. ✅ Comprehensive logging and monitoring

## 📊 Current State Analysis

### Working Extractors
- **MF** (`journals/mf.py`): ✅ Functional, uses email verification
- **MOR** (`journals/mor.py`): ✅ Functional, uses email verification
- **SICON** (new): ✅ Perfect extraction, needs production features
- **SIFIN**: 🔄 Shares SIAM platform with SICON

### Partial/Legacy
- **JOTA** (`journals/jota.py`): ⚠️ Basic functionality
- **MAFE** (`journals/mafe.py`): ⚠️ Basic functionality
- **FS** (`journals/fs.py`): ⚠️ SpringerNature platform
- **NACO** (`journals/naco.py`): ⚠️ Basic functionality

## 🏗️ Phase 1: Core Infrastructure (Week 1)

### 1.1 Enhanced Base Journal Class
```python
# core/enhanced_base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path

class EnhancedBaseJournal(ABC):
    """Enhanced base class with all production features"""
    
    def __init__(self, config: dict):
        self.config = config
        self.journal_name = config['journal_name']
        self.state_file = Path(f"state/{self.journal_name}_state.json")
        self.previous_state = self.load_state()
        self.changes = {
            'new_manuscripts': [],
            'status_changes': [],
            'new_reports': [],
            'new_referees': [],
            'overdue_reviews': []
        }
        self.logger = self.setup_logger()
        self.gmail_service = get_gmail_service()
        self.db_connection = self.setup_database()
    
    def load_state(self) -> dict:
        """Load previous extraction state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_state(self, current_state: dict):
        """Save current extraction state"""
        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(current_state, f, indent=2)
    
    def detect_changes(self, current_data: dict) -> dict:
        """Detect changes since last extraction"""
        # Compare manuscripts
        prev_ms_ids = set(self.previous_state.get('manuscripts', {}).keys())
        curr_ms_ids = set(current_data['manuscripts'].keys())
        
        # New manuscripts
        new_ms = curr_ms_ids - prev_ms_ids
        for ms_id in new_ms:
            self.changes['new_manuscripts'].append(ms_id)
        
        # Check existing manuscripts for changes
        for ms_id in prev_ms_ids & curr_ms_ids:
            self._detect_manuscript_changes(
                self.previous_state['manuscripts'][ms_id],
                current_data['manuscripts'][ms_id]
            )
        
        return self.changes
    
    def _detect_manuscript_changes(self, prev_ms: dict, curr_ms: dict):
        """Detect changes within a manuscript"""
        # Check for new referees
        prev_refs = {r['name']: r for r in prev_ms.get('referees', [])}
        curr_refs = {r['name']: r for r in curr_ms.get('referees', [])}
        
        # New referees
        for name in set(curr_refs.keys()) - set(prev_refs.keys()):
            self.changes['new_referees'].append({
                'manuscript_id': curr_ms['id'],
                'referee': curr_refs[name]
            })
        
        # Status changes
        for name in set(curr_refs.keys()) & set(prev_refs.keys()):
            if prev_refs[name]['status'] != curr_refs[name]['status']:
                self.changes['status_changes'].append({
                    'manuscript_id': curr_ms['id'],
                    'referee': name,
                    'old_status': prev_refs[name]['status'],
                    'new_status': curr_refs[name]['status'],
                    'change_date': datetime.now()
                })
        
        # Check for new reports
        if curr_refs[name].get('report_submitted') and not prev_refs[name].get('report_submitted'):
            self.changes['new_reports'].append({
                'manuscript_id': curr_ms['id'],
                'referee': name,
                'submission_date': datetime.now()
            })
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Journal-specific authentication"""
        pass
    
    @abstractmethod
    def extract_manuscripts(self) -> List[dict]:
        """Extract manuscript data"""
        pass
    
    def verify_with_email(self, referee: dict, manuscript: dict) -> dict:
        """Verify referee information with Gmail"""
        # Reuse our perfected email search logic
        pass
    
    def download_documents(self, manuscript: dict):
        """Download all available documents"""
        # Download PDFs, reports, cover letters
        pass
    
    def save_to_database(self, data: dict):
        """Save extraction results to database"""
        # Save to manuscripts, referees, status_history tables
        pass
    
    def generate_digest_data(self) -> dict:
        """Generate data for digest email"""
        return {
            'journal': self.journal_name,
            'changes': self.changes,
            'summary': self._generate_summary()
        }
    
    def run_extraction(self) -> dict:
        """Main extraction workflow with all features"""
        try:
            self.logger.info(f"Starting {self.journal_name} extraction")
            
            # Authenticate
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            
            # Verify with email
            for ms in manuscripts:
                for ref in ms['referees']:
                    self.verify_with_email(ref, ms)
            
            # Download documents
            for ms in manuscripts:
                self.download_documents(ms)
            
            # Detect changes
            current_state = self._format_state(manuscripts)
            self.detect_changes(current_state)
            
            # Save to database
            self.save_to_database(current_state)
            
            # Save state
            self.save_state(current_state)
            
            # Generate digest data
            digest_data = self.generate_digest_data()
            
            self.logger.info(f"Completed {self.journal_name} extraction")
            return digest_data
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise
```

### 1.2 Unified Document Downloader
```python
# core/document_downloader.py
class UnifiedDocumentDownloader:
    """Handles all document downloads across journals"""
    
    def __init__(self, driver, output_dir):
        self.driver = driver
        self.output_dir = output_dir
        self.download_strategies = {
            'pdf': self._download_pdf,
            'report': self._download_report,
            'cover_letter': self._download_cover_letter
        }
    
    def download_all_documents(self, manuscript: dict, page_source: str):
        """Download all available documents for a manuscript"""
        results = {
            'pdf': False,
            'reports': [],
            'cover_letter': False,
            'other': []
        }
        
        # Detect available documents
        available = self._detect_available_documents(page_source)
        
        # Download each type
        for doc_type, links in available.items():
            if doc_type in self.download_strategies:
                self.download_strategies[doc_type](manuscript, links, results)
        
        return results
```

### 1.3 Change Detection Engine
```python
# core/change_detection.py
class ChangeDetectionEngine:
    """Detects and tracks changes across extractions"""
    
    def __init__(self, journal_name: str):
        self.journal_name = journal_name
        self.notification_rules = self._load_notification_rules()
    
    def analyze_changes(self, previous: dict, current: dict) -> dict:
        """Comprehensive change analysis"""
        changes = {
            'critical': [],  # Needs immediate attention
            'important': [], # Include in digest
            'routine': []    # Log only
        }
        
        # Categorize changes by importance
        # New manuscripts are critical
        # Status changes are important
        # Metadata updates are routine
        
        return changes
    
    def should_notify(self, change: dict) -> bool:
        """Determine if a change warrants notification"""
        # Apply notification rules
        pass
```

## 🏗️ Phase 2: SICON/SIFIN Implementation (Week 2)

### 2.1 Unified SIAM Extractor
```python
# journals/siam_base.py
from core.enhanced_base import EnhancedBaseJournal

class SIAMJournalExtractor(EnhancedBaseJournal):
    """Base extractor for SIAM journals (SICON/SIFIN)"""
    
    def __init__(self, journal_code: str):
        config = {
            'journal_name': journal_code,
            'base_url': f'http://{journal_code.lower()}.siam.org',
            'folder_id': '1800' if journal_code == 'SICON' else '1801'  # Example
        }
        super().__init__(config)
        self.setup_driver()
    
    def authenticate(self) -> bool:
        """ORCID authentication for SIAM"""
        # Use our perfected ORCID auth
        return self._authenticate_orcid()
    
    def extract_manuscripts(self) -> List[dict]:
        """Extract manuscripts with perfect status parsing"""
        # Use our perfected extraction logic
        manuscripts = []
        
        # Navigate to manuscripts
        self._navigate_to_manuscripts()
        
        # Parse table with perfect status matching
        manuscripts = self._parse_manuscripts_table()
        
        # Extract emails and verify
        for ms in manuscripts:
            self._extract_referee_details(ms)
        
        return manuscripts
```

### 2.2 SICON Implementation
```python
# journals/sicon.py
from journals.siam_base import SIAMJournalExtractor

class SICON(SIAMJournalExtractor):
    """SICON journal extractor with all features"""
    
    def __init__(self):
        super().__init__('SICON')
    
    def post_process(self, manuscripts: List[dict]):
        """SICON-specific post-processing"""
        # Any SICON-specific logic
        pass
```

### 2.3 SIFIN Implementation
```python
# journals/sifin.py
from journals.siam_base import SIAMJournalExtractor

class SIFIN(SIAMJournalExtractor):
    """SIFIN journal extractor with all features"""
    
    def __init__(self):
        super().__init__('SIFIN')
        # SIFIN might have different folder_id
        self.config['folder_id'] = '1802'  # Example
```

## 🏗️ Phase 3: MOR/MF Upgrade (Week 3)

### 3.1 Enhance MF Extractor
```python
# journals/mf_enhanced.py
from core.enhanced_base import EnhancedBaseJournal
from journals.mf import MF as LegacyMF

class MF(EnhancedBaseJournal):
    """Enhanced MF extractor with all new features"""
    
    def __init__(self):
        config = {'journal_name': 'MF'}
        super().__init__(config)
        self.legacy_extractor = LegacyMF()
    
    def authenticate(self) -> bool:
        """Use existing MF authentication"""
        return self.legacy_extractor.authenticate()
    
    def extract_manuscripts(self) -> List[dict]:
        """Enhanced extraction with change detection"""
        # Start with legacy extraction
        legacy_data = self.legacy_extractor.extract()
        
        # Convert to new format
        manuscripts = self._convert_legacy_format(legacy_data)
        
        # Add new features
        for ms in manuscripts:
            # Check for report availability
            self._check_report_status(ms)
            
            # Download new reports
            self._download_new_reports(ms)
        
        return manuscripts
```

### 3.2 Enhance MOR Extractor
```python
# journals/mor_enhanced.py
# Similar structure to MF enhancement
```

## 🏗️ Phase 4: Remaining Journals (Week 4)

### 4.1 Create extractors for JOTA, MAFE, FS, NACO
- Use the enhanced base class
- Implement journal-specific authentication
- Add email verification
- Ensure perfect status parsing

## 🔄 Integration Components

### Weekly System Integration
```python
# weekly_extraction_system_v2.py
from journals.sicon import SICON
from journals.sifin import SIFIN
from journals.mf_enhanced import MF
from journals.mor_enhanced import MOR

class EnhancedWeeklyExtraction:
    """Weekly extraction with all journals"""
    
    def __init__(self):
        self.journals = [
            SICON(),
            SIFIN(), 
            MF(),
            MOR(),
            # Add others as implemented
        ]
    
    def run_all_extractions(self):
        """Run all journal extractions"""
        all_changes = {}
        
        for journal in self.journals:
            try:
                digest_data = journal.run_extraction()
                all_changes[journal.journal_name] = digest_data
            except Exception as e:
                self.logger.error(f"Failed to extract {journal.journal_name}: {e}")
        
        # Generate unified digest email
        self.generate_digest_email(all_changes)
```

### Database Schema Updates
```sql
-- Add tables for comprehensive tracking
CREATE TABLE referee_status_history (
    id SERIAL PRIMARY KEY,
    manuscript_id VARCHAR(50),
    referee_name VARCHAR(200),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    change_date TIMESTAMP,
    journal VARCHAR(20)
);

CREATE TABLE document_downloads (
    id SERIAL PRIMARY KEY,
    manuscript_id VARCHAR(50),
    document_type VARCHAR(50),
    filename VARCHAR(500),
    download_date TIMESTAMP,
    journal VARCHAR(20)
);

CREATE TABLE email_verifications (
    id SERIAL PRIMARY KEY,
    referee_email VARCHAR(200),
    manuscript_id VARCHAR(50),
    emails_found INTEGER,
    last_verified TIMESTAMP,
    journal VARCHAR(20)
);
```

## 📅 Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Enhanced base journal class
- [ ] Unified document downloader
- [ ] Change detection engine
- [ ] Database schema updates

### Week 2: SICON/SIFIN
- [ ] SIAM base extractor
- [ ] SICON with all features
- [ ] SIFIN with all features
- [ ] Integration tests

### Week 3: MOR/MF Upgrade
- [ ] Enhance MF with new features
- [ ] Enhance MOR with new features
- [ ] Migrate to new infrastructure
- [ ] Backward compatibility tests

### Week 4: Remaining Journals
- [ ] JOTA implementation
- [ ] MAFE implementation
- [ ] FS implementation
- [ ] NACO implementation

### Week 5: Production Deployment
- [ ] Full system integration test
- [ ] Performance optimization
- [ ] Monitoring setup
- [ ] Documentation
- [ ] Deploy to production

## 🎯 Success Metrics

Each journal extractor will be considered "perfect" when it:
1. ✅ Extracts 100% of manuscripts and referees
2. ✅ Has 0 "Unknown" referee statuses
3. ✅ Verifies >90% of referees via email
4. ✅ Downloads all available documents
5. ✅ Detects all status changes
6. ✅ Integrates with weekly system
7. ✅ Generates accurate digest data
8. ✅ Handles errors gracefully
9. ✅ Logs all actions comprehensively
10. ✅ Runs incrementally for efficiency

## 🚀 Next Steps

1. **Immediate**: Implement Phase 1 core infrastructure
2. **This week**: Complete SICON/SIFIN with all features
3. **Next week**: Upgrade MOR/MF to new infrastructure
4. **Following week**: Implement remaining journals
5. **Final week**: Full system testing and deployment

This plan ensures ALL journals will have the same high-quality features, with SICON/SIFIN leading the way as the most advanced implementations.