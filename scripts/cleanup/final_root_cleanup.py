#!/usr/bin/env python3
"""Final cleanup of root directory - move remaining files to appropriate locations"""

import shutil
from pathlib import Path
from datetime import datetime

def final_root_cleanup():
    base = Path.cwd()
    
    print("🧹 Final root directory cleanup...\n")
    
    # Create necessary directories
    (base / "data" / "results").mkdir(parents=True, exist_ok=True)
    (base / "scripts" / "utils").mkdir(parents=True, exist_ok=True)
    (base / "config" / "env").mkdir(parents=True, exist_ok=True)
    
    # Move data files
    print("📊 Moving data files...")
    data_files = {
        "mf_final_results.json": "data/results/",
        "mf_scraping_results.json": "data/results/",
        "mor_complete_test_results.json": "data/results/",
        "complete_extraction_results.json": "data/results/",
        "mf_category_discovery_report.json": "data/results/",
        "mor_individual_result.txt": "data/results/",
        "fs_output.txt": "data/results/",
        "audit_results.json": "docs/reports/",
        "codebase_analysis_report.json": "docs/reports/",
        "implementation_recommendations.json": "docs/reports/",
        "deduplication_analysis.json": "docs/reports/"
    }
    
    moved = 0
    for file, dest in data_files.items():
        source = base / file
        if source.exists():
            try:
                target = base / dest / file
                shutil.move(str(source), str(target))
                moved += 1
            except:
                pass
    print(f"  ✓ Moved {moved} data files")
    
    # Move scripts
    print("\n🔧 Moving utility scripts...")
    script_files = {
        "activate_fresh.sh": "scripts/",
        "auth_1password.sh": "scripts/",
        "clean_environment.sh": "scripts/",
        "execute_aggressive_deduplication.py": "scripts/cleanup/",
        "final_root_cleanup.py": "scripts/cleanup/"
    }
    
    moved = 0
    for file, dest in script_files.items():
        source = base / file
        if source.exists():
            try:
                target = base / dest / file
                target.parent.mkdir(exist_ok=True)
                shutil.move(str(source), str(target))
                moved += 1
            except:
                pass
    print(f"  ✓ Moved {moved} scripts")
    
    # Move env example
    print("\n🔐 Moving environment files...")
    env_files = {
        "env_example.txt": "config/env/"
    }
    
    for file, dest in env_files.items():
        source = base / file
        if source.exists():
            try:
                target = base / dest / file
                shutil.move(str(source), str(target))
                print(f"  ✓ Moved {file}")
            except:
                pass
    
    # Archive old directories
    print("\n📁 Archiving miscellaneous directories...")
    archive_base = base / "archive" / f"final_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    archive_base.mkdir(parents=True, exist_ok=True)
    
    dirs_to_archive = [
        "editorial_assistant",  # Old structure
        "core",  # Should be in src/
        "backups",  # Old backups
        "journal_data_headless",
        "my_jota_profile",
        "my_jota_profile_backup",
        "migration_output",
        "production_logs",
        "state",
        "weekly_extractions"
    ]
    
    archived = 0
    for dir_name in dirs_to_archive:
        source = base / dir_name
        if source.exists() and source.is_dir():
            try:
                dest = archive_base / dir_name
                shutil.move(str(source), str(dest))
                archived += 1
            except:
                pass
    print(f"  ✓ Archived {archived} directories")
    
    # List what should remain in root
    print("\n✅ Final root directory should contain:")
    essential_root = [
        "README.md",
        "CLEANUP_AND_FIXES_SUMMARY.md",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements_analytics.txt",
        ".env",
        ".env.example",
        ".gitignore",
        "setup.py",
        "pyproject.toml",
        "alembic.ini",
        "pytest.ini",
        "Makefile",
        "run_unified_with_1password.py",
        # Directories
        "unified_system/",
        "src/",
        "tests/",
        "docs/",
        "scripts/",
        "output/",
        "data/",
        "config/",
        "archive/",
        "alembic/",
        "venv/",
        "venv_fresh/"
    ]
    
    print("\n📋 Essential items:")
    for item in essential_root:
        path = base / item.rstrip('/')
        if path.exists():
            print(f"  ✓ {item}")
        else:
            print(f"  ✗ {item} (missing)")
    
    # Count remaining items
    remaining = []
    for item in base.iterdir():
        if not item.name.startswith('.') and item.name not in [i.rstrip('/') for i in essential_root]:
            remaining.append(item.name)
    
    if remaining:
        print(f"\n⚠️  {len(remaining)} non-essential items remain:")
        for item in sorted(remaining)[:10]:
            print(f"  - {item}")
        if len(remaining) > 10:
            print(f"  ... and {len(remaining) - 10} more")
    else:
        print("\n✨ Root directory is perfectly clean!")


if __name__ == "__main__":
    final_root_cleanup()