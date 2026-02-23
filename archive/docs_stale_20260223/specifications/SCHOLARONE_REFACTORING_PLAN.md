# 🏗️ SCHOLARONE EXTRACTOR REFACTORING PLAN

## 🎯 OBJECTIVE

Create a unified **ScholarOneExtractor** base class that handles all common functionality across MF, MOR, and future journals, while allowing journal-specific customization through inheritance.

---

## 📊 CURRENT STATE ANALYSIS

### **Common Patterns Identified**

Both MF and MOR extractors share **85%+ identical functionality**:

#### **Core Navigation**
- Login with 2FA handling
- AE Center navigation
- Category detection and processing
- 3-pass extraction system (Forward → Backward → Forward)
- Manuscript navigation (next/previous)
- Tab switching (Details, Audit Trail, Information)

#### **Data Extraction Methods**
```python
# Identical method signatures and logic
extract_manuscript_details()
extract_referees_comprehensive()
extract_document_links()
extract_audit_trail()
extract_communication_events()
navigate_to_manuscript_information_tab()
extract_basic_manuscript_info()
```

#### **Enhancement Systems**
- Deep web enrichment (MathSciNet, name corrections)
- Timeline analytics and communication patterns
- Gmail cross-checking integration
- Comprehensive caching system
- PDF download and organization

#### **Error Handling**
- Popup management and recovery
- Navigation timeout handling
- 2FA retry logic
- Session management

### **Journal-Specific Differences**

Only **15%** of code is journal-specific:

#### **MF-Specific**
- Category names: "Awaiting AE Recommendation", "Awaiting Reviewer Reports"
- Referee table XPaths: Different column structures
- URL patterns: `/mf/` in paths
- Field mappings: Some different form field names

#### **MOR-Specific**
- Category names: "Awaiting Reviewer Selection", "Overdue Reviewer Reports"
- Referee table XPaths: Different popup structures
- URL patterns: `/mor/` in paths
- Version history: More complex revision handling

---

## 🏗️ PROPOSED ARCHITECTURE

### **Class Hierarchy**
```python
BaseExtractor (abstract)
└── ScholarOneExtractor (platform base)
    ├── MFExtractor (journal specific)
    ├── MORExtractor (journal specific)
    └── Future journals: SICON, SIFIN, etc.
```

### **Core Components**

#### **1. ScholarOneExtractor (Base Class)**
```python
class ScholarOneExtractor(CachedExtractorMixin):
    """
    Universal base class for ALL ScholarOne journals.
    Contains 85% of shared functionality.
    """

    # ABSTRACT METHODS (must be overridden)
    def get_journal_config(self):
        """Return journal-specific configuration"""

    def get_category_mappings(self):
        """Return journal-specific category names"""

    def get_xpath_patterns(self):
        """Return journal-specific XPath selectors"""

    # SHARED METHODS (work for all journals)
    def login_with_2fa(self):
    def navigate_to_ae_center(self):
    def extract_three_pass_system(self):
    def extract_audit_trail(self):
    def deep_web_enrichment(self):
    def gmail_crosscheck(self):
    # ... 100+ shared methods
```

#### **2. Journal-Specific Classes**
```python
class MFExtractor(ScholarOneExtractor):
    """Mathematical Finance specific implementation"""

    def get_journal_config(self):
        return {
            'journal_code': 'mf',
            'base_url': 'https://mc.manuscriptcentral.com/mf',
            'credential_key': 'editorial-scripts-MF'
        }

    def get_category_mappings(self):
        return {
            'awaiting_reports': 'Awaiting Reviewer Reports',
            'ae_recommendation': 'Awaiting AE Recommendation',
            'overdue': 'Overdue Reviewer Reports'
        }

    def get_xpath_patterns(self):
        return {
            'referee_table': "//table[@class='mf-referee-table']",
            'email_popup': "//div[@id='mf-popup-email']",
            'category_links': "//a[contains(@href, '/mf/')]"
        }

class MORExtractor(ScholarOneExtractor):
    """Mathematics of Operations Research specific"""

    def get_journal_config(self):
        return {
            'journal_code': 'mor',
            'base_url': 'https://mc.manuscriptcentral.com/mor',
            'credential_key': 'editorial-scripts-MOR'
        }

    # Override only the differences...
```

---

## 📋 REFACTORING IMPLEMENTATION PLAN

### **Phase 1: Create Base Class** (1-2 hours)
1. **Extract common methods** from MF/MOR into ScholarOneExtractor
2. **Identify abstract methods** that need journal-specific implementation
3. **Create configuration system** for journal-specific settings
4. **Test base class** with minimal journal implementation

### **Phase 2: Migrate MF Extractor** (30 minutes)
1. **Inherit from ScholarOneExtractor**
2. **Override journal-specific methods only**
3. **Test full MF functionality**
4. **Validate no regression** in features or performance

### **Phase 3: Migrate MOR Extractor** (30 minutes)
1. **Inherit from ScholarOneExtractor**
2. **Override journal-specific methods only**
3. **Test full MOR functionality**
4. **Validate no regression** in features or performance

### **Phase 4: Code Cleanup** (30 minutes)
1. **Remove duplicate code** from original extractors
2. **Update documentation** and workflow guides
3. **Create generic ScholarOne documentation**
4. **Add future journal template**

---

## 🎯 CONFIGURATION-DRIVEN APPROACH

### **Journal Configuration File**
```python
# config/journal_configs.py
JOURNAL_CONFIGS = {
    'mf': {
        'name': 'Mathematical Finance',
        'base_url': 'https://mc.manuscriptcentral.com/mf',
        'credential_key': 'editorial-scripts-MF',
        'categories': {
            'awaiting_reports': 'Awaiting Reviewer Reports',
            'ae_recommendation': 'Awaiting AE Recommendation'
        },
        'xpaths': {
            'referee_table': "//table[@class='referee-table']",
            'email_popup': "//div[contains(@class, 'popup-email')]"
        }
    },
    'mor': {
        'name': 'Mathematics of Operations Research',
        'base_url': 'https://mc.manuscriptcentral.com/mor',
        'credential_key': 'editorial-scripts-MOR',
        'categories': {
            'awaiting_selection': 'Awaiting Reviewer Selection',
            'awaiting_reports': 'Awaiting Reviewer Reports'
        }
    }
}
```

### **Usage Example**
```python
# Future journal implementation becomes trivial:
class SICONExtractor(ScholarOneExtractor):
    def __init__(self):
        super().__init__(journal_code='sicon')

    # That's it! Inherits all functionality
    # Only override if journal has unique requirements
```

---

## 📊 EXPECTED BENEFITS

### **Code Reduction**
- **MF Extractor**: 6,489 → ~800 lines (87% reduction)
- **MOR Extractor**: 11,149 → ~900 lines (92% reduction)
- **Total Codebase**: Significant reduction while adding new journal support

### **Maintainability**
- ✅ **Single source** for bug fixes and enhancements
- ✅ **Consistent behavior** across all journals
- ✅ **Easy testing** with shared test suite
- ✅ **Rapid journal addition** (hours instead of weeks)

### **Feature Consistency**
- ✅ **All enhancements** automatically available to all journals
- ✅ **Unified caching** and error handling
- ✅ **Consistent data formats** across journals
- ✅ **Shared monitoring** and debugging tools

---

## 🚨 RISK MITIGATION

### **Backward Compatibility**
- **Keep original files** until refactored versions are validated
- **Identical APIs** - no external interface changes
- **Same output formats** - no downstream impact
- **Gradual migration** - one journal at a time

### **Testing Strategy**
- **Unit tests** for base class methods
- **Integration tests** for journal-specific implementations
- **Regression testing** against known good outputs
- **Performance benchmarking** to ensure no slowdown

---

## 🎯 SUCCESS CRITERIA

### **Functional Requirements**
- [ ] ✅ **100% feature parity** with existing extractors
- [ ] ✅ **Same performance** characteristics
- [ ] ✅ **Identical data output** formats
- [ ] ✅ **All enhancement features** working

### **Code Quality Requirements**
- [ ] ✅ **<1000 lines** per journal-specific extractor
- [ ] ✅ **No duplicate code** between journals
- [ ] ✅ **Easy to add** new journals (template-based)
- [ ] ✅ **Comprehensive documentation** for base class

### **Future Journal Template**
```python
class NewJournalExtractor(ScholarOneExtractor):
    """Template for any new ScholarOne journal"""

    def get_journal_config(self):
        return JOURNAL_CONFIGS['new_journal']

    # Override only if journal has unique requirements:
    # def extract_special_feature(self):
    #     # Journal-specific implementation
```

---

## 📞 IMPLEMENTATION DECISION

**Recommendation**: Proceed with refactoring using the configuration-driven approach.

**Timeline**: ~3-4 hours total implementation
- Phase 1 (Base class): 2 hours
- Phase 2 (MF migration): 30 minutes
- Phase 3 (MOR migration): 30 minutes
- Phase 4 (Cleanup): 30 minutes

**Next Steps**:
1. Create ScholarOneExtractor base class
2. Extract shared functionality from MF/MOR
3. Test migration with one journal first
4. Validate complete functionality
5. Document new architecture

---

**Last Updated**: August 19, 2025
**Status**: Ready for Implementation
**Priority**: High - Significant code reduction and maintainability improvement
