#!/usr/bin/env python3
"""
Canonical output schema normalization for all journal extractors.
Converts platform-specific JSON output to a unified schema (v1.0.0).

Usage: call normalize_wrapper(results_dict, journal_code) before json.dump().
"""

import re
from datetime import datetime
from typing import Optional

SCHEMA_VERSION = "1.0.0"

PLATFORM_MAP = {
    "MF": "ScholarOne",
    "MOR": "ScholarOne",
    "FS": "Email (Gmail)",
    "JOTA": "Editorial Manager",
    "MAFE": "Editorial Manager",
    "SICON": "SIAM",
    "SIFIN": "SIAM",
    "NACO": "EditFlow (MSP)",
}

JOURNAL_NAME_MAP = {
    "MF": "Mathematical Finance",
    "MOR": "Mathematics of Operations Research",
    "FS": "Finance and Stochastics",
    "JOTA": "Journal of Optimization Theory and Applications",
    "MAFE": "Mathematical and Financial Economics",
    "SICON": "SIAM Journal on Control and Optimization",
    "SIFIN": "SIAM Journal on Financial Mathematics",
    "NACO": "Numerical Algebra, Control and Optimization",
}

DATE_FORMATS = [
    "%d-%b-%Y",
    "%d %b %Y",
    "%Y-%m-%d",
    "%b %d, %Y",
    "%m/%d/%Y",
    "%d-%B-%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
]

REFEREE_DATE_MAPPINGS = {
    "ScholarOne": {
        "invited": ["invitation_date", "dates.invited"],
        "agreed": ["agreed_date", "dates.agreed"],
        "due": ["due_date", "dates.due"],
        "returned": ["review_returned_date", "dates.returned"],
    },
    "Editorial Manager": {
        "invited": ["contact_date"],
        "agreed": ["acceptance_date"],
        "due": ["due_date"],
        "returned": ["received_date"],
    },
    "SIAM": {
        "invited": ["contact_date"],
        "agreed": ["acceptance_date"],
        "due": ["due_date"],
        "returned": ["received_date"],
    },
    "Email (Gmail)": {
        "invited": ["invited_date", "dates.invited"],
        "agreed": ["response_date", "dates.agreed"],
        "due": ["dates.due"],
        "returned": ["report_date", "dates.returned"],
    },
    "EditFlow (MSP)": {
        "invited": ["contacted_date"],
        "agreed": [],
        "due": [],
        "returned": [],
    },
}

CANONICAL_MANUSCRIPT_FIELDS = {
    "manuscript_id",
    "title",
    "abstract",
    "keywords",
    "submission_date",
    "status",
    "category",
    "is_revision",
    "revision_number",
    "article_type",
    "authors",
    "referees",
    "editors",
    "documents",
    "audit_trail",
    "communication_timeline",
    "timeline_analytics",
    "platform_specific",
    "extraction_timestamp",
    "extracted_at",
}

CANONICAL_AUTHOR_FIELDS = {
    "name",
    "email",
    "institution",
    "department",
    "country",
    "orcid",
    "is_corresponding",
    "web_profile",
    "platform_specific",
}

CANONICAL_REFEREE_FIELDS = {
    "name",
    "email",
    "institution",
    "department",
    "country",
    "orcid",
    "status",
    "dates",
    "recommendation",
    "report",
    "web_profile",
    "statistics",
    "status_details",
    "platform_specific",
}

PROMOTED_METADATA_FIELDS = [
    "title",
    "abstract",
    "keywords",
    "submission_date",
    "manuscript_type",
    "article_type",
    "revision_number",
    "status",
    "category",
]


def normalize_date(date_str) -> Optional[str]:
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return None
    date_str = date_str.strip()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    if "," in date_str and any(x in date_str for x in ["+", "GMT", "-0", "+0", "-1", "+1"]):
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    if re.match(r"^\d{8}_\d{6}$", date_str):
        try:
            return datetime.strptime(date_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d")
        except Exception:
            pass

    clean = date_str.split()[0:3]
    if len(clean) >= 1:
        for test_str in [" ".join(clean), clean[0]]:
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(test_str, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def normalize_keywords(keywords) -> list:
    if keywords is None:
        return []
    if isinstance(keywords, list):
        return keywords
    if isinstance(keywords, str):
        if "," in keywords:
            return [k.strip() for k in keywords.split(",") if k.strip()]
        if ";" in keywords:
            return [k.strip() for k in keywords.split(";") if k.strip()]
        return [keywords.strip()] if keywords.strip() else []
    return []


def _normalize_author_corresponding(author: dict) -> bool:
    if "is_corresponding" in author:
        return bool(author["is_corresponding"])
    if "corresponding_author" in author:
        return bool(author["corresponding_author"])
    role = author.get("role", "")
    if isinstance(role, str) and "corresponding" in role.lower():
        return True
    return False


def _resolve_nested_field(obj: dict, field_path: str):
    if "." in field_path:
        parts = field_path.split(".")
        val = obj
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return None
        return val
    return obj.get(field_path)


def _promote_metadata_fields(manuscript: dict) -> None:
    metadata = manuscript.get("metadata", {})
    if not isinstance(metadata, dict):
        return

    for field in PROMOTED_METADATA_FIELDS:
        if field in metadata and not manuscript.get(field):
            manuscript[field] = metadata[field]

    if not manuscript.get("article_type"):
        manuscript["article_type"] = metadata.get("manuscript_type") or metadata.get("article_type")

    if not manuscript.get("status"):
        manuscript["status"] = metadata.get("current_stage") or metadata.get("status")


def _collect_platform_specific(obj: dict, canonical_fields: set) -> None:
    ps = obj.get("platform_specific", {})
    for key in list(obj.keys()):
        if key not in canonical_fields:
            ps[key] = obj.pop(key)
    if ps:
        obj["platform_specific"] = ps


def _normalize_referee(ref: dict, platform: str) -> None:
    mapping = REFEREE_DATE_MAPPINGS.get(platform, {})
    canonical_dates = {}

    for canon_key, source_fields in mapping.items():
        for source_field in source_fields:
            val = _resolve_nested_field(ref, source_field)
            if val:
                canonical_dates[canon_key] = normalize_date(str(val))
                break
        if canon_key not in canonical_dates:
            canonical_dates[canon_key] = None

    if not mapping:
        canonical_dates = {
            "invited": None,
            "agreed": None,
            "due": None,
            "returned": None,
        }

    ref["dates"] = canonical_dates

    if not ref.get("institution") and ref.get("affiliation"):
        ref["institution"] = ref["affiliation"]
    if not ref.get("institution") and ref.get("affiliation_full"):
        ref["institution"] = ref["affiliation_full"]

    _collect_platform_specific(ref, CANONICAL_REFEREE_FIELDS)


def _normalize_author(author: dict, platform: str) -> None:
    author["is_corresponding"] = _normalize_author_corresponding(author)

    if not author.get("institution") and author.get("affiliation"):
        author["institution"] = author["affiliation"]
    if not author.get("institution") and author.get("affiliation_full"):
        author["institution"] = author["affiliation_full"]

    _collect_platform_specific(author, CANONICAL_AUTHOR_FIELDS)


def _normalize_manuscript(ms: dict, journal_code: str, platform: str) -> None:
    if ms.get("id") and not ms.get("manuscript_id"):
        ms["manuscript_id"] = ms["id"]

    _promote_metadata_fields(ms)

    if ms.get("submission_date"):
        original = ms["submission_date"]
        normalized = normalize_date(str(original))
        ms["submission_date"] = normalized

    ms["keywords"] = normalize_keywords(ms.get("keywords"))

    if not ms.get("article_type") and ms.get("manuscript_type"):
        ms["article_type"] = ms["manuscript_type"]

    for author in ms.get("authors", []):
        _normalize_author(author, platform)

    for ref in ms.get("referees", []):
        _normalize_referee(ref, platform)

    _collect_platform_specific(ms, CANONICAL_MANUSCRIPT_FIELDS)


def normalize_wrapper(results: dict, journal_code: str) -> dict:
    results["schema_version"] = SCHEMA_VERSION
    results.setdefault("journal", journal_code)
    results.setdefault("journal_name", JOURNAL_NAME_MAP.get(journal_code, ""))
    results.setdefault("platform", PLATFORM_MAP.get(journal_code, ""))
    results.setdefault("extractor_version", "2.0.0")
    results.setdefault("errors", [])

    if "extraction_time" in results and "extraction_timestamp" not in results:
        ts = results.pop("extraction_time")
        try:
            results["extraction_timestamp"] = datetime.strptime(ts, "%Y%m%d_%H%M%S").isoformat()
        except Exception:
            results["extraction_timestamp"] = datetime.now().isoformat()
    results.setdefault("extraction_timestamp", datetime.now().isoformat())

    results.setdefault("summary", {})

    platform = PLATFORM_MAP.get(journal_code, "")
    for ms in results.get("manuscripts", []):
        _normalize_manuscript(ms, journal_code, platform)

    return results
