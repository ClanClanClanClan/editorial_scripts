#!/usr/bin/env python3
"""
Archive old files to legacy directory.
This script moves old test files and previous implementations to a legacy folder.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def archive_old_files():
    """Archive old files to legacy directory."""
    
    # Create legacy directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    legacy_dir = Path(f"legacy_{timestamp}")
    legacy_dir.mkdir(exist_ok=True)
    
    # Patterns for files to archive
    patterns_to_archive = [
        # Old test files
        "test_*.py",
        
        # Old implementations
        "*_extractor.py",
        "*_scraper.py",
        "*_stable_*.py", 
        "*_final_*.py",
        "*_complete_*.py",
        "perfect_*.py",
        "foolproof_*.py",
        
        # Specific files to keep in new structure
        # (these will be excluded)
    ]
    
    # Files to explicitly keep
    files_to_keep = {
        "setup.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        "archive_old_files.py",  # This script
    }
    
    # Directories to keep
    dirs_to_keep = {
        "editorial_assistant",
        "config", 
        "data",
        "logs",
        ".git",
        "venv",
        "__pycache__",
    }
    
    archived_count = 0
    
    # Archive Python files
    for pattern in patterns_to_archive:
        for file_path in Path(".").glob(pattern):
            if file_path.name not in files_to_keep and file_path.is_file():
                dest = legacy_dir / file_path.name
                print(f"Archiving: {file_path} -> {dest}")
                shutil.move(str(file_path), str(dest))
                archived_count += 1
    
    # Archive old result directories
    for item in Path(".").iterdir():
        if item.is_dir() and item.name not in dirs_to_keep:
            if any(pattern in item.name for pattern in ["results", "output", "temp", "test"]):
                dest = legacy_dir / item.name
                print(f"Archiving directory: {item} -> {dest}")
                shutil.move(str(item), str(dest))
                archived_count += 1
    
    # Archive specific old files
    old_files = [
        "REFACTORING_PLAN.md",
        "FINAL_COMPLETION_REPORT.md",
        "MF_MOR_DIGEST.md",
        "journal_specs.md",
        "enhanced_journal_specs.md",
        "main_enhanced.py",
        "main.py",
        "email_utils.py",  # If it exists in root
    ]
    
    for old_file in old_files:
        if Path(old_file).exists():
            dest = legacy_dir / old_file
            print(f"Archiving: {old_file} -> {dest}")
            shutil.move(old_file, str(dest))
            archived_count += 1
    
    print(f"\n✅ Archived {archived_count} files/directories to {legacy_dir}/")
    
    # Create a manifest
    manifest_path = legacy_dir / "ARCHIVE_MANIFEST.txt"
    with open(manifest_path, 'w') as f:
        f.write(f"Archive created on: {datetime.now().isoformat()}\n")
        f.write(f"Total items archived: {archived_count}\n\n")
        f.write("Contents:\n")
        for item in sorted(legacy_dir.iterdir()):
            if item.name != "ARCHIVE_MANIFEST.txt":
                f.write(f"- {item.name}\n")
    
    print(f"📝 Created manifest at {manifest_path}")
    
    # Show what remains
    print("\n📁 Remaining structure:")
    remaining_items = []
    for item in Path(".").iterdir():
        if not item.name.startswith('.') and item.name != legacy_dir.name:
            remaining_items.append(item.name)
    
    for item in sorted(remaining_items):
        print(f"  - {item}")
    
    return legacy_dir


if __name__ == "__main__":
    print("🗄️  Archiving old files to legacy directory...\n")
    legacy_dir = archive_old_files()
    print(f"\n✨ Clean-up complete! Old files moved to: {legacy_dir}/")
    print("\nYour editorial_assistant package is now clean and organized!")