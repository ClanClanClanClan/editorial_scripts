#!/usr/bin/env python3
"""
Deep analysis of remaining files to identify duplicates and what should be archived
"""

import os
import re
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import json

class DeduplicationAnalyzer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.analysis = {
            "duplicate_tests": defaultdict(list),
            "duplicate_scripts": defaultdict(list),
            "redundant_docs": defaultdict(list),
            "old_extractions": [],
            "unnecessary_dirs": [],
            "keep_files": [],
            "archive_candidates": []
        }
        
    def analyze_test_files(self):
        """Analyze test files for duplication"""
        print("\n🔍 Analyzing test files...")
        
        test_categories = defaultdict(list)
        tests_dir = self.base_path / "tests"
        
        if tests_dir.exists():
            for test_file in tests_dir.glob("test_*.py"):
                # Categorize by what they test
                name = test_file.name
                
                # Extract the main subject being tested
                if "sicon" in name or "siam" in name:
                    category = "siam_tests"
                elif "sifin" in name:
                    category = "sifin_tests"
                elif "api" in name:
                    category = "api_tests"
                elif "referee" in name and "analytics" in name:
                    category = "referee_analytics_tests"
                elif "database" in name or "db" in name:
                    category = "database_tests"
                elif "complete" in name or "integration" in name:
                    category = "integration_tests"
                elif "scraper" in name or "extraction" in name:
                    category = "scraper_tests"
                else:
                    category = "misc_tests"
                
                test_categories[category].append(test_file)
        
        # Identify duplicates within each category
        for category, files in test_categories.items():
            if len(files) > 2:  # More than 2 files in same category is suspicious
                self.analysis["duplicate_tests"][category] = [f.name for f in files]
        
        # Print findings
        for category, files in self.analysis["duplicate_tests"].items():
            print(f"\n  {category}: {len(files)} files")
            for f in sorted(files)[:5]:  # Show first 5
                print(f"    - {f}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")
    
    def analyze_documentation(self):
        """Analyze documentation for redundancy"""
        print("\n📚 Analyzing documentation...")
        
        docs_dir = self.base_path / "docs"
        doc_patterns = {
            "audit_reports": ["*AUDIT*.md", "*audit*.md"],
            "setup_guides": ["*SETUP*.md", "*GUIDE*.md", "*setup*.md"],
            "status_reports": ["*STATUS*.md", "*REPORT*.md", "*SUMMARY*.md"],
            "completion_reports": ["*COMPLETION*.md", "*COMPLETE*.md", "*FINAL*.md"]
        }
        
        for category, patterns in doc_patterns.items():
            found_docs = []
            for pattern in patterns:
                # Check in docs dir
                if docs_dir.exists():
                    found_docs.extend(docs_dir.rglob(pattern))
                # Check in root (files that weren't moved yet)
                found_docs.extend(self.base_path.glob(pattern))
            
            if len(found_docs) > 2:
                self.analysis["redundant_docs"][category] = [
                    str(f.relative_to(self.base_path)) for f in found_docs
                ]
        
        # Print findings
        for category, files in self.analysis["redundant_docs"].items():
            print(f"\n  {category}: {len(files)} files")
            for f in sorted(files)[:3]:
                print(f"    - {f}")
    
    def analyze_scripts(self):
        """Analyze scripts for duplication"""
        print("\n🔧 Analyzing scripts...")
        
        script_patterns = {
            "run_scripts": ["run_*.py"],
            "test_runners": ["test_*.py"],  # In root, not in tests/
            "debug_scripts": ["debug_*.py"],
            "fix_scripts": ["fix_*.py"],
            "setup_scripts": ["setup_*.py"],
            "extraction_scripts": ["*extraction*.py", "*scraper*.py"]
        }
        
        scripts_dir = self.base_path / "scripts"
        
        for category, patterns in script_patterns.items():
            found_scripts = []
            for pattern in patterns:
                # Check in scripts dir
                if scripts_dir.exists():
                    found_scripts.extend(scripts_dir.rglob(pattern))
                # Check in root
                found_scripts.extend(self.base_path.glob(pattern))
            
            # Remove items that are in tests directory
            found_scripts = [f for f in found_scripts if "tests" not in str(f)]
            
            if len(found_scripts) > 2:
                self.analysis["duplicate_scripts"][category] = [
                    str(f.relative_to(self.base_path)) for f in found_scripts
                ]
    
    def analyze_directories(self):
        """Analyze directories for unnecessary ones"""
        print("\n📁 Analyzing directories...")
        
        unnecessary_patterns = [
            # Debug directories
            "debug_*", "*_debug_*", 
            # Old extraction results
            "siam_*", "sicon_*_*", "sifin_*_*",
            # Test output
            "test_results_*", "*_test_*",
            # Demo directories
            "demo_*", 
            # Old dashboard outputs
            "dashboard_html_*",
            # Crosscheck results (keep only latest)
            "crosscheck_results_*",
            # Various output directories
            "*_output", "*_results",
            # Old virtual environments
            "venv_*", ".venv*",
            # Build directories
            "build", "dist", "*.egg-info"
        ]
        
        found_dirs = []
        for pattern in unnecessary_patterns:
            for item in self.base_path.glob(pattern):
                if item.is_dir() and item.name not in ["output", "venv", "venv_fresh"]:
                    # Get size and age
                    try:
                        size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                        age_days = (datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)).days
                        found_dirs.append({
                            "path": str(item.relative_to(self.base_path)),
                            "size_mb": round(size / 1024 / 1024, 2),
                            "age_days": age_days
                        })
                    except:
                        pass
        
        # Sort by size
        self.analysis["unnecessary_dirs"] = sorted(found_dirs, key=lambda x: x["size_mb"], reverse=True)
        
        # Print findings
        print(f"\n  Found {len(self.analysis['unnecessary_dirs'])} potentially unnecessary directories:")
        for dir_info in self.analysis["unnecessary_dirs"][:10]:
            print(f"    - {dir_info['path']} ({dir_info['size_mb']} MB, {dir_info['age_days']} days old)")
    
    def identify_essential_files(self):
        """Identify files that must be kept"""
        print("\n✅ Identifying essential files...")
        
        essential_patterns = [
            # Core system
            "unified_system/**/*.py",
            "src/**/*.py",
            # Main runners
            "run_unified_with_1password.py",
            # Configuration
            "requirements*.txt",
            ".env*",
            "*.yaml", "*.yml",
            "alembic.ini",
            "pyproject.toml",
            "setup.py",
            "Makefile",
            # Git files
            ".gitignore",
            # Current documentation
            "README*.md",
            "CLEANUP_AND_FIXES_SUMMARY.md",
            # Database
            "database/schema.sql",
            "alembic/**/*.py"
        ]
        
        self.analysis["keep_files"] = []
        for pattern in essential_patterns:
            for item in self.base_path.glob(pattern):
                if item.is_file():
                    self.analysis["keep_files"].append(str(item.relative_to(self.base_path)))
    
    def generate_recommendations(self):
        """Generate specific recommendations"""
        print("\n📋 Generating recommendations...")
        
        recommendations = {
            "immediate_archive": [],
            "review_then_archive": [],
            "consolidate": [],
            "keep": []
        }
        
        # Test files - keep only the most recent/comprehensive ones
        if self.analysis["duplicate_tests"]:
            print("\n  Test Files Recommendations:")
            for category, files in self.analysis["duplicate_tests"].items():
                if "siam_tests" in category:
                    keep = ["test_sicon_fixed.py", "test_sicon_gmail.py", "test_siam_complete.py"]
                    archive = [f for f in files if f not in keep]
                    if archive:
                        recommendations["immediate_archive"].extend([f"tests/{f}" for f in archive])
                        print(f"    Archive {len(archive)} duplicate SIAM tests")
                
                elif "api_tests" in category:
                    keep = ["test_api_startup.py", "test_api.py"]
                    archive = [f for f in files if f not in keep]
                    if archive:
                        recommendations["immediate_archive"].extend([f"tests/{f}" for f in archive])
                        print(f"    Archive {len(archive)} duplicate API tests")
        
        # Documentation - keep only the latest/most comprehensive
        if self.analysis["redundant_docs"]:
            print("\n  Documentation Recommendations:")
            for category, files in self.analysis["redundant_docs"].items():
                if "audit" in category:
                    # Keep only the most recent audit
                    recommendations["immediate_archive"].extend(files[1:])  # Archive all but first
                    print(f"    Archive {len(files)-1} old audit reports")
                
                elif "completion" in category:
                    # Keep only the final report
                    final_reports = [f for f in files if "FINAL" in f.upper()]
                    if final_reports:
                        archive = [f for f in files if f not in final_reports[:1]]
                        recommendations["immediate_archive"].extend(archive)
                        print(f"    Archive {len(archive)} old completion reports")
        
        # Scripts - remove duplicates
        if self.analysis["duplicate_scripts"]:
            print("\n  Script Recommendations:")
            for category, files in self.analysis["duplicate_scripts"].items():
                if "run_scripts" in category:
                    keep = ["run_unified_with_1password.py"]
                    archive = [f for f in files if not any(k in f for k in keep)]
                    if archive:
                        recommendations["review_then_archive"].extend(archive)
                        print(f"    Review {len(archive)} run scripts")
        
        # Directories
        if self.analysis["unnecessary_dirs"]:
            print("\n  Directory Recommendations:")
            # Archive all debug directories
            debug_dirs = [d["path"] for d in self.analysis["unnecessary_dirs"] 
                         if "debug" in d["path"] or "test_results" in d["path"]]
            if debug_dirs:
                recommendations["immediate_archive"].extend(debug_dirs)
                print(f"    Archive {len(debug_dirs)} debug/test directories")
            
            # Archive old extraction directories
            extraction_dirs = [d["path"] for d in self.analysis["unnecessary_dirs"]
                             if any(x in d["path"] for x in ["siam_", "sicon_", "sifin_", "demo_"])]
            if extraction_dirs:
                recommendations["immediate_archive"].extend(extraction_dirs[:20])  # First 20
                print(f"    Archive {min(len(extraction_dirs), 20)} old extraction directories")
        
        return recommendations
    
    def create_deduplication_script(self, recommendations):
        """Create a script to execute the deduplication"""
        script_content = f'''#!/usr/bin/env python3
"""
Execute deduplication based on analysis
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import shutil
from pathlib import Path
from datetime import datetime

def execute_deduplication():
    base = Path.cwd()
    archive_base = base / "archive" / "deduplication_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Files/dirs to archive immediately
    immediate_archive = {json.dumps(recommendations["immediate_archive"], indent=4)}
    
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
                print(f"  ✓ Archived: {{item_path}}")
            except Exception as e:
                failed_count += 1
                print(f"  ✗ Failed: {{item_path}} - {{e}}")
    
    print(f"\\n✅ Deduplication complete!")
    print(f"  Archived: {{archived_count}} items")
    print(f"  Failed: {{failed_count}} items")
    print(f"  Location: {{archive_base}}")
    
    # Create summary
    summary_path = archive_base / "DEDUPLICATION_SUMMARY.md"
    with open(summary_path, 'w') as f:
        f.write(f"# Deduplication Summary\\n\\n")
        f.write(f"Date: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}\\n\\n")
        f.write(f"## Statistics\\n")
        f.write(f"- Items archived: {{archived_count}}\\n")
        f.write(f"- Failed operations: {{failed_count}}\\n\\n")
        f.write(f"## Archived Items\\n\\n")
        for item in immediate_archive[:50]:  # First 50
            f.write(f"- {{item}}\\n")
        if len(immediate_archive) > 50:
            f.write(f"\\n... and {{len(immediate_archive) - 50}} more items\\n")

if __name__ == "__main__":
    execute_deduplication()
'''
        
        script_path = self.base_path / "execute_deduplication.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        print(f"\n💾 Created deduplication script: {script_path}")
        print("   Run with: python3 execute_deduplication.py")
    
    def save_analysis(self):
        """Save the full analysis"""
        analysis_path = self.base_path / "deduplication_analysis.json"
        
        # Convert defaultdicts to regular dicts for JSON serialization
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "duplicate_tests": dict(self.analysis["duplicate_tests"]),
            "duplicate_scripts": dict(self.analysis["duplicate_scripts"]),
            "redundant_docs": dict(self.analysis["redundant_docs"]),
            "unnecessary_dirs": self.analysis["unnecessary_dirs"],
            "keep_files_count": len(self.analysis["keep_files"]),
            "archive_candidates_count": len(self.analysis["archive_candidates"])
        }
        
        with open(analysis_path, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"\n💾 Saved full analysis to: {analysis_path}")
    
    def run(self):
        """Run the complete analysis"""
        print("🔍 Starting deep deduplication analysis...")
        
        self.analyze_test_files()
        self.analyze_documentation()
        self.analyze_scripts()
        self.analyze_directories()
        self.identify_essential_files()
        
        recommendations = self.generate_recommendations()
        
        # Summary
        print("\n📊 Summary:")
        print(f"  - Duplicate test categories: {len(self.analysis['duplicate_tests'])}")
        print(f"  - Redundant documentation categories: {len(self.analysis['redundant_docs'])}")
        print(f"  - Duplicate script categories: {len(self.analysis['duplicate_scripts'])}")
        print(f"  - Unnecessary directories: {len(self.analysis['unnecessary_dirs'])}")
        print(f"  - Essential files identified: {len(self.analysis['keep_files'])}")
        
        print(f"\n🎯 Recommendations:")
        print(f"  - Immediate archive: {len(recommendations['immediate_archive'])} items")
        print(f"  - Review then archive: {len(recommendations['review_then_archive'])} items")
        
        self.save_analysis()
        self.create_deduplication_script(recommendations)
        
        # Calculate potential space savings
        total_size = 0
        for dir_info in self.analysis["unnecessary_dirs"]:
            total_size += dir_info["size_mb"]
        
        print(f"\n💾 Potential space savings: ~{round(total_size, 1)} MB")


if __name__ == "__main__":
    analyzer = DeduplicationAnalyzer(Path.cwd())
    analyzer.run()