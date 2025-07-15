# Archive Directory

This directory contains historical and deprecated code that has been removed from the main system.

## Contents

### `archive_compressed_20250715.tar.gz`
- Compressed archive containing all historical cleanup folders
- Includes: aggressive_dedup, cleanup_20250711, debug_files, legacy_implementations, etc.
- Created during the July 15, 2025 major cleanup

### `broken_implementations/`
- Contains implementations that were attempted but didn't work properly
- `editorial_scripts_ultimate/` - The "ultimate" system that was moved from root
  - Contains optimized extractors and models
  - Moved here because the main `editorial_assistant/` system is the working implementation

## Purpose

This archive preserves the development history while keeping the main project clean and organized. The working system is now in the `editorial_assistant/` directory with `run_extraction.py` as the main entry point.

## Clean System Structure

The main project now has a clean structure:
- `editorial_assistant/` - Main working implementation
- `run_extraction.py` - Primary entry point
- `scripts/` - Organized utility scripts
- `tests/` - All test files
- `docs/` - Documentation
- `config/` - Configuration files
- `data/` - Data outputs

---
*Archive created during July 15, 2025 cleanup*
