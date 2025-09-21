#!/usr/bin/env python3
"""
Compare MF and MOR extractor capabilities in detail
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# Add production path
sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

try:
    import extractors.mor_extractor as mor_module
    import extractors.mf_extractor as mf_module
except ImportError as e:
    print(f"❌ Error importing extractors: {e}")
    sys.exit(1)

# Get all methods from MOR extractor
mor_methods = set()
if hasattr(mor_module, 'MORExtractor'):
    mor_class = mor_module.MORExtractor
    mor_methods = {m for m in dir(mor_class) if not m.startswith('_') and callable(getattr(mor_class, m, None))}

# Get all methods from MF extractor  
mf_methods = set()
if hasattr(mf_module, 'ComprehensiveMFExtractor'):
    mf_class = mf_module.ComprehensiveMFExtractor
    mf_methods = {m for m in dir(mf_class) if not m.startswith('_') and callable(getattr(mf_class, m, None))}

print("="*60)
print("🔬 MF vs MOR EXTRACTOR CAPABILITY COMPARISON")
print("="*60)

# Key MF capabilities to check
key_capabilities = [
    # Core extraction
    ('extract_manuscript_details', 'Extract full manuscript details'),
    ('extract_referees_comprehensive', 'Comprehensive referee extraction'),
    ('extract_authors_from_details', 'Extract authors with full details'),
    ('extract_metadata_from_details', 'Extract metadata'),
    
    # Email & popup handling
    ('extract_email_from_popup_window', 'Extract emails from popup windows'),
    ('click_and_extract_email', 'Click and extract referee emails'),
    ('get_email_from_popup_safe', 'Safe popup email extraction'),
    
    # Document handling
    ('extract_all_documents', 'Extract all documents'),
    ('extract_cover_letter_from_details', 'Extract cover letters'),
    ('extract_response_to_reviewers', 'Extract response to reviewers'),
    
    # Advanced features
    ('extract_referee_report_from_link', 'Extract referee reports'),
    ('extract_review_popup_content', 'Extract review content from popups'),
    ('extract_report_with_timeout', 'Extract reports with timeout'),
    
    # ORCID & enrichment
    ('infer_country_from_web_search', 'Web search for country inference'),
    ('parse_affiliation_string', 'Parse affiliation strings'),
    
    # Navigation
    ('navigate_to_manuscript_information_tab', 'Navigate to manuscript info'),
    ('get_manuscript_categories', 'Get manuscript categories'),
    
    # Utility methods
    ('safe_click', 'Safe element clicking'),
    ('safe_get_text', 'Safe text extraction'),
    ('smart_wait', 'Smart waiting with variation'),
    ('with_retry', 'Retry decorator (module level)')
]

print("\n📊 KEY CAPABILITY ANALYSIS:")
print("-" * 50)

mf_score = 0
mor_score = 0

for method_name, description in key_capabilities:
    # Check if MF has it
    mf_has = method_name in mf_methods or (method_name == 'with_retry' and hasattr(mf_module, 'with_retry'))
    
    # Check if MOR has it or equivalent
    mor_has = method_name in mor_methods or (method_name == 'with_retry' and hasattr(mor_module, 'with_retry'))
    
    # Check for equivalent methods in MOR
    mor_equivalents = {
        'extract_manuscript_details': 'extract_manuscript_comprehensive',
        'extract_referees_comprehensive': 'extract_referees_enhanced',
        'extract_authors_from_details': 'extract_authors',
        'extract_metadata_from_details': 'extract_metadata',
        'extract_email_from_popup_window': 'extract_email_from_popup',
        'click_and_extract_email': 'extract_referee_emails_from_table',
        'extract_all_documents': 'download_all_documents',
        'navigate_to_manuscript_information_tab': 'navigate_to_manuscript_info_tab'
    }
    
    if not mor_has and method_name in mor_equivalents:
        mor_has = mor_equivalents[method_name] in mor_methods
    
    if mf_has:
        mf_score += 1
    if mor_has:
        mor_score += 1
        
    mf_icon = "✅" if mf_has else "❌"
    mor_icon = "✅" if mor_has else "❌"
    
    print(f"{description:40} MF:{mf_icon}  MOR:{mor_icon}")

print("-" * 50)
print(f"\n🎯 SCORES:")
print(f"   MF Extractor:  {mf_score}/{len(key_capabilities)} capabilities ({100*mf_score/len(key_capabilities):.1f}%)")
print(f"   MOR Extractor: {mor_score}/{len(key_capabilities)} capabilities ({100*mor_score/len(key_capabilities):.1f}%)")

# Show unique methods in each
print("\n🔍 UNIQUE METHODS:")
print("-" * 50)

mf_only = mf_methods - mor_methods
mor_only = mor_methods - mf_methods

print(f"\nMF-only methods ({len(mf_only)}):")
for i, method in enumerate(sorted(list(mf_only)[:10]), 1):
    print(f"  {i}. {method}")
if len(mf_only) > 10:
    print(f"  ... and {len(mf_only)-10} more")

print(f"\nMOR-only methods ({len(mor_only)}):")
for i, method in enumerate(sorted(list(mor_only)[:10]), 1):
    print(f"  {i}. {method}")
if len(mor_only) > 10:
    print(f"  ... and {len(mor_only)-10} more")

# Final assessment
print("\n" + "="*60)
print("📢 FINAL ASSESSMENT:")
print("="*60)

coverage = 100 * mor_score / mf_score if mf_score > 0 else 0

if coverage >= 95:
    print("✅ MOR extractor has FULL MF-level capabilities!")
elif coverage >= 80:
    print("⚠️  MOR extractor has MOST MF capabilities (>80%)")
elif coverage >= 60:
    print("🔶 MOR extractor has PARTIAL MF capabilities (60-80%)")
else:
    print("❌ MOR extractor LACKS many MF capabilities (<60%)")

print(f"\nCoverage: {coverage:.1f}% of MF capabilities")

# Save detailed report
report = {
    'timestamp': datetime.now().isoformat(),
    'mf_score': mf_score,
    'mor_score': mor_score,
    'coverage_percentage': coverage,
    'total_capabilities_checked': len(key_capabilities),
    'mf_unique_methods': len(mf_only),
    'mor_unique_methods': len(mor_only)
}

output_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs') / f"capability_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n📄 Detailed report saved to: {output_file.name}")