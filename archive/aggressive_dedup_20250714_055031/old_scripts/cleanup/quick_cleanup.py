#!/usr/bin/env python3
"""Quick and safe cleanup of the most important items"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def quick_cleanup():
    """Perform quick cleanup of the most obvious issues"""
    base = Path.cwd()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("🧹 Starting quick cleanup...\n")
    
    # 1. Create organized directories
    print("📁 Creating organized directories...")
    dirs_to_create = [
        "tests",
        "docs/reports", 
        "docs/guides",
        "archive/old_tests",
        "archive/old_debug",
        "scripts"
    ]
    
    for dir_name in dirs_to_create:
        (base / dir_name).mkdir(parents=True, exist_ok=True)
    
    # 2. Move test files
    print("\n📋 Moving test files...")
    test_count = 0
    for test_file in base.glob("test_*.py"):
        if test_file.is_file() and test_file.parent == base:
            try:
                dest = base / "tests" / test_file.name
                shutil.move(str(test_file), str(dest))
                test_count += 1
            except Exception as e:
                print(f"  ⚠️ Failed to move {test_file.name}: {e}")
    print(f"  ✅ Moved {test_count} test files")
    
    # 3. Archive old debug files
    print("\n🗄️ Archiving debug files...")
    debug_count = 0
    debug_patterns = ["debug_*.html", "debug_*.png", "*_debug_*"]
    
    for pattern in debug_patterns:
        for debug_file in base.glob(pattern):
            if debug_file.is_file():
                try:
                    dest = base / "archive" / "old_debug" / debug_file.name
                    shutil.move(str(debug_file), str(dest))
                    debug_count += 1
                except Exception as e:
                    pass
    print(f"  ✅ Archived {debug_count} debug files")
    
    # 4. Move documentation
    print("\n📚 Organizing documentation...")
    doc_count = 0
    for doc in base.glob("*.md"):
        if doc.name not in ["README.md"] and doc.is_file():
            try:
                if "report" in doc.name.lower() or "audit" in doc.name.lower():
                    dest = base / "docs" / "reports" / doc.name
                elif "guide" in doc.name.lower() or "setup" in doc.name.lower():
                    dest = base / "docs" / "guides" / doc.name
                else:
                    dest = base / "docs" / doc.name
                
                shutil.move(str(doc), str(dest))
                doc_count += 1
            except Exception as e:
                print(f"  ⚠️ Failed to move {doc.name}: {e}")
    print(f"  ✅ Organized {doc_count} documentation files")
    
    # 5. Clean up Python cache
    print("\n🗑️ Removing Python cache...")
    cache_count = 0
    for cache_dir in base.rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir)
            cache_count += 1
        except:
            pass
    
    for pyc_file in base.rglob("*.pyc"):
        try:
            pyc_file.unlink()
            cache_count += 1
        except:
            pass
    print(f"  ✅ Removed {cache_count} cache items")
    
    # 6. Create a simple README for the new structure
    readme_content = f"""# Editorial Scripts - Organized Structure

*Cleaned up on {datetime.now().strftime('%Y-%m-%d')}*

## Directory Structure

- **unified_system/** - Main extraction system (DO NOT MODIFY)
  - extractors/ - Journal-specific extractors
  - core/ - Core functionality
  
- **tests/** - All test files
- **docs/** - Documentation
  - reports/ - Analysis and audit reports
  - guides/ - Setup and usage guides
  
- **output/** - Extraction results by journal
- **scripts/** - Utility and maintenance scripts
- **archive/** - Archived old files
  - old_debug/ - Old debug files
  - old_tests/ - Old test files
  
- **data/** - Data files and cache
- **config/** - Configuration files

## Key Files

- `run_unified_with_1password.py` - Main extraction runner
- `test_sicon_fixed.py` - Test SICON extraction
- `requirements.txt` - Python dependencies
"""
    
    readme_path = base / "README_STRUCTURE.md"
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    print(f"\n✅ Quick cleanup complete!")
    print(f"📄 Created README_STRUCTURE.md with new organization info")

if __name__ == "__main__":
    quick_cleanup()