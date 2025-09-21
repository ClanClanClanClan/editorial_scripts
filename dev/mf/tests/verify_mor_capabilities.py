#!/usr/bin/env python3
"""
Verify MOR extractor has all MF-level capabilities
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directories to path
production_path = Path(__file__).parent.parent.parent / 'production/src'
if str(production_path) not in sys.path:
    sys.path.insert(0, str(production_path))

# Import extractors
try:
    from extractors.mor_extractor import MORExtractor
    from extractors.mf_extractor import MFExtractor
except ImportError as e:
    print(f"Error importing extractors: {e}")
    print(f"Paths in sys.path: {sys.path[:3]}")
    sys.exit(1)

def verify_capabilities():
    """Verify MOR has all MF capabilities"""
    print("\n" + "="*60)
    print("MOR EXTRACTOR CAPABILITY VERIFICATION")
    print("="*60)
    
    capabilities = {
        "Retry decorator (@with_retry)": False,
        "Cache integration (CachedExtractorMixin)": False,
        "Referee email extraction (extract_referee_emails)": False,
        "Document downloads (download_documents)": False,
        "Audit trail with pagination (extract_audit_trail)": False,
        "Version history (extract_version_history)": False,
        "Enhanced status parsing (extract_enhanced_status)": False,
        "ORCID enrichment (enrich_with_orcid)": False,
        "Safe element access (safe_click, safe_get_text)": False,
        "Smart wait with variation (smart_wait)": False,
        "Popup window handling (handle_popup_window)": False,
        "Complete extraction method (extract_all_manuscripts)": False
    }
    
    # Check MOR extractor
    mor_module = sys.modules.get('extractors.mor_extractor')
    if mor_module:
        # Check for retry decorator
        if hasattr(mor_module, 'with_retry'):
            capabilities["Retry decorator (@with_retry)"] = True
            
        # Check MOR class
        if hasattr(mor_module, 'MORExtractor'):
            mor_class = mor_module.MORExtractor
            
            # Check inheritance
            if 'CachedExtractorMixin' in [c.__name__ for c in mor_class.__mro__]:
                capabilities["Cache integration (CachedExtractorMixin)"] = True
            
            # Check methods
            methods_to_check = [
                ('extract_referee_emails', "Referee email extraction (extract_referee_emails)"),
                ('download_documents', "Document downloads (download_documents)"),
                ('extract_audit_trail', "Audit trail with pagination (extract_audit_trail)"),
                ('extract_version_history', "Version history (extract_version_history)"),
                ('extract_enhanced_status', "Enhanced status parsing (extract_enhanced_status)"),
                ('enrich_with_orcid', "ORCID enrichment (enrich_with_orcid)"),
                ('safe_click', "Safe element access (safe_click, safe_get_text)"),
                ('smart_wait', "Smart wait with variation (smart_wait)"),
                ('handle_popup_window', "Popup window handling (handle_popup_window)"),
                ('extract_all_manuscripts', "Complete extraction method (extract_all_manuscripts)")
            ]
            
            for method_name, capability_name in methods_to_check:
                if hasattr(mor_class, method_name):
                    capabilities[capability_name] = True
                    
    # Print results
    print("\n📊 CAPABILITY CHECKLIST:")
    print("-" * 40)
    
    passed = 0
    failed = 0
    
    for capability, status in capabilities.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {capability}")
        if status:
            passed += 1
        else:
            failed += 1
    
    print("-" * 40)
    score = (passed / len(capabilities)) * 100
    print(f"\n📈 MF-LEVEL SCORE: {score:.1f}% ({passed}/{len(capabilities)} features)")
    
    if score == 100:
        print("\n🎉 SUCCESS: MOR extractor has ALL MF-level capabilities!")
    elif score >= 80:
        print("\n⚠️  ALMOST THERE: MOR extractor has most MF capabilities")
    else:
        print("\n❌ INCOMPLETE: MOR extractor needs more work")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "capabilities": capabilities,
        "score": score,
        "passed": passed,
        "failed": failed
    }
    
    output_file = Path(__file__).parent.parent / 'outputs' / f"mor_capability_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {output_file.name}")
    return score == 100

if __name__ == "__main__":
    success = verify_capabilities()
    sys.exit(0 if success else 1)