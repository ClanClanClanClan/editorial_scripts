import pytest
from core.output_schema import (
    CANONICAL_AUTHOR_FIELDS,
    CANONICAL_MANUSCRIPT_FIELDS,
    CANONICAL_REFEREE_FIELDS,
    _collect_platform_specific,
    _normalize_author,
    _normalize_author_corresponding,
    _normalize_referee,
    _resolve_nested_field,
    normalize_date,
    normalize_keywords,
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
