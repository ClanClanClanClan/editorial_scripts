#!/usr/bin/env python3
"""
Comprehensive cleanup and reorganization of editorial_scripts folder

This script will:
1. Create a clean, organized folder structure
2. Move files to appropriate locations
3. Archive old/duplicate content
4. Remove unnecessary files
5. Create proper documentation
"""

import os
import shutil
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Define the new folder structure
NEW_STRUCTURE = {
    "src": {
        "core": "Core functionality and base classes",
        "extractors": {
            "siam": "SIAM journal extractors (SICON, SIFIN)",
            "scholarone": "ScholarOne extractors (MF, MOR)", 
            "editorial_manager": "Editorial Manager extractors (FS, JOTA, MAFE, NACO)"
        },
        "api": "FastAPI application and routers",
        "analytics": "Referee analytics and reporting",
        "ai": "AI integration services",
        "infrastructure": "Database, storage, scrapers",
        "utils": "Utility functions and helpers"
    },
    "tests": {
        "unit": "Unit tests",
        "integration": "Integration tests", 
        "fixtures": "Test data and fixtures"
    },
    "scripts": {
        "setup": "Setup and installation scripts",
        "maintenance": "Maintenance and cleanup scripts",
        "analysis": "Analysis and reporting scripts"
    },
    "data": {
        "cache": "Temporary cache files",
        "downloads": "Downloaded PDFs and documents",
        "exports": "Exported data and reports",
        "database": "Database files"
    },
    "docs": {
        "api": "API documentation",
        "guides": "User guides and tutorials",
        "technical": "Technical documentation",
        "reports": "Analysis and audit reports"
    },
    "config": "Configuration files",
    "output": {
        "sicon": "SICON extraction results",
        "sifin": "SIFIN extraction results",
        "mf": "MF extraction results", 
        "mor": "MOR extraction results",
        "other": "Other journal results"
    },
    "archive": {
        f"{datetime.now().strftime('%Y%m%d')}_cleanup": "Files archived during cleanup"
    }
}

class FolderReorganizer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.archive_path = self.base_path / "archive" / f"{datetime.now().strftime('%Y%m%d')}_cleanup"
        self.file_mappings = []
        self.stats = defaultdict(int)
        
    def analyze_current_structure(self):
        """Analyze the current folder structure and categorize files"""
        print("📊 Analyzing current folder structure...")
        
        # Categories of files to handle
        self.categories = {
            "test_files": [],
            "debug_files": [],
            "extraction_results": [],
            "source_code": [],
            "documentation": [],
            "config_files": [],
            "scripts": [],
            "virtual_envs": [],
            "temp_files": [],
            "archives": [],
            "data_files": []
        }
        
        # Walk through all files
        for item in self.base_path.iterdir():
            if item.name.startswith('.'):
                continue
                
            if item.is_file():
                self._categorize_file(item)
            elif item.is_dir():
                self._categorize_directory(item)
        
        # Print analysis results
        print("\n📋 Analysis Results:")
        for category, files in self.categories.items():
            print(f"  {category}: {len(files)} items")
    
    def _categorize_file(self, file_path: Path):
        """Categorize a single file"""
        name = file_path.name
        
        if name.startswith('test_') and name.endswith('.py'):
            self.categories["test_files"].append(file_path)
        elif name.startswith('debug_') or 'debug' in name:
            self.categories["debug_files"].append(file_path)
        elif name.endswith('.md'):
            self.categories["documentation"].append(file_path)
        elif name.endswith(('.yaml', '.yml', '.json', '.ini')) and 'config' in name.lower():
            self.categories["config_files"].append(file_path)
        elif name.endswith('.py'):
            if any(x in name for x in ['scraper', 'extractor', 'analyzer']):
                self.categories["scripts"].append(file_path)
            else:
                self.categories["source_code"].append(file_path)
        elif name.endswith(('.log', '.png', '.html', '.pdf')):
            self.categories["extraction_results"].append(file_path)
        else:
            self.categories["temp_files"].append(file_path)
    
    def _categorize_directory(self, dir_path: Path):
        """Categorize a directory"""
        name = dir_path.name
        
        if name.startswith('venv') or name == '__pycache__':
            self.categories["virtual_envs"].append(dir_path)
        elif 'archive' in name or 'legacy' in name or 'old' in name:
            self.categories["archives"].append(dir_path)
        elif any(x in name for x in ['sicon_', 'sifin_', 'mf_', 'mor_', 'extraction']):
            self.categories["extraction_results"].append(dir_path)
        elif name in ['data', 'cache', 'downloads', 'output']:
            self.categories["data_files"].append(dir_path)
        elif name.startswith('debug_'):
            self.categories["debug_files"].append(dir_path)
    
    def create_new_structure(self):
        """Create the new folder structure"""
        print("\n🏗️ Creating new folder structure...")
        
        def create_structure(base: Path, structure: dict, level=0):
            for name, value in structure.items():
                path = base / name
                if isinstance(value, dict):
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"{'  ' * level}📁 {name}/")
                    create_structure(path, value, level + 1)
                else:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"{'  ' * level}📁 {name}/ - {value}")
                    # Create README for each directory
                    readme_path = path / "README.md"
                    if not readme_path.exists():
                        readme_path.write_text(f"# {name}\n\n{value}\n")
        
        create_structure(self.base_path, NEW_STRUCTURE)
    
    def move_files(self):
        """Move files to their new locations"""
        print("\n📦 Moving files to new locations...")
        
        # Move test files
        for test_file in self.categories["test_files"]:
            if test_file.exists():
                dest = self._determine_test_destination(test_file)
                self._move_file(test_file, dest)
        
        # Archive debug files
        for debug_file in self.categories["debug_files"]:
            if debug_file.exists():
                self._archive_file(debug_file, "debug_files")
        
        # Move documentation
        for doc_file in self.categories["documentation"]:
            if doc_file.exists():
                dest = self._determine_doc_destination(doc_file)
                self._move_file(doc_file, dest)
        
        # Move source code files
        self._reorganize_source_code()
        
        # Archive old extraction results
        for result in self.categories["extraction_results"]:
            if result.exists():
                self._archive_file(result, "old_extractions")
    
    def _determine_test_destination(self, test_file: Path) -> Path:
        """Determine where a test file should go"""
        name = test_file.name
        
        if 'integration' in name or 'complete' in name or 'system' in name:
            return self.base_path / "tests" / "integration" / name
        else:
            return self.base_path / "tests" / "unit" / name
    
    def _determine_doc_destination(self, doc_file: Path) -> Path:
        """Determine where a documentation file should go"""
        name = doc_file.name.lower()
        
        if any(x in name for x in ['api', 'endpoint', 'route']):
            return self.base_path / "docs" / "api" / doc_file.name
        elif any(x in name for x in ['report', 'audit', 'analysis']):
            return self.base_path / "docs" / "reports" / doc_file.name
        elif any(x in name for x in ['guide', 'setup', 'install']):
            return self.base_path / "docs" / "guides" / doc_file.name
        else:
            return self.base_path / "docs" / "technical" / doc_file.name
    
    def _reorganize_source_code(self):
        """Reorganize source code files"""
        # Move unified_system to src
        unified_path = self.base_path / "unified_system"
        if unified_path.exists():
            # Move extractors
            extractors_src = unified_path / "extractors"
            if extractors_src.exists():
                for journal_type in extractors_src.iterdir():
                    if journal_type.is_dir():
                        dest = self.base_path / "src" / "extractors" / journal_type.name
                        if journal_type.name == "siam":
                            self._move_directory(journal_type, dest)
                        # Add other journal types as needed
        
        # Move other source files
        for src_file in self.categories["source_code"]:
            if src_file.exists() and src_file.parent == self.base_path:
                # Determine appropriate location
                if 'api' in src_file.name:
                    dest = self.base_path / "src" / "api" / src_file.name
                elif 'analytics' in src_file.name:
                    dest = self.base_path / "src" / "analytics" / src_file.name
                else:
                    dest = self.base_path / "src" / "utils" / src_file.name
                self._move_file(src_file, dest)
    
    def _move_file(self, source: Path, dest: Path):
        """Move a file to a new location"""
        if source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(source), str(dest))
                self.stats["moved"] += 1
                self.file_mappings.append({
                    "from": str(source.relative_to(self.base_path)),
                    "to": str(dest.relative_to(self.base_path))
                })
            except Exception as e:
                print(f"  ⚠️ Failed to move {source.name}: {e}")
                self.stats["failed"] += 1
    
    def _move_directory(self, source: Path, dest: Path):
        """Move a directory to a new location"""
        if source.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                if dest.exists():
                    # Merge directories
                    shutil.copytree(str(source), str(dest), dirs_exist_ok=True)
                    shutil.rmtree(str(source))
                else:
                    shutil.move(str(source), str(dest))
                self.stats["moved_dirs"] += 1
            except Exception as e:
                print(f"  ⚠️ Failed to move directory {source.name}: {e}")
                self.stats["failed"] += 1
    
    def _archive_file(self, source: Path, category: str):
        """Archive a file"""
        if source.exists():
            dest = self.archive_path / category / source.name
            self._move_file(source, dest)
            self.stats["archived"] += 1
    
    def cleanup_empty_directories(self):
        """Remove empty directories"""
        print("\n🧹 Cleaning up empty directories...")
        
        for root, dirs, files in os.walk(self.base_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.stats["removed_dirs"] += 1
    
    def create_manifest(self):
        """Create a manifest of all changes"""
        print("\n📝 Creating manifest...")
        
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "stats": dict(self.stats),
            "file_mappings": self.file_mappings,
            "new_structure": NEW_STRUCTURE
        }
        
        manifest_path = self.base_path / "docs" / "REORGANIZATION_MANIFEST.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Also create a human-readable summary
        summary_path = self.base_path / "docs" / "REORGANIZATION_SUMMARY.md"
        with open(summary_path, 'w') as f:
            f.write(f"# Folder Reorganization Summary\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Statistics\n\n")
            for key, value in self.stats.items():
                f.write(f"- {key.replace('_', ' ').title()}: {value}\n")
            f.write(f"\n## New Structure\n\n")
            f.write("```\neditorial_scripts/\n")
            self._write_structure_tree(f, NEW_STRUCTURE, 1)
            f.write("```\n")
    
    def _write_structure_tree(self, f, structure: dict, level: int):
        """Write structure tree to file"""
        for name, value in structure.items():
            f.write(f"{'  ' * level}├── {name}/\n")
            if isinstance(value, dict):
                self._write_structure_tree(f, value, level + 1)
    
    def run(self, dry_run: bool = True):
        """Run the reorganization"""
        print(f"\n🚀 Starting folder reorganization (dry_run={dry_run})...")
        
        self.analyze_current_structure()
        
        if dry_run:
            print("\n⚠️ DRY RUN MODE - No files will be moved")
            print("\nProposed new structure:")
            self._print_structure(NEW_STRUCTURE)
            return
        
        # Confirm before proceeding
        response = input("\n⚠️ This will reorganize the entire folder. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Reorganization cancelled")
            return
        
        self.create_new_structure()
        self.move_files()
        self.cleanup_empty_directories()
        self.create_manifest()
        
        print(f"\n✅ Reorganization complete!")
        print(f"  Files moved: {self.stats['moved']}")
        print(f"  Files archived: {self.stats['archived']}")
        print(f"  Directories cleaned: {self.stats['removed_dirs']}")
        print(f"  Failed operations: {self.stats['failed']}")
    
    def _print_structure(self, structure: dict, level: int = 0):
        """Print the structure tree"""
        for name, value in structure.items():
            print(f"{'  ' * level}├── {name}/")
            if isinstance(value, dict):
                self._print_structure(value, level + 1)


if __name__ == "__main__":
    import sys
    
    # Get the path to editorial_scripts
    base_path = Path(__file__).parent
    
    # Check for dry run flag
    dry_run = "--execute" not in sys.argv
    
    # Run reorganization
    reorganizer = FolderReorganizer(base_path)
    reorganizer.run(dry_run=dry_run)
    
    if dry_run:
        print("\n💡 To execute the reorganization, run:")
        print(f"   python {__file__} --execute")