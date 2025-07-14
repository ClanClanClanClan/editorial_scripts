#!/usr/bin/env python3
"""
Cleanup and Organize Editorial Scripts Codebase
- Archives test/debug scripts
- Identifies working implementations
- Prepares for refactoring
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set

class CodebaseOrganizer:
    def __init__(self):
        self.base_dir = Path(".")
        self.archive_dir = self.base_dir / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.archive_dir.mkdir(exist_ok=True)
        
        # Track what we find
        self.test_files = []
        self.debug_files = []
        self.demo_files = []
        self.duplicate_implementations = {}
        self.working_extractors = []
        self.useless_files = []
        
    def analyze_codebase(self):
        """Analyze the codebase structure"""
        print("🔍 Analyzing codebase structure...")
        
        # Files to analyze
        python_files = list(self.base_dir.glob("**/*.py"))
        
        for file in python_files:
            if self._should_skip(file):
                continue
                
            file_str = str(file)
            file_name = file.name.lower()
            
            # Categorize files
            if file_name.startswith("test_") or "_test" in file_name:
                self.test_files.append(file)
            elif file_name.startswith("debug_") or "_debug" in file_name:
                self.debug_files.append(file)
            elif file_name.startswith("demo_") or "_demo" in file_name:
                self.demo_files.append(file)
            elif any(x in file_name for x in ["temp_", "tmp_", "old_", "backup_"]):
                self.useless_files.append(file)
            
            # Find duplicate implementations
            self._check_for_duplicates(file)
            
            # Find working extractors
            if self._is_working_extractor(file):
                self.working_extractors.append(file)
    
    def _should_skip(self, file: Path) -> bool:
        """Check if we should skip this file"""
        skip_dirs = ["venv", ".git", "__pycache__", "archive", ".pytest_cache", 
                     "venv_fresh", ".venv_new", "node_modules"]
        return any(skip_dir in str(file) for skip_dir in skip_dirs)
    
    def _check_for_duplicates(self, file: Path):
        """Check for duplicate implementations"""
        patterns = {
            "sicon": ["sicon", "SICON"],
            "sifin": ["sifin", "SIFIN"],
            "mf": ["mf_", "MF_", "mafe", "MAFE"],
            "mor": ["mor_", "MOR_"]
        }
        
        for journal, keywords in patterns.items():
            if any(kw in str(file) for kw in keywords):
                if journal not in self.duplicate_implementations:
                    self.duplicate_implementations[journal] = []
                self.duplicate_implementations[journal].append(file)
    
    def _is_working_extractor(self, file: Path) -> bool:
        """Check if this is a working extractor"""
        try:
            with open(file, 'r') as f:
                content = f.read()
                
            # Indicators of working code
            working_indicators = [
                "run_extraction",
                "extract_manuscripts", 
                "authenticate",
                "download_pdf",
                "class.*Extractor",
                "class.*Scraper"
            ]
            
            # Indicators of test/debug code
            test_indicators = [
                "if __name__",
                "test_",
                "debug_",
                "print\\(",
                "demo"
            ]
            
            has_working = any(indicator in content for indicator in working_indicators)
            has_test = sum(1 for indicator in test_indicators if indicator in content)
            
            # Likely working if it has working code and minimal test code
            return has_working and has_test <= 2
            
        except:
            return False
    
    def generate_report(self):
        """Generate analysis report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_python_files": len(self.test_files) + len(self.debug_files) + 
                                    len(self.demo_files) + len(self.working_extractors),
                "test_files": len(self.test_files),
                "debug_files": len(self.debug_files),
                "demo_files": len(self.demo_files),
                "useless_files": len(self.useless_files),
                "potential_working_extractors": len(self.working_extractors)
            },
            "duplicate_implementations": {
                journal: len(files) for journal, files in self.duplicate_implementations.items()
            },
            "files_to_archive": {
                "test_files": [str(f) for f in self.test_files],
                "debug_files": [str(f) for f in self.debug_files],
                "demo_files": [str(f) for f in self.demo_files],
                "useless_files": [str(f) for f in self.useless_files]
            },
            "working_extractors": [str(f) for f in self.working_extractors],
            "duplicate_details": {
                journal: [str(f) for f in files] 
                for journal, files in self.duplicate_implementations.items()
            }
        }
        
        with open("codebase_analysis_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self, report):
        """Print analysis summary"""
        print("\n📊 CODEBASE ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\n📁 Files Found:")
        print(f"  - Test files: {report['summary']['test_files']}")
        print(f"  - Debug files: {report['summary']['debug_files']}")
        print(f"  - Demo files: {report['summary']['demo_files']}")
        print(f"  - Useless files: {report['summary']['useless_files']}")
        print(f"  - Potential working extractors: {report['summary']['potential_working_extractors']}")
        
        print(f"\n🔄 Duplicate Implementations:")
        for journal, count in report['duplicate_implementations'].items():
            print(f"  - {journal.upper()}: {count} implementations found")
        
        print(f"\n✅ Likely Working Extractors:")
        for extractor in report['working_extractors'][:10]:  # Show first 10
            print(f"  - {extractor}")
        
        if len(report['working_extractors']) > 10:
            print(f"  ... and {len(report['working_extractors']) - 10} more")
        
        print(f"\n🗑️ Files to Archive: {sum(len(v) for v in report['files_to_archive'].values())}")
    
    def archive_files(self, report):
        """Archive test/debug/demo files"""
        print("\n📦 Archiving files...")
        
        categories = {
            "test_files": self.test_files,
            "debug_files": self.debug_files,
            "demo_files": self.demo_files,
            "useless_files": self.useless_files
        }
        
        for category, files in categories.items():
            if not files:
                continue
                
            category_dir = self.archive_dir / category
            category_dir.mkdir(exist_ok=True)
            
            for file in files:
                try:
                    dest = category_dir / file.name
                    # Don't archive if it's in a key directory
                    if any(important in str(file) for important in 
                          ["editorial_assistant", "core", "src/infrastructure/scrapers"]):
                        print(f"  ⚠️  Skipping important file: {file}")
                        continue
                    
                    shutil.move(str(file), str(dest))
                    print(f"  ✓ Archived: {file}")
                except Exception as e:
                    print(f"  ✗ Failed to archive {file}: {e}")
    
    def create_clean_structure(self):
        """Create the new clean directory structure"""
        print("\n🏗️ Creating clean structure...")
        
        directories = [
            "unified_system/core",
            "unified_system/extractors/siam",
            "unified_system/extractors/scholarone",
            "unified_system/analytics",
            "unified_system/integrations",
            "unified_system/tests/unit",
            "unified_system/tests/integration",
            "unified_system/tests/fixtures",
            "unified_system/cache",
            "unified_system/output"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {directory}")
    
    def identify_best_implementations(self):
        """Identify the best implementation for each journal"""
        print("\n🎯 Identifying best implementations...")
        
        recommendations = {
            "SICON": {
                "current_best": "src/infrastructure/scrapers/siam_scraper_fixed.py",
                "alternatives": [
                    "journals/sicon.py",
                    "editorial_assistant/extractors/sicon.py"
                ],
                "recommendation": "Merge siam_scraper_fixed with journal implementation"
            },
            "SIFIN": {
                "current_best": "src/infrastructure/scrapers/siam_scraper_fixed.py",
                "alternatives": [
                    "journals/sifin.py",
                    "editorial_assistant/extractors/sifin.py"
                ],
                "recommendation": "Same as SICON - use unified SIAM base"
            },
            "MF": {
                "current_best": "src/infrastructure/scrapers/mf_scraper_fixed.py",
                "alternatives": ["editorial_assistant/extractors/mf.py"],
                "recommendation": "Use mf_scraper_fixed as base"
            },
            "MOR": {
                "current_best": "src/infrastructure/scrapers/mor_scraper_fixed.py",
                "alternatives": ["editorial_assistant/extractors/mor.py"],
                "recommendation": "Use mor_scraper_fixed as base"
            }
        }
        
        with open("implementation_recommendations.json", "w") as f:
            json.dump(recommendations, f, indent=2)
        
        for journal, info in recommendations.items():
            print(f"\n{journal}:")
            print(f"  Best: {info['current_best']}")
            print(f"  Recommendation: {info['recommendation']}")


def main():
    print("🧹 EDITORIAL SCRIPTS CLEANUP & ORGANIZATION")
    print("=" * 60)
    
    organizer = CodebaseOrganizer()
    
    # Analyze codebase
    organizer.analyze_codebase()
    
    # Generate report
    report = organizer.generate_report()
    
    # Print summary
    organizer.print_summary(report)
    
    # Identify best implementations
    organizer.identify_best_implementations()
    
    # Ask before archiving
    response = input("\n🤔 Archive test/debug/demo files? (y/n): ")
    if response.lower() == 'y':
        organizer.archive_files(report)
    
    # Ask before creating structure
    response = input("\n🏗️ Create clean unified structure? (y/n): ")
    if response.lower() == 'y':
        organizer.create_clean_structure()
    
    print("\n✅ Cleanup complete!")
    print("📄 Reports generated:")
    print("  - codebase_analysis_report.json")
    print("  - implementation_recommendations.json")


if __name__ == "__main__":
    main()