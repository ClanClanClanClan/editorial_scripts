import pytest
from core.output_schema import (
    CANONICAL_AUTHOR_FIELDS,
    CANONICAL_MANUSCRIPT_FIELDS,
    CANONICAL_REFEREE_FIELDS,
    CANONICAL_REPORT_FIELDS,
    _collect_platform_specific,
    _finalize_referee_reports,
    _normalize_author,
    _normalize_author_corresponding,
    _normalize_referee,
    _normalize_report,
    _resolve_nested_field,
    normalize_date,
    normalize_keywords,
    normalize_recommendation,
    normalize_wrapper,
)


class TestNormalizeDate:
    def test_iso_passthrough(self):
        assert normalize_date("2025-01-15") == "2025-01-15"

    def test_dd_mon_yyyy(self):
        assert normalize_date("15-Jan-2025") == "2025-01-15"

    def test_dd_month_yyyy(self):
        assert normalize_date("15 Jan 2025") == "2025-01-15"

    def test_mon_dd_yyyy(self):
        assert normalize_date("Jan 15, 2025") == "2025-01-15"

    def test_slash_format(self):
        assert normalize_date("01/15/2025") == "2025-01-15"

    def test_compact_timestamp(self):
        assert normalize_date("20250115_143000") == "2025-01-15"

    def test_iso_with_time(self):
        assert normalize_date("2025-01-15T14:30:00") == "2025-01-15"

    def test_none(self):
        assert normalize_date(None) is None

    def test_empty(self):
        assert normalize_date("") is None

    def test_garbage(self):
        assert normalize_date("not-a-date") is None

    def test_whitespace_only(self):
        assert normalize_date("   ") is None

    def test_rfc2822(self):
        result = normalize_date("Mon, 15 Jan 2025 14:30:00 +0000")
        assert result == "2025-01-15"


class TestNormalizeKeywords:
    def test_comma_separated(self):
        assert normalize_keywords("a, b, c") == ["a", "b", "c"]

    def test_semicolon_separated(self):
        assert normalize_keywords("a; b; c") == ["a", "b", "c"]

    def test_list_passthrough(self):
        assert normalize_keywords(["a", "b"]) == ["a", "b"]

    def test_none(self):
        assert normalize_keywords(None) == []

    def test_empty_string(self):
        assert normalize_keywords("") == []

    def test_single_keyword(self):
        assert normalize_keywords("finance") == ["finance"]


class TestAuthorCorresponding:
    def test_is_corresponding_true(self):
        assert _normalize_author_corresponding({"is_corresponding": True}) is True

    def test_is_corresponding_false(self):
        assert _normalize_author_corresponding({"is_corresponding": False}) is False

    def test_corresponding_author_field(self):
        assert _normalize_author_corresponding({"corresponding_author": True}) is True

    def test_role_field(self):
        assert _normalize_author_corresponding({"role": "Corresponding Author"}) is True

    def test_no_flag(self):
        assert _normalize_author_corresponding({"name": "Smith"}) is False


class TestResolveNestedField:
    def test_simple_key(self):
        assert _resolve_nested_field({"a": 1}, "a") == 1

    def test_dot_path(self):
        assert _resolve_nested_field({"a": {"b": 2}}, "a.b") == 2

    def test_missing_key(self):
        assert _resolve_nested_field({"a": 1}, "b") is None

    def test_missing_nested(self):
        assert _resolve_nested_field({"a": {"b": 2}}, "a.c") is None

    def test_non_dict_intermediate(self):
        assert _resolve_nested_field({"a": "string"}, "a.b") is None


class TestCollectPlatformSpecific:
    def test_moves_extra_fields(self):
        obj = {"name": "Smith", "email": "a@b.com", "custom_field": "value"}
        _collect_platform_specific(obj, CANONICAL_AUTHOR_FIELDS)
        assert "custom_field" not in obj
        assert obj["platform_specific"]["custom_field"] == "value"

    def test_keeps_canonical_fields(self):
        obj = {"name": "Smith", "email": "a@b.com"}
        _collect_platform_specific(obj, CANONICAL_AUTHOR_FIELDS)
        assert obj["name"] == "Smith"
        assert obj["email"] == "a@b.com"


class TestNormalizeRefereeDates:
    def test_scholarone(self):
        ref = {"name": "R1", "invitation_date": "15-Jan-2025", "agreed_date": "20-Jan-2025"}
        _normalize_referee(ref, "ScholarOne")
        assert ref["dates"]["invited"] == "2025-01-15"
        assert ref["dates"]["agreed"] == "2025-01-20"
        assert ref["dates"]["due"] is None
        assert ref["dates"]["returned"] is None

    def test_editorial_manager(self):
        ref = {"name": "R1", "contact_date": "15 Jan 2025", "received_date": "20 Jan 2025"}
        _normalize_referee(ref, "Editorial Manager")
        assert ref["dates"]["invited"] == "2025-01-15"
        assert ref["dates"]["returned"] == "2025-01-20"

    def test_siam(self):
        ref = {"name": "R1", "contact_date": "2025-01-15"}
        _normalize_referee(ref, "SIAM")
        assert ref["dates"]["invited"] == "2025-01-15"

    def test_unknown_platform(self):
        ref = {"name": "R1"}
        _normalize_referee(ref, "UnknownPlatform")
        assert ref["dates"] == {"invited": None, "agreed": None, "due": None, "returned": None}

    def test_nested_dates_field(self):
        ref = {"name": "R1", "dates": {"invited": "2025-01-15", "agreed": "2025-01-20"}}
        _normalize_referee(ref, "ScholarOne")
        assert ref["dates"]["invited"] == "2025-01-15"
        assert ref["dates"]["agreed"] == "2025-01-20"


class TestNormalizeWrapper:
    def test_smoke(self):
        results = {"manuscripts": [{"id": "MOR-2025-0001"}]}
        out = normalize_wrapper(results, "MOR")
        assert out["schema_version"] == "1.0.0"
        assert out["journal"] == "MOR"
        assert out["journal_name"] == "Mathematics of Operations Research"
        assert out["platform"] == "ScholarOne"
        assert "extraction_timestamp" in out

    def test_preserves_existing_journal(self):
        results = {"manuscripts": [], "journal": "CUSTOM"}
        out = normalize_wrapper(results, "MOR")
        assert out["journal"] == "CUSTOM"

    def test_manuscript_id_promotion(self):
        results = {"manuscripts": [{"id": "X-001", "title": "Test"}]}
        normalize_wrapper(results, "MF")
        assert results["manuscripts"][0]["manuscript_id"] == "X-001"


class TestNormalizeRecommendation:
    def test_accept(self):
        assert normalize_recommendation("Accept") == "Accept"
        assert normalize_recommendation("publish as is") == "Accept"
        assert normalize_recommendation("Accept without revision") == "Accept"

    def test_minor_revision(self):
        assert normalize_recommendation("Minor Revision") == "Minor Revision"
        assert normalize_recommendation("minor revisions") == "Minor Revision"
        assert normalize_recommendation("Accept with minor revisions") == "Minor Revision"

    def test_major_revision(self):
        assert normalize_recommendation("Major Revision") == "Major Revision"
        assert normalize_recommendation("revise and resubmit") == "Major Revision"
        assert normalize_recommendation("reject and resubmit") == "Major Revision"

    def test_reject(self):
        assert normalize_recommendation("Reject") == "Reject"
        assert normalize_recommendation("decline") == "Reject"
        assert normalize_recommendation("desk reject") == "Reject"

    def test_unknown(self):
        assert normalize_recommendation("") == "Unknown"
        assert normalize_recommendation(None) == "Unknown"
        assert normalize_recommendation("???") == "Unknown"

    def test_substring_fallback(self):
        # Free-form variants caught by substring rules
        assert normalize_recommendation("Accept (after minor revisions)") == "Minor Revision"
        assert normalize_recommendation("Major revision required") == "Major Revision"
        assert normalize_recommendation("Reject - not suitable") == "Reject"


class TestNormalizeReport:
    def test_canonical_passthrough(self):
        rpt = {
            "revision": 1,
            "recommendation": "Accept",
            "comments_to_author": "Good paper.",
            "scores": {"clarity": "high"},
        }
        out = _normalize_report(rpt)
        assert out["revision"] == 1
        assert out["recommendation"] == "Accept"
        assert out["recommendation_raw"] == "Accept"
        assert out["comments_to_author"] == "Good paper."
        assert out["available"] is True
        assert out["word_count"] == 2

    def test_truncates_long_strings(self):
        rpt = {"comments_to_author": "x" * 30000}
        out = _normalize_report(rpt)
        assert len(out["comments_to_author"]) == 20000

    def test_word_count_computed(self):
        rpt = {"comments_to_author": "one two three four five"}
        out = _normalize_report(rpt)
        assert out["word_count"] == 5

    def test_word_count_preserved_if_set(self):
        rpt = {"comments_to_author": "one two three", "word_count": 999}
        out = _normalize_report(rpt)
        assert out["word_count"] == 999

    def test_recommendation_raw_preserved_with_canonical_overlay(self):
        rpt = {"recommendation": "publish as is"}
        out = _normalize_report(rpt)
        assert out["recommendation_raw"] == "publish as is"
        assert out["recommendation"] == "Accept"

    def test_available_false_for_empty_report(self):
        out = _normalize_report({})
        assert out["available"] is False
        assert out["word_count"] == 0

    def test_extra_fields_moved_to_platform_specific(self):
        rpt = {"comments_to_author": "Hi", "popup_html_path": "/tmp/x.html"}
        out = _normalize_report(rpt)
        assert "popup_html_path" not in out
        assert out["platform_specific"]["popup_html_path"] == "/tmp/x.html"

    def test_idempotent(self):
        rpt = {
            "revision": 0,
            "recommendation": "Reject",
            "comments_to_author": "No good.",
            "scores": {},
        }
        first = _normalize_report(rpt)
        second = _normalize_report(first)
        assert first == second


class TestFinalizeRefereeReports:
    def test_single_report_wrapped_into_list(self):
        ref = {"name": "R1", "report": {"comments_to_author": "Looks fine."}}
        _finalize_referee_reports(ref)
        assert isinstance(ref["reports"], list)
        assert len(ref["reports"]) == 1
        assert ref["report"] is ref["reports"][-1]

    def test_reports_list_normalized_and_sorted(self):
        ref = {
            "name": "R1",
            "reports": [
                {"revision": 1, "comments_to_author": "R1 comments"},
                {"revision": 0, "comments_to_author": "R0 comments"},
            ],
        }
        _finalize_referee_reports(ref)
        # Ascending by revision
        assert ref["reports"][0]["revision"] == 0
        assert ref["reports"][1]["revision"] == 1
        # Singular mirrors the latest (highest revision)
        assert ref["report"]["comments_to_author"] == "R1 comments"

    def test_empty_referee(self):
        ref = {"name": "R1"}
        _finalize_referee_reports(ref)
        assert ref["reports"] == []
        assert "report" not in ref

    def test_singular_and_list_coexist(self):
        ref = {
            "name": "R1",
            "report": {"comments_to_author": "Latest comment"},
            "reports": [{"comments_to_author": "Older comment", "revision": 0}],
        }
        _finalize_referee_reports(ref)
        # Both should be present (since they have different content)
        texts = [r["comments_to_author"] for r in ref["reports"]]
        assert "Older comment" in texts
        assert "Latest comment" in texts


class TestNormalizeRefereeIntegration:
    def test_singular_report_canonicalized(self):
        ref = {
            "name": "R1",
            "report": {"comments_to_author": "Solid contribution.", "recommendation": "Accept"},
        }
        _normalize_referee(ref, "SIAM")
        # Reports list created from singular
        assert len(ref["reports"]) == 1
        assert ref["report"]["recommendation"] == "Accept"
        assert ref["report"]["available"] is True

    def test_top_level_recommendation_surfaced(self):
        ref = {
            "name": "R1",
            "report": {"comments_to_author": "Good.", "recommendation": "Minor Revision"},
        }
        _normalize_referee(ref, "SIAM")
        assert ref["recommendation"] == "Minor Revision"
