"""Tests for Wiley ScienceConnect extractor."""

import pytest
from core.wiley_base import WileyBaseExtractor


class TestParseWileyDate:
    def test_standard_format(self):
        assert WileyBaseExtractor._parse_wiley_date("Mar 29, 2026") == "2026-03-29"

    def test_full_month(self):
        assert WileyBaseExtractor._parse_wiley_date("March 29, 2026") == "2026-03-29"

    def test_iso_format_passthrough(self):
        assert WileyBaseExtractor._parse_wiley_date("2026-03-29") == "2026-03-29"

    def test_empty(self):
        assert WileyBaseExtractor._parse_wiley_date("") == ""

    def test_none(self):
        assert WileyBaseExtractor._parse_wiley_date(None) == ""

    def test_whitespace(self):
        assert WileyBaseExtractor._parse_wiley_date("  Apr 03, 2026  ") == "2026-04-03"

    def test_jan(self):
        assert WileyBaseExtractor._parse_wiley_date("Jan 01, 2026") == "2026-01-01"

    def test_dec(self):
        assert WileyBaseExtractor._parse_wiley_date("Dec 31, 2025") == "2025-12-31"

    def test_invalid(self):
        assert WileyBaseExtractor._parse_wiley_date("not a date") == ""

    def test_partial(self):
        assert WileyBaseExtractor._parse_wiley_date("Mar 2026") == ""


class TestMapStatus:
    def test_accepted(self):
        assert WileyBaseExtractor._map_status("Invitation accepted") == "Agreed"

    def test_pending(self):
        assert WileyBaseExtractor._map_status("Pending response") == "Invited"

    def test_declined(self):
        assert WileyBaseExtractor._map_status("Invitation declined") == "Declined"

    def test_expired(self):
        assert WileyBaseExtractor._map_status("Invitation expired") == "No Response"

    def test_revoked(self):
        assert WileyBaseExtractor._map_status("Invitation revoked") == "Terminated"

    def test_submitted(self):
        assert WileyBaseExtractor._map_status("Report submitted") == "Report Submitted"

    def test_unknown_passthrough(self):
        assert WileyBaseExtractor._map_status("Some New Status") == "Some New Status"

    def test_case_insensitive(self):
        assert WileyBaseExtractor._map_status("INVITATION ACCEPTED") == "Agreed"

    def test_empty(self):
        assert WileyBaseExtractor._map_status("") == ""


class TestExtractRefereeDatesParsing:
    def test_invited_date_regex(self):
        import re

        pattern = re.compile(
            r"^(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*(.+)", re.IGNORECASE
        )
        m = pattern.match("Invited:Mar 29, 2026")
        assert m is not None
        assert m.group(1) == "Invited"
        assert m.group(2) == "Mar 29, 2026"

    def test_accepted_date_regex(self):
        import re

        pattern = re.compile(
            r"^(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*(.+)", re.IGNORECASE
        )
        m = pattern.match("Accepted:Apr 03, 2026")
        assert m is not None
        assert m.group(1) == "Accepted"

    def test_expired_date_regex(self):
        import re

        pattern = re.compile(
            r"^(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*(.+)", re.IGNORECASE
        )
        m = pattern.match("Expired:Mar 25, 2026")
        assert m is not None

    def test_non_date_text_no_match(self):
        import re

        pattern = re.compile(
            r"^(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*(.+)", re.IGNORECASE
        )
        assert pattern.match("Time left to submit:2 months") is None
        assert pattern.match("Keywords:none") is None


class TestRefereeSourcParsing:
    def test_manually_invited(self):
        tid = "reviewerInvitedManually-reviewer-name-b244c831"
        source = "unknown"
        for prefix in ("reviewerInvitedManually-", "reviewerSuggestions-", "reviewerSearch-"):
            if prefix in tid:
                source = prefix.rstrip("-").replace("reviewer", "").lower()
                break
        assert source == "invitedmanually"

    def test_suggestions(self):
        tid = "reviewerSuggestions-reviewer-name-7bd18ede"
        source = "unknown"
        for prefix in ("reviewerInvitedManually-", "reviewerSuggestions-", "reviewerSearch-"):
            if prefix in tid:
                source = prefix.rstrip("-").replace("reviewer", "").lower()
                break
        assert source == "suggestions"

    def test_search(self):
        tid = "reviewerSearch-reviewer-name-912e1003"
        source = "unknown"
        for prefix in ("reviewerInvitedManually-", "reviewerSuggestions-", "reviewerSearch-"):
            if prefix in tid:
                source = prefix.rstrip("-").replace("reviewer", "").lower()
                break
        assert source == "search"


class TestClassConfig:
    def test_mf_wiley_config(self):
        from extractors.mf_wiley_extractor import MFWileyExtractor

        assert MFWileyExtractor.JOURNAL_CODE == "MF_WILEY"
        assert MFWileyExtractor.JOURNAL_NAME == "Mathematical Finance"
        assert MFWileyExtractor.LOGIN_URL == "https://wiley.scienceconnect.io/login"
        assert MFWileyExtractor.DASHBOARD_URL == "https://review.wiley.com"

    def test_platform_mapping(self):
        from core.output_schema import JOURNAL_NAME_MAP, PLATFORM_MAP, REFEREE_DATE_MAPPINGS

        assert PLATFORM_MAP["MF_WILEY"] == "Wiley ScienceConnect"
        assert JOURNAL_NAME_MAP["MF_WILEY"] == "Mathematical Finance"
        assert "Wiley ScienceConnect" in REFEREE_DATE_MAPPINGS
        mapping = REFEREE_DATE_MAPPINGS["Wiley ScienceConnect"]
        assert "invited" in mapping
        assert "agreed" in mapping
        assert "due" in mapping
        assert "returned" in mapping

    def test_journals_list_includes_mf_wiley(self):
        from pipeline import JOURNALS

        assert "mf_wiley" in JOURNALS


class TestOutputSchemaDateFormats:
    def test_wiley_date_in_normalize_date(self):
        from core.output_schema import normalize_date

        assert normalize_date("Mar 29, 2026") == "2026-03-29"
        assert normalize_date("Apr 03, 2026") == "2026-04-03"
        assert normalize_date("Feb 25, 2026") == "2026-02-25"


class TestCrossJournalReportIncludes:
    def test_mf_wiley_in_cross_journal(self):
        from reporting.cross_journal_report import JOURNALS

        assert "mf_wiley" in JOURNALS
