"""Tests for NACO (EditFlow/MSP) detail-page extraction scaffold.

These tests use synthetic HTML fixtures that approximate the EditFlow
DOM structure. After the first live capture pass, we'll add real
fixture files (in production/downloads/naco/debug/*.html) and refine
the parser to match the actual selectors.
"""

from bs4 import BeautifulSoup
from extractors.naco_extractor import NACOExtractor


def _make_extractor():
    """Build a NACO extractor without running its setup."""
    ext = NACOExtractor.__new__(NACOExtractor)
    return ext


# ── Fixtures ──────────────────────────────────────────────────────────────────


REFEREE_TABLE_HTML = """
<html><body>
<h2>Refereeing</h2>
<table>
  <thead>
    <tr><th>Reviewer</th><th>Status</th><th>Dates</th><th>Report</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>Alice Smith alice@example.com</td>
      <td>Report Submitted</td>
      <td>2026-01-15 2026-02-01 2026-03-10</td>
      <td><a href="/report.php?rid=123">View Report</a></td>
    </tr>
    <tr>
      <td>Bob Jones bob.jones@univ.edu</td>
      <td>Agreed</td>
      <td>2026-02-15 2026-04-15</td>
      <td>—</td>
    </tr>
    <tr>
      <td>Carol White carol@institute.org</td>
      <td>Declined</td>
      <td>2026-03-01</td>
      <td>—</td>
    </tr>
  </tbody>
</table>
</body></html>
"""


INLINE_REPORT_HTML = """
<html><body>
<h3>Reviewer 1: alice@example.com</h3>
<section>
<p>Recommendation: Minor Revision</p>
<p>Comments to Author:</p>
<p>The paper is well written and presents a meaningful contribution.
A few minor issues: typo in equation 3, please clarify section 4.2.</p>
</section>
</body></html>
"""


NO_REFEREE_TABLE_HTML = """
<html><body>
<h2>Article details</h2>
<p>Title: A test article</p>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Submitted</td><td>2026-01-01</td></tr>
</table>
</body></html>
"""


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestExtractRefereesFromDetailPage:
    def test_finds_referees_in_table(self):
        ext = _make_extractor()
        soup = BeautifulSoup(REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        assert len(refs) == 3

    def test_referee_emails_extracted(self):
        ext = _make_extractor()
        soup = BeautifulSoup(REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        emails = {r["email"] for r in refs}
        assert "alice@example.com" in emails
        assert "bob.jones@univ.edu" in emails
        assert "carol@institute.org" in emails

    def test_status_mapped(self):
        ext = _make_extractor()
        soup = BeautifulSoup(REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        by_email = {r["email"]: r for r in refs}
        assert by_email["alice@example.com"]["status"] == "Report Submitted"
        assert by_email["bob.jones@univ.edu"]["status"] == "Agreed"
        assert by_email["carol@institute.org"]["status"] == "Declined"

    def test_dates_extracted(self):
        ext = _make_extractor()
        soup = BeautifulSoup(REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        by_email = {r["email"]: r for r in refs}
        assert by_email["alice@example.com"].get("contacted_date") == "2026-01-15"
        assert by_email["alice@example.com"].get("received_date") == "2026-03-10"

    def test_report_url_captured(self):
        ext = _make_extractor()
        soup = BeautifulSoup(REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        by_email = {r["email"]: r for r in refs}
        assert by_email["alice@example.com"].get("report_url") == "/report.php?rid=123"
        assert "report_url" not in by_email["bob.jones@univ.edu"]

    def test_no_referee_table_returns_empty(self):
        ext = _make_extractor()
        soup = BeautifulSoup(NO_REFEREE_TABLE_HTML, "html.parser")
        refs = ext._extract_referees_from_detail_page(soup)
        assert refs == []


class TestParseNacoStatus:
    def test_submitted(self):
        assert (
            NACOExtractor._parse_naco_status("Report submitted on 2026-01-01") == "Report Submitted"
        )
        assert NACOExtractor._parse_naco_status("Review complete") == "Report Submitted"

    def test_agreed(self):
        assert NACOExtractor._parse_naco_status("Agreed to review") == "Agreed"
        assert NACOExtractor._parse_naco_status("Accepted") == "Agreed"

    def test_declined(self):
        assert NACOExtractor._parse_naco_status("Declined") == "Declined"
        assert NACOExtractor._parse_naco_status("rejected") == "Declined"

    def test_invited(self):
        assert NACOExtractor._parse_naco_status("Awaiting response") == "Invited"
        assert NACOExtractor._parse_naco_status("invited") == "Invited"

    def test_unknown(self):
        assert NACOExtractor._parse_naco_status("") == "Unknown"
        assert NACOExtractor._parse_naco_status("???") == "Unknown"


class TestExtractRefereeReportInline:
    def test_finds_inline_report(self):
        ext = _make_extractor()
        soup = BeautifulSoup(INLINE_REPORT_HTML, "html.parser")
        report = ext._extract_referee_report_inline(soup, "alice@example.com")
        assert report is not None
        assert "Minor Revision" in report["recommendation"]
        assert "well written" in report["comments_to_author"]
        assert report["source"] == "editflow_inline"
        assert report["available"] is True

    def test_no_anchor_returns_none(self):
        ext = _make_extractor()
        soup = BeautifulSoup(INLINE_REPORT_HTML, "html.parser")
        report = ext._extract_referee_report_inline(soup, "nobody@example.com")
        assert report is None

    def test_empty_email_returns_none(self):
        ext = _make_extractor()
        soup = BeautifulSoup(INLINE_REPORT_HTML, "html.parser")
        report = ext._extract_referee_report_inline(soup, "")
        assert report is None


class TestEnrichManuscriptFromDetailPage:
    def test_no_driver_skipped(self):
        # When driver is None, the function returns early without raising
        ext = _make_extractor()
        ms = {"manuscript_id": "NACO-1", "referees": []}
        # Will fail at navigate; should not raise
        result = ext._enrich_manuscript_from_detail_page(ms)
        assert result is None
