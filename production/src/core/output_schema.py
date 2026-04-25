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
    "MF_WILEY": "Wiley ScienceConnect",
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
    "MF_WILEY": "Mathematical Finance",
}

# Logical grouping for journals that are the same publication on different
# platforms. Used by the dashboard, action items, and cross-journal report
# to render MF (legacy ScholarOne) + MF_WILEY (new Wiley platform) as a
# single "Mathematical Finance" group while keeping their data separate.
#
# Codes are stored in lowercase (matches journal code casing across the
# codebase). Values are the canonical group code (uppercase).
JOURNAL_GROUP_MAP = {
    "mf": "MF",
    "mf_wiley": "MF",
}

JOURNAL_GROUP_DISPLAY = {
    "MF": "Mathematical Finance",
    "MOR": "Mathematics of Operations Research",
    "FS": "Finance and Stochastics",
    "JOTA": "Journal of Optimization Theory and Applications",
    "MAFE": "Mathematical and Financial Economics",
    "SICON": "SIAM Journal on Control and Optimization",
    "SIFIN": "SIAM Journal on Financial Mathematics",
    "NACO": "Numerical Algebra, Control and Optimization",
}


def journal_group(journal_code: str) -> str:
    """Return the group code for a journal. Self-maps if no group is defined.

    Lowercased input handled. Output is uppercase.
    """
    if not journal_code:
        return ""
    return JOURNAL_GROUP_MAP.get(journal_code.lower(), journal_code.upper())


def journal_group_display(journal_code: str) -> str:
    """Return the human-readable display name for the journal's group."""
    group = journal_group(journal_code)
    return JOURNAL_GROUP_DISPLAY.get(group, group)


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
    "Wiley ScienceConnect": {
        "invited": ["invited_date", "dates.invited"],
        "agreed": ["accepted_date", "dates.agreed"],
        "due": ["due_date", "dates.due"],
        "returned": ["submitted_date", "dates.returned"],
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
    "reports",
    "web_profile",
    "statistics",
    "status_details",
    "platform_specific",
}

CANONICAL_REPORT_FIELDS = {
    "revision",
    "recommendation",
    "recommendation_raw",
    "manuscript_quality",
    "scores",
    "comments_to_author",
    "confidential_comments",
    "raw_text",
    "report_date",
    "word_count",
    "available",
    "extraction_status",
    "source",
    "attachments",
}

# Map raw recommendation strings (from any extractor) → canonical 5-value enum.
# Lookup is case-insensitive on the lowercased key.
RECOMMENDATION_CANONICAL_MAP = {
    # Accept variants
    "accept": "Accept",
    "accept as is": "Accept",
    "accept without revision": "Accept",
    "publish as is": "Accept",
    "publish": "Accept",
    "accept with no changes": "Accept",
    # Minor revision variants
    "minor revision": "Minor Revision",
    "minor revisions": "Minor Revision",
    "accept with minor revisions": "Minor Revision",
    "accept after minor revisions": "Minor Revision",
    "minor changes": "Minor Revision",
    "minor": "Minor Revision",
    # Major revision variants
    "major revision": "Major Revision",
    "major revisions": "Major Revision",
    "revise and resubmit": "Major Revision",
    "resubmit for review": "Major Revision",
    "accept with major revisions": "Major Revision",
    "accept after major revisions": "Major Revision",
    "reject and resubmit": "Major Revision",
    "major": "Major Revision",
    # Reject variants
    "reject": "Reject",
    "decline": "Reject",
    "reject - do not encourage resubmission": "Reject",
    "reject without resubmission": "Reject",
    "do not publish": "Reject",
    # Desk reject (treated as Reject for canonical purposes)
    "desk reject": "Reject",
    "desk rejection": "Reject",
}


def normalize_recommendation(raw: str) -> str:
    """Map a raw recommendation string to one of: Accept, Minor Revision, Major Revision, Reject, Unknown."""
    if not raw or not isinstance(raw, str):
        return "Unknown"
    key = raw.strip().lower()
    if not key:
        return "Unknown"
    if key in RECOMMENDATION_CANONICAL_MAP:
        return RECOMMENDATION_CANONICAL_MAP[key]
    # Substring fallback (catches "Accept (after minor revisions)" etc.)
    if "minor" in key and ("revis" in key or "change" in key):
        return "Minor Revision"
    if "major" in key and ("revis" in key or "change" in key):
        return "Major Revision"
    if "reject" in key or "decline" in key:
        return "Reject"
    if "accept" in key or "publish" in key:
        return "Accept"
    return "Unknown"


def _normalize_report(report: dict, default_revision: int = 0) -> dict:
    """Coerce a report dict to the canonical schema. Idempotent."""
    if not isinstance(report, dict):
        return {}

    out = dict(report)

    # Truncate long string fields
    for field, max_len in (
        ("comments_to_author", 20000),
        ("confidential_comments", 20000),
        ("raw_text", 20000),
    ):
        val = out.get(field, "")
        if isinstance(val, str) and len(val) > max_len:
            out[field] = val[:max_len]
        elif not isinstance(val, str):
            out[field] = ""

    # Recommendation: store both canonical and raw
    raw_rec = out.get("recommendation") or out.get("recommendation_raw") or ""
    if raw_rec:
        out["recommendation_raw"] = raw_rec
        canonical = normalize_recommendation(raw_rec)
        # Only overwrite recommendation if the canonical mapping found something specific
        if canonical != "Unknown" or not out.get("recommendation"):
            out["recommendation"] = canonical

    # Defaults for missing fields
    out.setdefault("revision", default_revision)
    out.setdefault("manuscript_quality", None)
    out.setdefault("scores", {})
    out.setdefault("comments_to_author", "")
    out.setdefault("confidential_comments", "")
    out.setdefault("raw_text", "")
    out.setdefault("report_date", None)
    out.setdefault("recommendation", "")
    out.setdefault("attachments", [])
    out.setdefault("source", "")
    out.setdefault("extraction_status", "ok")

    # Compute word_count from comments_to_author if missing
    if "word_count" not in out or not isinstance(out.get("word_count"), int):
        wc_text = out.get("comments_to_author") or out.get("raw_text") or ""
        out["word_count"] = len(wc_text.split())

    # Available = there's anything actionable
    out["available"] = bool(
        out.get("comments_to_author")
        or out.get("raw_text")
        or out.get("scores")
        or (out.get("recommendation") and out.get("recommendation") != "Unknown")
        or out.get("attachments")
    )

    # Strip non-canonical keys into platform_specific to keep schema clean
    extra = {}
    for k in list(out.keys()):
        if k not in CANONICAL_REPORT_FIELDS and k != "platform_specific":
            extra[k] = out.pop(k)
    if extra:
        ps = out.setdefault("platform_specific", {})
        if isinstance(ps, dict):
            ps.update(extra)

    return out


def _finalize_referee_reports(ref: dict) -> None:
    """Make referee.reports canonical (list of normalized reports, sorted by revision).
    Sets referee.report = reports[-1] for backward compatibility."""
    reports = ref.get("reports")
    single = ref.get("report")

    # Coerce: if only `report` (singular) exists, wrap in list
    if isinstance(single, dict) and not isinstance(reports, list):
        reports = [single]
    elif not isinstance(reports, list):
        reports = []
    elif isinstance(single, dict) and isinstance(reports, list):
        # Both exist: ensure singular is in the list (avoid duplicates by identity)
        if single not in reports:
            # Only append if it adds new info (e.g. has comments not in any reports entry)
            single_text = (single.get("comments_to_author") or "").strip()
            existing_texts = {(r.get("comments_to_author") or "").strip() for r in reports}
            if single_text and single_text not in existing_texts:
                reports.append(single)

    # Normalize each entry
    normalized = []
    for idx, rpt in enumerate(reports):
        if isinstance(rpt, dict):
            normalized.append(_normalize_report(rpt, default_revision=idx))

    # Sort by revision ascending; missing revisions kept stable
    normalized.sort(key=lambda r: (r.get("revision") if r.get("revision") is not None else 0))

    if normalized:
        ref["reports"] = normalized
        ref["report"] = normalized[-1]
    else:
        # No reports — keep referee.reports as empty list, drop singular
        ref["reports"] = []
        ref.pop("report", None)


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
            if not val:
                ps = ref.get("platform_specific") or {}
                val = ps.get(source_field)
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

    # Canonicalize report(s): build referee.reports list, mirror latest into referee.report
    _finalize_referee_reports(ref)

    # If a top-level recommendation is missing but the latest report has one, surface it
    if not ref.get("recommendation") and isinstance(ref.get("report"), dict):
        latest_rec = ref["report"].get("recommendation") or ref["report"].get("recommendation_raw")
        if latest_rec:
            ref["recommendation"] = latest_rec

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
