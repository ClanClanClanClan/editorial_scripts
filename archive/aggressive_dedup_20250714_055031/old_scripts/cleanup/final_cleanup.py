#!/usr/bin/env python3
"""Final cleanup - move remaining files to organized locations"""

import shutil
from pathlib import Path
from datetime import datetime

def final_cleanup():
    """Move remaining files to appropriate locations"""
    base = Path.cwd()
    
    print("🧹 Final cleanup pass...\n")
    
    # Create directories
    (base / "archive" / "screenshots").mkdir(parents=True, exist_ok=True)
    (base / "archive" / "logs").mkdir(parents=True, exist_ok=True)
    (base / "archive" / "old_extractions").mkdir(parents=True, exist_ok=True)
    (base / "scripts" / "cleanup").mkdir(parents=True, exist_ok=True)
    (base / "scripts" / "setup").mkdir(parents=True, exist_ok=True)
    
    # Move screenshots
    print("📸 Moving screenshots...")
    screenshot_count = 0
    for png in base.glob("*.png"):
        try:
            dest = base / "archive" / "screenshots" / png.name
            shutil.move(str(png), str(dest))
            screenshot_count += 1
        except Exception as e:
            print(f"  ⚠️ Failed to move {png.name}: {e}")
    print(f"  ✅ Moved {screenshot_count} screenshots")
    
    # Move HTML files
    print("\n📄 Moving HTML files...")
    html_count = 0
    for html in base.glob("*.html"):
        try:
            dest = base / "archive" / "old_extractions" / html.name
            shutil.move(str(html), str(dest))
            html_count += 1
        except Exception as e:
            print(f"  ⚠️ Failed to move {html.name}: {e}")
    print(f"  ✅ Moved {html_count} HTML files")
    
    # Move log files
    print("\n📝 Moving log files...")
    log_count = 0
    for log in base.glob("*.log"):
        try:
            dest = base / "archive" / "logs" / log.name
            shutil.move(str(log), str(dest))
            log_count += 1
        except Exception as e:
            print(f"  ⚠️ Failed to move {log.name}: {e}")
    print(f"  ✅ Moved {log_count} log files")
    
    # Move cleanup scripts
    print("\n🔧 Organizing scripts...")
    script_count = 0
    cleanup_scripts = [
        "cleanup_and_organize.py",
        "cleanup_and_reorganize.py", 
        "safe_cleanup.py",
        "quick_cleanup.py",
        "final_cleanup.py",
        "cleanup_report_*.json"
    ]
    
    for pattern in cleanup_scripts:
        for script in base.glob(pattern):
            if script.is_file():
                try:
                    dest = base / "scripts" / "cleanup" / script.name
                    shutil.move(str(script), str(dest))
                    script_count += 1
                except:
                    pass
    
    # Move setup scripts
    setup_scripts = [
        "setup_*.py",
        "fix_*.py",
        "migrate_*.py",
        "*_setup.py"
    ]
    
    for pattern in setup_scripts:
        for script in base.glob(pattern):
            if script.is_file():
                try:
                    dest = base / "scripts" / "setup" / script.name
                    shutil.move(str(script), str(dest))
                    script_count += 1
                except:
                    pass
    
    print(f"  ✅ Organized {script_count} scripts")
    
    # Move old extraction directories
    print("\n📦 Archiving old extraction directories...")
    extraction_count = 0
    patterns = [
        "siam_*", "sicon_*", "sifin_*", "mf_*", "mor_*",
        "*_extraction_*", "*_debug_*", "*_output",
        "demo_*", "enhanced_*", "fixed_*"
    ]
    
    for pattern in patterns:
        for item in base.glob(pattern):
            if item.is_dir() and item.name not in ["output", "unified_system", "archive"]:
                try:
                    dest = base / "archive" / "old_extractions" / item.name
                    shutil.move(str(item), str(dest))
                    extraction_count += 1
                except Exception as e:
                    print(f"  ⚠️ Failed to move {item.name}: {e}")
    
    print(f"  ✅ Archived {extraction_count} extraction directories")
    
    # Move miscellaneous Python files
    print("\n🐍 Organizing Python files...")
    py_count = 0
    misc_py_files = [
        "run_*.py",
        "validate_*.py", 
        "verify_*.py",
        "test_*.py",  # Any remaining test files
        "debug_*.py",
        "patch_*.py"
    ]
    
    for pattern in misc_py_files:
        for py_file in base.glob(pattern):
            if py_file.is_file() and py_file.parent == base:
                try:
                    if "test_" in py_file.name:
                        dest = base / "tests" / py_file.name
                    else:
                        dest = base / "scripts" / py_file.name
                    shutil.move(str(py_file), str(dest))
                    py_count += 1
                except:
                    pass
    
    print(f"  ✅ Organized {py_count} Python files")
    
    # Create main README
    readme_content = f"""# Editorial Scripts

A comprehensive system for extracting manuscript and referee data from editorial management systems.

## Quick Start

1. **Setup environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv_fresh/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure credentials**:
   - Copy `.env.example` to `.env`
   - Add your journal credentials

3. **Run extractions**:
   ```bash
   # SICON extraction
   python run_unified_with_1password.py --journal SICON
   
   # Test extraction
   python test_sicon_fixed.py
   ```

## Project Structure

- **unified_system/** - Core extraction system
  - `extractors/` - Journal-specific extractors
  - `core/` - Base classes and utilities
  
- **src/** - Additional source code
  - `api/` - FastAPI application
  - `analytics/` - Referee analytics
  - `ai/` - AI integration
  
- **output/** - Extraction results organized by journal
- **tests/** - Test files
- **docs/** - Documentation
- **scripts/** - Utility scripts
- **config/** - Configuration files
- **data/** - Data storage and cache

## Key Components

1. **SIAM Extractors** (SICON, SIFIN) - Working ✅
2. **ScholarOne Extractors** (MF, MOR) - In development
3. **Editorial Manager Extractors** - Planned
4. **Gmail Integration** - For cross-checking
5. **AI Analysis** - For manuscript insights

## Recent Updates

- Fixed SICON title and author extraction
- Improved referee email extraction  
- Cleaned up and organized folder structure
- Added comprehensive documentation

*Last updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    with open(base / "README.md", 'w') as f:
        f.write(readme_content)
    
    print("\n✅ Final cleanup complete!")
    print("📄 Updated main README.md")
    
    # Print summary of what's left in root
    print("\n📊 Remaining in root directory:")
    important_files = [
        "README.md",
        "requirements.txt",
        "requirements-dev.txt",
        ".env",
        ".env.example",
        ".gitignore",
        "setup.py",
        "pyproject.toml",
        "alembic.ini",
        "Makefile"
    ]
    
    remaining = []
    for item in base.iterdir():
        if item.name.startswith('.'):
            continue
        if item.is_file() and item.name not in important_files:
            remaining.append(item.name)
        elif item.is_dir() and item.name not in [
            "unified_system", "src", "tests", "docs", "scripts",
            "output", "data", "config", "archive", "venv", "venv_fresh",
            "analytics", "alembic", "ai_analysis_cache", "attachments",
            "backups", "cache", "crosscheck_results_20250713_165040"
        ]:
            remaining.append(f"{item.name}/")
    
    if remaining:
        print("  Files/dirs to review manually:")
        for item in sorted(remaining)[:20]:  # Show first 20
            print(f"    - {item}")
        if len(remaining) > 20:
            print(f"    ... and {len(remaining) - 20} more")
    else:
        print("  ✨ Root directory is clean!")

if __name__ == "__main__":
    final_cleanup()