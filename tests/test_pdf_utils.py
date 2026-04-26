"""Tests for the shared PDF text + report-attachment helpers."""

import sys
from pathlib import Path

import pytest

PROD_SRC = Path(__file__).resolve().parent.parent / "production" / "src"
if str(PROD_SRC) not in sys.path:
    sys.path.insert(0, str(PROD_SRC))

from core.pdf_utils import (  # noqa: E402
    derive_recommendation_from_text,
    extract_pdf_text,
    populate_report_from_pdf,
)

# ── derive_recommendation_from_text ───────────────────────────────────


class TestDeriveRecommendation:
    def test_reject(self):
        assert derive_recommendation_from_text("I recommend reject of this paper.") == "Reject"

    def test_major_revision(self):
        assert (
            derive_recommendation_from_text(
                "The paper has merit but requires Major Revisions before acceptance."
            )
            == "Major Revision"
        )

    def test_minor_revision(self):
        assert (
            derive_recommendation_from_text(
                "I recommend acceptance subject to minor revisions of the proofs."
            )
            == "Minor Revision"
        )

    def test_accept_with_minor(self):
        assert derive_recommendation_from_text("Accept with minor revisions") == "Minor Revision"

    def test_accept(self):
        assert (
            derive_recommendation_from_text(
                "I recommend acceptance of this manuscript without changes."
            )
            == "Accept"
        )

    def test_no_signal(self):
        assert derive_recommendation_from_text("Lorem ipsum dolor sit amet.") is None

    def test_empty(self):
        assert derive_recommendation_from_text("") is None
        assert derive_recommendation_from_text(None) is None


# ── extract_pdf_text ──────────────────────────────────────────────────


class TestExtractPdfText:
    def test_missing_file(self, tmp_path):
        assert extract_pdf_text(tmp_path / "nope.pdf") == ""

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.pdf"
        f.write_bytes(b"")
        assert extract_pdf_text(f) == ""

    def test_nonpdf_returns_empty(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("not a pdf")
        # Both pdfplumber and PyPDF2 should fail and return ""
        assert extract_pdf_text(f) == ""


# ── populate_report_from_pdf ──────────────────────────────────────────


def _make_min_pdf(path: Path, text: str) -> None:
    """Build a minimal one-page PDF using reportlab if available, else
    skip the test. We use an external lib only here to avoid baking a
    binary fixture into the repo."""
    try:
        from reportlab.pdfgen import canvas  # type: ignore
    except ImportError:
        pytest.skip("reportlab not installed")

    c = canvas.Canvas(str(path))
    # Wrap to multiple lines so PyPDF2 has structure
    y = 750
    for line in text.split("\n"):
        c.drawString(72, y, line)
        y -= 14
        if y < 50:
            c.showPage()
            y = 750
    c.save()


class TestPopulateReport:
    def test_empty_report_gets_text(self, tmp_path):
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "I recommend Major Revisions.\nThe proofs need work.")
        report: dict = {}
        ok = populate_report_from_pdf(report, pdf, attachment_url="http://x/a.pdf")
        assert ok is True
        assert report["raw_text"]
        assert report["comments_to_author"]
        assert report["recommendation"] == "Major Revision"
        assert report["available"] is True
        assert report["extraction_status"] == "ok"
        assert report["word_count"] > 0
        assert any(a.get("url") == "http://x/a.pdf" for a in report["attachments"])

    def test_keeps_existing_recommendation(self, tmp_path):
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "I recommend Reject.")
        report = {"recommendation": "Accept"}
        populate_report_from_pdf(report, pdf)
        # Should NOT overwrite existing recommendation
        assert report["recommendation"] == "Accept"

    def test_keeps_longer_existing_raw_text(self, tmp_path):
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "Short.")
        report = {"raw_text": "x" * 5000}
        populate_report_from_pdf(report, pdf)
        # Existing raw_text was longer, should be kept
        assert report["raw_text"] == "x" * 5000

    def test_overwrite_replaces(self, tmp_path):
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "New PDF content here.\nSecond line.")
        report = {"raw_text": "x" * 5000, "comments_to_author": "old"}
        populate_report_from_pdf(report, pdf, overwrite=True)
        assert "New PDF content" in (report["raw_text"] or "")
        assert "New PDF content" in (report["comments_to_author"] or "")

    def test_missing_file_returns_false(self, tmp_path):
        report: dict = {}
        ok = populate_report_from_pdf(report, tmp_path / "nope.pdf")
        assert ok is False
        # Attachment metadata still recorded with the bad path so we know
        # something was referenced
        assert report.get("attachments") is not None

    def test_attachments_dedup_by_path(self, tmp_path):
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "Some content.")
        report: dict = {}
        populate_report_from_pdf(report, pdf, attachment_url="http://a")
        populate_report_from_pdf(report, pdf, attachment_url="http://a")
        # Two calls, same path → one entry
        assert len(report["attachments"]) == 1

    def test_stub_pointer_replaced_by_pdf_text(self, tmp_path):
        # The reviewer wrote "Please see the attached report." inline AND
        # uploaded a PDF. The PDF content should win.
        pdf = tmp_path / "review.pdf"
        long_pdf_text = (
            "This is the actual review content with substantive feedback "
            "about the manuscript spanning multiple paragraphs."
        )
        _make_min_pdf(pdf, long_pdf_text)
        report = {"comments_to_author": "Please see the attached report."}
        populate_report_from_pdf(report, pdf)
        assert "actual review content" in report["comments_to_author"]
        # And the original stub is gone
        assert report["comments_to_author"] != "Please see the attached report."

    def test_pdf_replaces_when_3x_longer(self, tmp_path):
        # Even without a stub phrase, if existing cta is materially shorter
        # than the PDF text, the PDF wins. (For empty/short inline forms
        # paired with substantive PDF reports.)
        pdf = tmp_path / "review.pdf"
        long_text = "Detailed review feedback. " * 30  # ~720 chars
        _make_min_pdf(pdf, long_text)
        report = {"comments_to_author": "OK"}  # 2 chars, <<3x of PDF
        populate_report_from_pdf(report, pdf)
        assert "Detailed review feedback" in report["comments_to_author"]

    def test_pdf_does_not_replace_substantive_inline(self, tmp_path):
        # A substantive existing cta should NOT be replaced by a similarly
        # sized or shorter PDF.
        pdf = tmp_path / "review.pdf"
        _make_min_pdf(pdf, "Short PDF.")
        long_inline = "Long substantive inline review. " * 20  # ~640 chars
        report = {"comments_to_author": long_inline}
        populate_report_from_pdf(report, pdf)
        # PDF was much shorter — keep the inline cta
        assert "Long substantive inline review" in report["comments_to_author"]
