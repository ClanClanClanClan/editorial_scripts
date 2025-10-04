# Archive Directory

This directory contains historical and deprecated assets that should remain out of the active codebase. Anything that is no longer needed for day-to-day development should be moved here (or deleted) to keep the repository root small.

## Notable folders

- `broken_implementations/` – experiments that never shipped
- `legacy_implementations_20250726/` – the pre-cleanup production tree
- `data_snapshots/` – frozen JSON/CSV exports moved out of the repository root (contains PII; keep private)
- `logs/` – historical extraction logs
- `docs_backup_*` – point-in-time copies of documentation

Feel free to add sub-folders, but keep a short README alongside large drops so future audits can see what changed and why.

The working production pipeline continues to live under `production/src/extractors`; the `archive/` tree is strictly for reference.
