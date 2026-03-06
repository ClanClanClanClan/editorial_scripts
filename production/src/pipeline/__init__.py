"""Referee recommendation pipeline: shared constants and utilities."""

import json
import unicodedata
from pathlib import Path

PRODUCTION_DIR = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PRODUCTION_DIR / "outputs"
MODELS_DIR = PRODUCTION_DIR / "models"

JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"]

H_INDEX_CAP = 40

FREEMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "mail.com",
    "protonmail.com",
    "icloud.com",
    "live.com",
    "msn.com",
    "ymail.com",
    "qq.com",
    "163.com",
    "126.com",
}


def _load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def normalize_name(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
