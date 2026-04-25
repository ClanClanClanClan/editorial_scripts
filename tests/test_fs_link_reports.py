"""Tests for FS extractor's _link_referee_reports_canonical method.

This is the helper that takes manuscript['referee_reports'] (the list of PDF
attachment metadata + analysis) and links each entry to the matching referee's
canonical referee.reports[] list.
"""

from unittest.mock import patch

from extractors.fs_extractor import ComprehensiveFSExtractor


def _make_extractor():
    """Create an FS extractor instance without running its full init chain."""
    ext = ComprehensiveFSExtractor.__new__(ComprehensiveFSExtractor)
    return ext


class TestLinkRefereeReportsCanonical:
    def test_match_by_full_name(self):
        ext = _make_extractor()
        manuscript = {
            "referees": [{"name": "Alice Smith", "report": {"available": False}}],
            "referee_reports": [
                {
                    "filename": "review.pdf",
                    "path": "/nonexistent/review.pdf",
                    "referee": "Alice Smith",
                    "analysis": {
                        "recommendation": "Minor Revision",
                        "scores": {"originality": 4},
                        "text_preview": "Solid paper. A few minor issues to fix.",
                    },
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        ref = manuscript["referees"][0]
        assert "reports" in ref
        assert len(ref["reports"]) == 1
        rpt = ref["reports"][0]
        assert rpt["recommendation"] == "Minor Revision"
        assert rpt["scores"]["originality"] == 4
        assert "Solid paper" in rpt["comments_to_author"]
        assert rpt["source"] == "fs_pdf"
        assert rpt["available"] is True

    def test_case_insensitive_match(self):
        ext = _make_extractor()
        manuscript = {
            "referees": [{"name": "Bob Jones"}],
            "referee_reports": [
                {
                    "filename": "review.pdf",
                    "path": "",
                    "referee": "BOB JONES",
                    "analysis": {"recommendation": "Reject", "text_preview": "No."},
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        assert len(manuscript["referees"][0]["reports"]) == 1

    def test_partial_name_match_via_parts(self):
        ext = _make_extractor()
        # "Smith Alice" (reversed order) should still match "Alice Smith"
        manuscript = {
            "referees": [{"name": "Alice Smith"}],
            "referee_reports": [
                {
                    "filename": "r.pdf",
                    "path": "",
                    "referee": "Smith Alice",
                    "analysis": {"recommendation": "Accept", "text_preview": "Great."},
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        assert len(manuscript["referees"][0].get("reports", [])) == 1

    def test_unknown_referee_not_linked(self):
        ext = _make_extractor()
        manuscript = {
            "referees": [{"name": "Alice Smith"}],
            "referee_reports": [
                {
                    "filename": "r.pdf",
                    "path": "",
                    "referee": "Unknown",
                    "analysis": {"recommendation": "Reject"},
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        assert manuscript["referees"][0].get("reports", []) == []

    def test_no_match_skipped(self):
        ext = _make_extractor()
        manuscript = {
            "referees": [{"name": "Alice Smith"}],
            "referee_reports": [
                {
                    "filename": "r.pdf",
                    "path": "",
                    "referee": "Charlie Brown",
                    "analysis": {"recommendation": "Reject"},
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        assert manuscript["referees"][0].get("reports", []) == []

    def test_singular_report_mirror_set(self):
        ext = _make_extractor()
        manuscript = {
            "referees": [{"name": "Alice Smith"}],
            "referee_reports": [
                {
                    "filename": "r.pdf",
                    "path": "",
                    "referee": "Alice Smith",
                    "analysis": {
                        "recommendation": "Accept",
                        "text_preview": "Excellent work.",
                    },
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        ref = manuscript["referees"][0]
        assert ref.get("report") is not None
        assert "Excellent" in ref["report"]["comments_to_author"]

    def test_duplicate_path_not_added_twice(self):
        ext = _make_extractor()
        # Pre-populate the referee's reports with an entry pointing to /tmp/x.pdf
        manuscript = {
            "referees": [
                {
                    "name": "Alice Smith",
                    "reports": [
                        {
                            "comments_to_author": "old",
                            "attachments": [{"local_path": "/tmp/x.pdf"}],
                        }
                    ],
                }
            ],
            "referee_reports": [
                {
                    "filename": "r.pdf",
                    "path": "/tmp/x.pdf",
                    "referee": "Alice Smith",
                    "analysis": {"recommendation": "Accept", "text_preview": "new"},
                }
            ],
        }
        with patch.object(ext, "extract_text_from_report_pdf", return_value=""):
            ext._link_referee_reports_canonical(manuscript)
        # Still only 1 entry — the duplicate is detected by attachment.local_path
        assert len(manuscript["referees"][0]["reports"]) == 1

    def test_no_referee_reports_noop(self):
        ext = _make_extractor()
        manuscript = {"referees": [{"name": "Alice"}], "referee_reports": []}
        ext._link_referee_reports_canonical(manuscript)
        assert manuscript["referees"][0].get("reports", []) == []
