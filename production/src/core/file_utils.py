"""Shared file utilities for loading extraction outputs."""

import json
from pathlib import Path

OUTPUTS_DIR = Path(__file__).resolve().parents[2] / "outputs"

_SKIP_PATTERNS = ("BASELINE", "debug", "rec_", "partial", "ae_", "recommendation")


def list_extraction_files(journal: str) -> list[Path]:
    journal_dir = OUTPUTS_DIR / journal.lower()
    if not journal_dir.exists():
        return []
    return sorted(
        [f for f in journal_dir.glob("*.json") if not any(s in f.name for s in _SKIP_PATTERNS)],
        key=lambda f: f.name,
        reverse=True,
    )


def find_latest_output(journal: str) -> Path | None:
    files = list_extraction_files(journal)
    return files[0] if files else None


def load_latest_extraction(journal: str) -> dict | None:
    path = find_latest_output(journal)
    if not path:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
