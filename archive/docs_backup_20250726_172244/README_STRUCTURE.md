# Editorial Scripts - Organized Structure

*Cleaned up on 2025-07-14*

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
