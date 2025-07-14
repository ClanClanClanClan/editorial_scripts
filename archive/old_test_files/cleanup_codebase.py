#!/usr/bin/env python3
"""
Codebase Cleanup Script
Organizes files into proper directories and archives obsolete code
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Set

class CodebaseOrganizer:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.base_path = Path(__file__).parent
        self.archive_path = self.base_path / "archive" / f"cleanup_{datetime.now().strftime('%Y%m%d')}"
        self.report = {
            "files_moved": [],
            "directories_created": [],
            "errors": [],
            "summary": {}
        }
        
    def organize(self):
        """Main organization workflow"""
        print("🧹 Starting codebase cleanup...")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        
        # Create directory structure
        self._create_directory_structure()
        
        # Organize files by category
        self._organize_debug_files()
        self._organize_test_files()
        self._organize_siam_extractors()
        self._organize_journal_specific_files()
        self._organize_documentation()
        self._consolidate_duplicates()
        
        # Generate report
        self._generate_report()
        
    def _create_directory_structure(self):
        """Create organized directory structure"""
        directories = [
            "archive/debug",
            "archive/legacy_extractors",
            "archive/old_tests",
            "archive/legacy_docs",
            "scripts/utilities",
            "scripts/analysis",
            "scripts/migration",
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "tests/fixtures",
            "docs/current",
            "docs/archive",
            "src/journals/implementations",
            "src/journals/base",
            "src/core/services",
            "src/core/models",
            "src/analytics/implementations",
            "logs"
        ]
        
        for dir_path in directories:
            full_path = self.base_path / dir_path
            if not full_path.exists():
                if not self.dry_run:
                    full_path.mkdir(parents=True, exist_ok=True)
                self.report["directories_created"].append(str(dir_path))
                print(f"📁 Created: {dir_path}")
                
    def _organize_debug_files(self):
        """Move debug files to archive"""
        debug_files = list(self.base_path.glob("debug_*.py"))
        debug_files.extend(self.base_path.glob("*_debug.py"))
        debug_files.extend(self.base_path.glob("*_debug/"))
        
        print(f"\n🔍 Found {len(debug_files)} debug files to archive")
        
        for file_path in debug_files:
            dest = self.archive_path / "debug" / file_path.name
            self._move_file(file_path, dest)
            
    def _organize_test_files(self):
        """Organize test files into proper test directory"""
        test_patterns = ["test_*.py", "*_test.py"]
        test_files = []
        
        for pattern in test_patterns:
            test_files.extend(self.base_path.glob(pattern))
            
        # Exclude files already in tests directory
        test_files = [f for f in test_files if "tests" not in str(f)]
        
        print(f"\n🧪 Found {len(test_files)} test files to organize")
        
        for file_path in test_files:
            # Determine test type based on name
            if "integration" in file_path.name.lower():
                dest = self.base_path / "tests" / "integration" / file_path.name
            elif "e2e" in file_path.name.lower() or "end_to_end" in file_path.name.lower():
                dest = self.base_path / "tests" / "e2e" / file_path.name
            else:
                dest = self.base_path / "tests" / "unit" / file_path.name
                
            self._move_file(file_path, dest)
            
    def _organize_siam_extractors(self):
        """Archive old SIAM extractor versions"""
        siam_files = list(self.base_path.glob("extract_siam_*.py"))
        siam_files.extend(self.base_path.glob("*_siam_extraction*.py"))
        siam_files.extend(self.base_path.glob("siam_*_20*.py"))  # Dated versions
        
        # Keep only the most recent/working versions
        keep_files = {"extract_siam_complete_working.py", "siam_working_extraction.py"}
        archive_files = [f for f in siam_files if f.name not in keep_files]
        
        print(f"\n📚 Found {len(archive_files)} old SIAM extractors to archive")
        
        for file_path in archive_files:
            dest = self.archive_path / "legacy_extractors" / file_path.name
            self._move_file(file_path, dest)
            
    def _organize_journal_specific_files(self):
        """Organize journal-specific files"""
        journal_patterns = {
            "mf_": "MF",
            "mor_": "MOR",
            "sicon_": "SICON",
            "sifin_": "SIFIN",
            "jota_": "JOTA",
            "mafe_": "MAFE",
            "fs_": "FS",
            "naco_": "NACO"
        }
        
        for prefix, journal in journal_patterns.items():
            files = list(self.base_path.glob(f"{prefix}*.py"))
            files.extend(self.base_path.glob(f"{prefix}*/"))
            
            # Exclude test and debug files already moved
            files = [f for f in files if not any(x in f.name for x in ["test_", "debug_", "_test", "_debug"])]
            
            if files:
                print(f"\n📰 Organizing {len(files)} {journal} files")
                
                for file_path in files:
                    dest = self.base_path / "src" / "journals" / journal.lower() / file_path.name
                    self._move_file(file_path, dest)
                    
    def _organize_documentation(self):
        """Organize documentation files"""
        # Archive old/duplicate documentation
        doc_files = list(self.base_path.glob("*.md"))
        
        current_docs = {
            "README.md",
            "REFACTORING_PLAN_2025.md",
            "PROJECT_SPECIFICATIONS.md",
            "EDITORIAL_COMMAND_CENTER_SPECS.md",
            "REFEREE_ANALYTICS_SPECIFICATIONS.md"
        }
        
        archive_docs = [f for f in doc_files if f.name not in current_docs]
        
        print(f"\n📄 Found {len(archive_docs)} documentation files to archive")
        
        for file_path in archive_docs:
            dest = self.archive_path / "legacy_docs" / file_path.name
            self._move_file(file_path, dest)
            
    def _consolidate_duplicates(self):
        """Identify and consolidate duplicate functionality"""
        # Find similar files by analyzing imports and class names
        duplicate_groups = {
            "referee_extractors": [
                "extract_detailed_referees.py",
                "extract_referee_data.py",
                "simple_referee_extractor.py",
                "working_referee_extractor.py",
                "final_working_referee_extractor.py"
            ],
            "pdf_handlers": [
                "pdf_downloader.py",
                "pdf_fetcher.py",
                "pdf_parser.py",
                "smart_pdf_downloader.py",
                "working_pdf_download_test.py"
            ],
            "email_utils": [
                "core/email_utils.py",
                "core/generic_email_utils.py"
            ]
        }
        
        print("\n🔄 Consolidating duplicate files")
        
        for group_name, files in duplicate_groups.items():
            existing_files = []
            for file_name in files:
                file_path = self.base_path / file_name
                if file_path.exists():
                    existing_files.append(file_path)
                    
            if len(existing_files) > 1:
                print(f"  Found {len(existing_files)} duplicate {group_name}")
                # Keep the most recent/comprehensive one
                # Archive the rest
                existing_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                for file_path in existing_files[1:]:
                    dest = self.archive_path / "duplicates" / group_name / file_path.name
                    self._move_file(file_path, dest)
                    
    def _move_file(self, source: Path, destination: Path):
        """Move file with logging"""
        try:
            if not self.dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
            
            self.report["files_moved"].append({
                "source": str(source.relative_to(self.base_path)),
                "destination": str(destination.relative_to(self.base_path))
            })
            
            print(f"  ➡️  {source.name} → {destination.parent.relative_to(self.base_path)}/")
            
        except Exception as e:
            self.report["errors"].append({
                "file": str(source),
                "error": str(e)
            })
            print(f"  ❌ Error moving {source.name}: {e}")
            
    def _generate_report(self):
        """Generate cleanup report"""
        self.report["summary"] = {
            "total_files_moved": len(self.report["files_moved"]),
            "directories_created": len(self.report["directories_created"]),
            "errors_encountered": len(self.report["errors"]),
            "timestamp": datetime.now().isoformat()
        }
        
        report_path = self.base_path / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        if not self.dry_run:
            with open(report_path, 'w') as f:
                json.dump(self.report, f, indent=2)
                
        print("\n📊 Cleanup Summary:")
        print(f"  Files to move: {self.report['summary']['total_files_moved']}")
        print(f"  Directories to create: {self.report['summary']['directories_created']}")
        print(f"  Errors: {self.report['summary']['errors_encountered']}")
        
        if self.dry_run:
            print("\n⚠️  This was a DRY RUN. No files were actually moved.")
            print("Run with --execute to perform the cleanup.")
            
            
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Organize editorial scripts codebase")
    parser.add_argument("--execute", action="store_true", help="Actually move files (default is dry run)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    organizer = CodebaseOrganizer(dry_run=not args.execute)
    organizer.organize()
    

if __name__ == "__main__":
    main()