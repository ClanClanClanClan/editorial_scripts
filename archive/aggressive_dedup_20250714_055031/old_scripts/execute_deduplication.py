#!/usr/bin/env python3
"""
Execute deduplication based on analysis
Generated on 2025-07-14 05:30:01
"""

import shutil
from pathlib import Path
from datetime import datetime

def execute_deduplication():
    base = Path.cwd()
    archive_base = base / "archive" / "deduplication_20250714_053001"
    
    # Files/dirs to archive immediately
    immediate_archive = [
    "tests/test_sicon_folder_direct.py",
    "tests/test_siam_final.py",
    "tests/test_sicon_fix.py",
    "tests/test_updated_siam.py",
    "tests/test_sicon_ultra_simple.py",
    "tests/test_siam_real.py",
    "tests/test_siam_scraper.py",
    "tests/test_complete_siam.py",
    "tests/test_siam_debug.py",
    "tests/test_sicon_simple.py",
    "tests/test_sicon_only.py",
    "tests/test_sicon_direct.py",
    "tests/test_sicon_debug.py",
    "tests/test_sicon_only_new.py",
    "tests/test_selenium_siam.py",
    "tests/test_siam_extraction.py",
    "tests/test_siam_simple.py",
    "tests/test_siam_auto.py",
    "tests/test_full_scraping.py",
    "docs/reports/UNIFIED_SYSTEM_AUDIT.md",
    "docs/reports/AUDIT_UNIFIED_SYSTEM.md",
    "docs/reports/FINAL_AUDIT_COMPLETE.md",
    "docs/reports/HONEST_AUDIT.md",
    "docs/reports/REAL_IMPLEMENTATION_AUDIT.md",
    "docs/reports/ULTRA_DEEP_AUDIT_FINAL.md",
    "docs/reports/FINAL_AUDIT_REPORT.md",
    "docs/reports/PHASE_1_COMPLETION_REPORT.md",
    "docs/reports/PHASE_1_TESTING_AND_DATABASE_COMPLETION_REPORT.md",
    "docs/reports/PHASE_2_SIAM_COMPLETION_REPORT.md",
    "docs/REFACTORING_COMPLETE.md",
    "docs/COMPLETE_SYSTEM_TEST_SUMMARY.md",
    "docs/CONNECTION_POOL_OPTIMIZATION_COMPLETE.md",
    "docs/SYSTEM_FIXES_COMPLETE.md",
    "docs/FINAL_HONEST_ASSESSMENT.md",
    "docs/FINAL_SIFIN_SOLUTION.md",
    "docs/reports/FINAL_COMPREHENSIVE_AUDIT.md",
    "docs/reports/ULTRA_COMPREHENSIVE_FINAL_REPORT.md",
    "docs/reports/FINAL_REPORT.md",
    "docs/reports/FINAL_CLEAN_ENVIRONMENT_REPORT.md",
    "docs/reports/ULTRA_DEEP_AUDIT_FINAL.md",
    "docs/reports/FINAL_AUDIT_REPORT.md",
    "debug_screenshots",
    "debug_screenshots_20250710_211812",
    "debug_referee_emails_20250710_234558",
    "test_results_20250713_162638",
    "test_results_20250713_162800",
    "debug_logs",
    "debug_test"
]
    
    # Create archive directory
    archive_base.mkdir(parents=True, exist_ok=True)
    
    print("🗄️ Starting deduplication...")
    archived_count = 0
    failed_count = 0
    
    for item_path in immediate_archive:
        source = base / item_path
        if source.exists():
            try:
                # Determine archive location
                if source.is_file():
                    category = "files"
                elif "test" in item_path:
                    category = "old_tests"
                elif "debug" in item_path:
                    category = "debug_dirs"
                elif any(x in item_path for x in ["siam", "sicon", "sifin"]):
                    category = "old_extractions"
                else:
                    category = "misc"
                
                dest = archive_base / category / source.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                
                if source.is_dir():
                    shutil.move(str(source), str(dest))
                else:
                    shutil.move(str(source), str(dest))
                
                archived_count += 1
                print(f"  ✓ Archived: {item_path}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Failed: {item_path} - {e}")
    
    print(f"\n✅ Deduplication complete!")
    print(f"  Archived: {archived_count} items")
    print(f"  Failed: {failed_count} items")
    print(f"  Location: {archive_base}")
    
    # Create summary
    summary_path = archive_base / "DEDUPLICATION_SUMMARY.md"
    with open(summary_path, 'w') as f:
        f.write(f"# Deduplication Summary\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Statistics\n")
        f.write(f"- Items archived: {archived_count}\n")
        f.write(f"- Failed operations: {failed_count}\n\n")
        f.write(f"## Archived Items\n\n")
        for item in immediate_archive[:50]:  # First 50
            f.write(f"- {item}\n")
        if len(immediate_archive) > 50:
            f.write(f"\n... and {len(immediate_archive) - 50} more items\n")

if __name__ == "__main__":
    execute_deduplication()
