#!/usr/bin/env python3
"""
Safe, conservative cleanup of editorial_scripts folder

This script will:
1. Archive old debug files and screenshots
2. Consolidate duplicate extraction results
3. Remove empty directories and temp files
4. Organize test files
5. Keep the working unified_system structure intact
"""

import os
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

class SafeCleanup:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.archive_path = self.base_path / "archive" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.stats = defaultdict(int)
        
    def cleanup_debug_files(self):
        """Archive old debug files (older than 7 days)"""
        print("\n🧹 Cleaning up debug files...")
        
        debug_archive = self.archive_path / "debug_files"
        debug_archive.mkdir(parents=True, exist_ok=True)
        
        # Find all debug files
        debug_patterns = [
            "debug_*.html",
            "debug_*.png", 
            "debug_*.log",
            "*_debug_*",
            "screenshot_*.png",
            "*error*.png"
        ]
        
        for pattern in debug_patterns:
            for file in self.base_path.glob(pattern):
                if file.is_file():
                    # Keep recent debug files (last 7 days)
                    age = datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)
                    if age > timedelta(days=7):
                        dest = debug_archive / file.name
                        shutil.move(str(file), str(dest))
                        self.stats["debug_archived"] += 1
                    else:
                        self.stats["debug_kept"] += 1
        
        print(f"  ✅ Archived {self.stats['debug_archived']} old debug files")
        print(f"  ✅ Kept {self.stats['debug_kept']} recent debug files")
    
    def cleanup_test_files(self):
        """Organize test files into a tests directory"""
        print("\n📁 Organizing test files...")
        
        tests_dir = self.base_path / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # Move test files to tests directory
        test_files = list(self.base_path.glob("test_*.py"))
        
        for test_file in test_files:
            if test_file.parent == self.base_path:
                dest = tests_dir / test_file.name
                shutil.move(str(test_file), str(dest))
                self.stats["tests_moved"] += 1
        
        print(f"  ✅ Moved {self.stats['tests_moved']} test files to tests/")
    
    def cleanup_extraction_results(self):
        """Consolidate old extraction results"""
        print("\n📦 Consolidating extraction results...")
        
        extractions_archive = self.archive_path / "old_extractions"
        extractions_archive.mkdir(parents=True, exist_ok=True)
        
        # Patterns for extraction result directories
        patterns = [
            "siam_*",
            "sicon_*", 
            "sifin_*",
            "mf_*",
            "mor_*",
            "*_extraction_*",
            "extractions/"
        ]
        
        # Keep only the most recent extraction for each journal
        journal_extractions = defaultdict(list)
        
        for pattern in patterns:
            for item in self.base_path.glob(pattern):
                if item.is_dir() and item.name not in ["output", "unified_system"]:
                    # Extract journal name from directory name
                    journal = None
                    for j in ["sicon", "sifin", "mf", "mor", "siam"]:
                        if j in item.name.lower():
                            journal = j
                            break
                    
                    if journal:
                        mod_time = datetime.fromtimestamp(item.stat().st_mtime)
                        journal_extractions[journal].append((mod_time, item))
        
        # Archive all but the most recent for each journal
        for journal, extractions in journal_extractions.items():
            if len(extractions) > 1:
                # Sort by modification time
                extractions.sort(key=lambda x: x[0], reverse=True)
                
                # Keep the most recent, archive the rest
                for _, item in extractions[1:]:
                    try:
                        dest = extractions_archive / item.name
                        if item.exists():
                            shutil.move(str(item), str(dest))
                            self.stats["extractions_archived"] += 1
                    except Exception as e:
                        print(f"    ⚠️ Failed to archive {item.name}: {e}")
                        self.stats["extraction_failures"] += 1
        
        print(f"  ✅ Archived {self.stats['extractions_archived']} old extraction directories")
    
    def cleanup_virtual_envs(self):
        """Remove extra virtual environments"""
        print("\n🐍 Cleaning up virtual environments...")
        
        venv_dirs = ["venv_test", "venv_clean", ".venv_new"]
        
        for venv in venv_dirs:
            venv_path = self.base_path / venv
            if venv_path.exists():
                shutil.rmtree(venv_path)
                self.stats["venvs_removed"] += 1
                print(f"  ✅ Removed {venv}")
        
        # Keep only venv or venv_fresh
        print(f"  ✅ Removed {self.stats['venvs_removed']} extra virtual environments")
    
    def cleanup_old_archives(self):
        """Consolidate old archive directories"""
        print("\n📚 Consolidating old archives...")
        
        old_archives = self.archive_path / "consolidated_archives"
        old_archives.mkdir(parents=True, exist_ok=True)
        
        archive_patterns = [
            "archive_*",
            "legacy_*",
            "*_old",
            "backups/"
        ]
        
        for pattern in archive_patterns:
            for item in self.base_path.glob(pattern):
                if item.is_dir() and item != self.archive_path:
                    dest = old_archives / item.name
                    shutil.move(str(item), str(dest))
                    self.stats["archives_consolidated"] += 1
        
        print(f"  ✅ Consolidated {self.stats['archives_consolidated']} old archive directories")
    
    def cleanup_temp_files(self):
        """Remove temporary and cache files"""
        print("\n🗑️ Removing temporary files...")
        
        temp_patterns = [
            "*.pyc",
            "__pycache__",
            ".DS_Store",
            "*.log",
            "tmp_*",
            "temp_*",
            ".pytest_cache",
            "*.bak",
            "*.backup"
        ]
        
        for pattern in temp_patterns:
            for item in self.base_path.rglob(pattern):
                if item.is_file():
                    item.unlink()
                    self.stats["temp_files_removed"] += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    self.stats["temp_dirs_removed"] += 1
        
        print(f"  ✅ Removed {self.stats['temp_files_removed']} temporary files")
        print(f"  ✅ Removed {self.stats['temp_dirs_removed']} temporary directories")
    
    def organize_documentation(self):
        """Organize documentation files"""
        print("\n📄 Organizing documentation...")
        
        docs_dir = self.base_path / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (docs_dir / "reports").mkdir(exist_ok=True)
        (docs_dir / "guides").mkdir(exist_ok=True) 
        (docs_dir / "technical").mkdir(exist_ok=True)
        
        # Move documentation files
        doc_files = list(self.base_path.glob("*.md"))
        
        for doc in doc_files:
            if doc.name not in ["README.md", "requirements.txt"]:
                # Categorize documentation
                if any(x in doc.name.lower() for x in ["report", "audit", "summary"]):
                    dest = docs_dir / "reports" / doc.name
                elif any(x in doc.name.lower() for x in ["guide", "setup", "install"]):
                    dest = docs_dir / "guides" / doc.name
                else:
                    dest = docs_dir / "technical" / doc.name
                
                shutil.move(str(doc), str(dest))
                self.stats["docs_organized"] += 1
        
        print(f"  ✅ Organized {self.stats['docs_organized']} documentation files")
    
    def create_cleanup_report(self):
        """Create a report of the cleanup"""
        print("\n📝 Creating cleanup report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": dict(self.stats),
            "archive_location": str(self.archive_path)
        }
        
        report_path = self.base_path / "CLEANUP_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Create README for archive
        readme_path = self.archive_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(f"# Archived Files - {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("This directory contains files archived during cleanup:\n\n")
            f.write(f"- **debug_files/**: Old debug HTML files and screenshots\n")
            f.write(f"- **old_extractions/**: Previous extraction results\n")
            f.write(f"- **consolidated_archives/**: Old archive directories\n\n")
            f.write("## Statistics\n\n")
            for key, value in self.stats.items():
                f.write(f"- {key.replace('_', ' ').title()}: {value}\n")
    
    def cleanup_empty_dirs(self):
        """Remove empty directories"""
        print("\n🧹 Removing empty directories...")
        
        for root, dirs, files in os.walk(self.base_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        self.stats["empty_dirs_removed"] += 1
                except:
                    pass
        
        print(f"  ✅ Removed {self.stats['empty_dirs_removed']} empty directories")
    
    def run(self, dry_run: bool = True):
        """Run the cleanup"""
        print(f"\n🚀 Starting safe cleanup (dry_run={dry_run})...")
        
        if dry_run:
            print("\n⚠️ DRY RUN MODE - No changes will be made")
            print("\nThis will:")
            print("  1. Archive debug files older than 7 days")
            print("  2. Move test files to tests/ directory")
            print("  3. Archive old extraction results (keeping most recent)")
            print("  4. Remove extra virtual environments")
            print("  5. Consolidate old archive directories")
            print("  6. Remove temporary files")
            print("  7. Organize documentation")
            print("  8. Remove empty directories")
            return
        
        # Check for force flag or confirm
        if "--force" not in sys.argv:
            try:
                response = input("\n⚠️ This will clean up the folder. Continue? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Cleanup cancelled")
                    return
            except EOFError:
                print("\n⚠️ Running in non-interactive mode. Use --force to skip confirmation.")
                return
        
        # Create archive directory
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Run cleanup steps
        self.cleanup_debug_files()
        self.cleanup_test_files()
        self.cleanup_extraction_results()
        self.cleanup_virtual_envs()
        self.cleanup_old_archives()
        self.cleanup_temp_files()
        self.organize_documentation()
        self.cleanup_empty_dirs()
        self.create_cleanup_report()
        
        print(f"\n✅ Cleanup complete!")
        print(f"\n📊 Summary:")
        for key, value in self.stats.items():
            if value > 0:
                print(f"  - {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n📁 Archived files location: {self.archive_path}")


if __name__ == "__main__":
    import sys
    
    # Get the path to editorial_scripts
    base_path = Path(__file__).parent
    
    # Check for dry run flag
    dry_run = "--execute" not in sys.argv
    
    # Run cleanup
    cleaner = SafeCleanup(base_path)
    cleaner.run(dry_run=dry_run)
    
    if dry_run:
        print("\n💡 To execute the cleanup, run:")
        print(f"   python3 {__file__} --execute")