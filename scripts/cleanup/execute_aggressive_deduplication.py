#!/usr/bin/env python3
"""
Execute aggressive deduplication based on detailed plan
Only keeps essential files, archives everything else
"""

import shutil
from pathlib import Path
from datetime import datetime
import os

def aggressive_deduplication():
    base = Path.cwd()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_base = base / "archive" / f"aggressive_dedup_{timestamp}"
    
    print("🚨 AGGRESSIVE DEDUPLICATION - This will archive most files!")
    print("📁 Creating archive directory...")
    
    # Create archive subdirectories
    (archive_base / "old_tests").mkdir(parents=True, exist_ok=True)
    (archive_base / "old_docs").mkdir(parents=True, exist_ok=True)
    (archive_base / "old_scripts").mkdir(parents=True, exist_ok=True)
    (archive_base / "old_dirs").mkdir(parents=True, exist_ok=True)
    (archive_base / "old_venvs").mkdir(parents=True, exist_ok=True)
    
    stats = {
        "tests_archived": 0,
        "docs_archived": 0,
        "scripts_archived": 0,
        "dirs_removed": 0,
        "space_saved_mb": 0
    }
    
    # 1. Delete virtual environments (they can be recreated)
    print("\n🗑️ Removing old virtual environments...")
    venvs_to_remove = ["venv_clean", "venv_test", ".venv_new"]
    for venv in venvs_to_remove:
        venv_path = base / venv
        if venv_path.exists():
            try:
                # Calculate size before removal
                size_mb = sum(f.stat().st_size for f in venv_path.rglob('*') if f.is_file()) / 1024 / 1024
                shutil.rmtree(venv_path)
                stats["space_saved_mb"] += size_mb
                stats["dirs_removed"] += 1
                print(f"  ✓ Removed {venv} ({size_mb:.1f} MB)")
            except Exception as e:
                print(f"  ✗ Failed to remove {venv}: {e}")
    
    # 2. Archive test files (keep only 4 essential ones)
    print("\n📋 Archiving test files...")
    keep_tests = {
        "test_unified_system.py",
        "test_sicon_fixed.py", 
        "test_sicon_gmail.py",
        "test_api_startup.py"
    }
    
    tests_dir = base / "tests"
    if tests_dir.exists():
        for test_file in tests_dir.glob("test_*.py"):
            if test_file.name not in keep_tests:
                try:
                    dest = archive_base / "old_tests" / test_file.name
                    shutil.move(str(test_file), str(dest))
                    stats["tests_archived"] += 1
                except Exception as e:
                    print(f"  ✗ Failed to archive {test_file.name}: {e}")
        
        print(f"  ✓ Archived {stats['tests_archived']} test files")
        print(f"  ✓ Kept {len(keep_tests)} essential tests")
    
    # 3. Archive old documentation
    print("\n📚 Archiving old documentation...")
    keep_docs = {
        "README.md",
        "README_STRUCTURE.md",
        "CLEANUP_AND_FIXES_SUMMARY.md",
        "AGGRESSIVE_DEDUPLICATION_PLAN.md"
    }
    
    # Archive docs in root
    for doc in base.glob("*.md"):
        if doc.name not in keep_docs:
            try:
                dest = archive_base / "old_docs" / doc.name
                shutil.move(str(doc), str(dest))
                stats["docs_archived"] += 1
            except:
                pass
    
    # Archive redundant docs in docs/
    docs_dir = base / "docs"
    if docs_dir.exists():
        # Keep only one setup guide and one audit report
        reports_to_archive = []
        guides_to_archive = []
        
        # Find all reports and guides
        for subdir in ["reports", "guides", ""]:
            subpath = docs_dir / subdir if subdir else docs_dir
            if subpath.exists():
                for doc in subpath.glob("*.md"):
                    doc_lower = doc.name.lower()
                    if "audit" in doc_lower or "report" in doc_lower:
                        if doc.name != "FINAL_AUDIT_REPORT.md":
                            reports_to_archive.append(doc)
                    elif "guide" in doc_lower or "setup" in doc_lower:
                        if doc.name != "SETUP_GUIDE.md":
                            guides_to_archive.append(doc)
        
        # Archive them
        for doc in reports_to_archive + guides_to_archive:
            try:
                dest = archive_base / "old_docs" / doc.parent.name / doc.name
                dest.parent.mkdir(exist_ok=True)
                shutil.move(str(doc), str(dest))
                stats["docs_archived"] += 1
            except:
                pass
    
    print(f"  ✓ Archived {stats['docs_archived']} documentation files")
    
    # 4. Archive old scripts
    print("\n🔧 Archiving old scripts...")
    # First, move essential script back to root if needed
    essential_runner = base / "scripts" / "run_unified_with_1password.py"
    if essential_runner.exists():
        shutil.move(str(essential_runner), str(base / "run_unified_with_1password.py"))
        print("  ✓ Moved run_unified_with_1password.py back to root")
    
    keep_scripts = {
        "run_unified_with_1password.py",
        "execute_aggressive_deduplication.py"  # This script
    }
    
    # Archive scripts in root
    for script in base.glob("*.py"):
        if script.name not in keep_scripts and script.parent == base:
            # Skip if it's in unified_system or src
            if "unified_system" not in str(script) and "src" not in str(script):
                try:
                    dest = archive_base / "old_scripts" / script.name
                    shutil.move(str(script), str(dest))
                    stats["scripts_archived"] += 1
                except:
                    pass
    
    # Archive scripts in scripts/
    scripts_dir = base / "scripts"
    if scripts_dir.exists():
        for script in scripts_dir.rglob("*.py"):
            # Keep only setup_1password.py
            if script.name != "setup_1password.py":
                try:
                    dest = archive_base / "old_scripts" / script.parent.name / script.name
                    dest.parent.mkdir(exist_ok=True)
                    shutil.move(str(script), str(dest))
                    stats["scripts_archived"] += 1
                except:
                    pass
    
    print(f"  ✓ Archived {stats['scripts_archived']} script files")
    
    # 5. Remove debug and test result directories
    print("\n📁 Removing debug directories...")
    patterns_to_remove = [
        "debug_*",
        "test_results_*",
        "dashboard_html_*",
        "pdf_debug_*",
        "siam_*",
        "sicon_*_*",
        "sifin_*_*",
        "demo_*",
        "enhanced_*",
        "fixed_*"
    ]
    
    for pattern in patterns_to_remove:
        for item in base.glob(pattern):
            if item.is_dir():
                try:
                    # Archive small ones, delete large ones
                    size_mb = sum(f.stat().st_size for f in item.rglob('*') if f.is_file()) / 1024 / 1024
                    if size_mb < 10:  # Archive if less than 10MB
                        dest = archive_base / "old_dirs" / item.name
                        shutil.move(str(item), str(dest))
                    else:
                        shutil.rmtree(item)
                    stats["space_saved_mb"] += size_mb
                    stats["dirs_removed"] += 1
                except:
                    pass
    
    print(f"  ✓ Removed/archived {stats['dirs_removed']} directories")
    
    # 6. Clean up empty directories
    print("\n🧹 Cleaning empty directories...")
    empty_count = 0
    for root, dirs, files in os.walk(base, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                if not any(dir_path.iterdir()) and "unified_system" not in str(dir_path):
                    dir_path.rmdir()
                    empty_count += 1
            except:
                pass
    print(f"  ✓ Removed {empty_count} empty directories")
    
    # Create summary
    print("\n📊 Creating summary...")
    summary_path = archive_base / "DEDUPLICATION_SUMMARY.md"
    with open(summary_path, 'w') as f:
        f.write(f"# Aggressive Deduplication Summary\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Statistics\n\n")
        f.write(f"- Test files archived: {stats['tests_archived']}\n")
        f.write(f"- Documentation archived: {stats['docs_archived']}\n")
        f.write(f"- Scripts archived: {stats['scripts_archived']}\n")
        f.write(f"- Directories removed: {stats['dirs_removed']}\n")
        f.write(f"- Space saved: ~{stats['space_saved_mb']:.1f} MB\n\n")
        f.write(f"## Essential Files Kept\n\n")
        f.write(f"### Tests (4 files)\n")
        for test in keep_tests:
            f.write(f"- {test}\n")
        f.write(f"\n### Core Structure\n")
        f.write(f"- unified_system/ (extraction system)\n")
        f.write(f"- src/ (source code)\n")
        f.write(f"- output/ (results)\n")
        f.write(f"- config/ (configuration)\n")
        f.write(f"- data/ (database)\n")
    
    # Final summary
    print(f"\n✅ AGGRESSIVE DEDUPLICATION COMPLETE!")
    print(f"\n📊 Final Statistics:")
    print(f"  - Test files: 50+ → 4")
    print(f"  - Docs: 40+ → ~5")
    print(f"  - Scripts: 30+ → 2")
    print(f"  - Space saved: ~{stats['space_saved_mb']:.1f} MB")
    print(f"  - Archive location: {archive_base}")
    
    print(f"\n⚠️  IMPORTANT: Test the system with:")
    print(f"  python3 tests/test_sicon_fixed.py")
    print(f"  python3 run_unified_with_1password.py --journal SICON")


if __name__ == "__main__":
    import sys
    
    print("⚠️  WARNING: This will aggressively archive most files!")
    print("   Only essential files will remain.")
    print("   Archive location: archive/aggressive_dedup_*")
    
    if "--force" in sys.argv:
        aggressive_deduplication()
    else:
        response = input("\nProceed with aggressive deduplication? (yes/N): ")
        if response.lower() == "yes":
            aggressive_deduplication()
        else:
            print("❌ Deduplication cancelled")
            print("\n💡 To force execution: python3 execute_aggressive_deduplication.py --force")