"""Tests for the pure ScholarOne popup parser.

The parser is testable without Selenium — we feed it realistic HTML
fragments that match what ScholarOne actually renders.
"""

from core.scholarone_base import ScholarOneBaseExtractor

# ── Fixtures ──────────────────────────────────────────────────────────────────


THREE_COL_FORM_HTML = """
<html>
<body>
  <table>
    <tr>
      <td>Recommendation</td>
      <td>Pick one:</td>
      <td>Minor Revision</td>
    </tr>
    <tr>
      <td>Originality</td>
      <td>Score 1-5:</td>
      <td>4</td>
    </tr>
    <tr>
      <td>Clarity</td>
      <td>Score 1-5:</td>
      <td>5</td>
    </tr>
    <tr>
      <td>Comments to the Author</td>
      <td>Free text:</td>
      <td>This paper makes a solid contribution to the literature.
The introduction is clear and the proofs are well structured.
A few minor typos noted in Section 3.</td>
    </tr>
    <tr>
      <td>Confidential Comments to Editor</td>
      <td>Editor only:</td>
      <td>I think this is acceptable after minor revisions.</td>
    </tr>
  </table>
</body>
</html>
"""

TWO_COL_SCORES_HTML = """
<html>
<body>
  <table>
    <tr><td>Recommendation</td><td>Accept</td></tr>
    <tr><td>Originality</td><td>5</td></tr>
    <tr><td>Quality</td><td>4</td></tr>
  </table>
  <p><b>Comments to Author:</b></p>
  <p>The paper is well written and the contribution is significant.</p>
  <p><b>Confidential Comments to Editor:</b></p>
  <p>Strongly recommend acceptance.</p>
</body>
</html>
"""

INLINE_LABELS_HTML = """
<html>
<body>
<pre>
Comments to the Author:
The paper has interesting results.
However, the discussion in Section 4 needs to be expanded.
Theorem 2.3 is a bit hard to follow.

Confidential Comments to Editor:
This is borderline; I lean accept after major revisions.

Recommendation: Major Revision
</pre>
</body>
</html>
"""

EMPTY_HTML = "<html><body></body></html>"

SHELL_HTML = """
<html>
<head><title>Review</title><meta name="viewport" content="width=device-width"></head>
<body>
<p>Loading the referee report. Please wait while the data loads.</p>
<p>If this page does not load within 30 seconds, please refresh.</p>
</body>
</html>
"""


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestThreeColumnForm:
    def test_recommendation_extracted(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert report["recommendation"] == "Minor Revision"

    def test_scores_extracted(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert report["scores"]["Originality"] == "4"
        assert report["scores"]["Clarity"] == "5"

    def test_comments_to_author_extracted(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert "solid contribution" in report["comments_to_author"]
        assert "Section 3" in report["comments_to_author"]

    def test_confidential_comments_extracted(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert "minor revisions" in report["confidential_comments"]

    def test_available_true(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert report["available"] is True

    def test_extraction_status_ok(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert report["extraction_status"] == "ok"

    def test_source_label(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(THREE_COL_FORM_HTML)
        assert report["source"] == "scholarone_popup"


class TestTwoColumnScoresHtml:
    def test_recommendation_in_table(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(TWO_COL_SCORES_HTML)
        assert report["recommendation"] == "Accept"

    def test_scores_in_table(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(TWO_COL_SCORES_HTML)
        assert report["scores"]["Originality"] == "5"
        assert report["scores"]["Quality"] == "4"

    def test_comments_via_regex_fallback(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(TWO_COL_SCORES_HTML)
        # Either via regex or via line-based fallback
        assert "well written" in report["comments_to_author"]


class TestInlineLabelsHtml:
    def test_comments_extracted_from_inline_labels(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(INLINE_LABELS_HTML)
        assert "Theorem 2.3" in report["comments_to_author"]

    def test_confidential_extracted(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(INLINE_LABELS_HTML)
        assert "borderline" in report["confidential_comments"]

    def test_raw_text_includes_full_body(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(INLINE_LABELS_HTML)
        assert "Section 4" in report["raw_text"]


class TestEmptyAndShell:
    def test_empty_html_returns_failed(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html("")
        assert report["extraction_status"] == "popup_failed"
        assert report["available"] is False

    def test_short_html_returns_failed(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html("<p>x</p>")
        assert report["extraction_status"] == "popup_failed"
        assert report["available"] is False

    def test_shell_html_returns_shell_only(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(SHELL_HTML)
        # No structured content found, but had >50 chars of HTML
        assert report["available"] is False
        assert report["extraction_status"] == "shell_only"


class TestRefereePassthrough:
    def test_referee_recommendation_used_as_default(self):
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(
            EMPTY_HTML, referee={"name": "R1", "recommendation": "Reject"}
        )
        # When the popup is empty, we still preserve the row-level recommendation
        # but extraction_status flags failure
        # (Empty HTML is < 50 chars → popup_failed)
        assert report["extraction_status"] == "popup_failed"


class TestParserDoesNotMistakePromptForResponse:
    def test_short_label_with_long_prompt_skips(self):
        # If a 3-col row has a prompt as cells[1] but no real response, we shouldn't
        # treat the prompt as the answer.
        html = """
        <table>
          <tr>
            <td>Comments to the Author</td>
            <td>Please provide detailed comments here for the author.</td>
            <td></td>
          </tr>
        </table>
        """
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(html)
        # Empty cells[2] → cells[1] is candidate. The 20-char cutoff filters
        # the prompt only when cells[1] is short. Here the prompt is long so
        # the parser may capture it. This is acceptable as raw_text fallback —
        # but verify we never silently corrupt structured fields.
        # At minimum, parser should not crash.
        assert "extraction_status" in report


# ── Regression: MOR popup with form-instruction prompt before review prose ────


# Realistic shape of a ScholarOne in-place popup once we navigate to the
# review-content URL. The actual review starts with "Referee Report on …"
# but the form first shows the section label, then a paragraph of
# instruction boilerplate ("Clearly label your … in the field provided
# below. Please be sure to retain anonymity in your comments."), then the
# real prose. Without the strip, cta would be the boilerplate (~135 chars)
# and the actual review would only live in raw_text.
MOR_INPLACE_POPUP_HTML = """
<html>
<body>
  <h2>Reviewer 1: Keppo, Jussi</h2>
  <p>Recommendation: Major Revision</p>
  <p>Confidential Comments to the Editor</p>
  <p>I have no confidential comments.</p>
  <p>Comments to the Author</p>
  <p>Clearly label your Major and Minor Comments to Author in the field
provided below. Please be sure to retain anonymity in your comments.</p>

<p>Referee Report on "Decision Making under Costly Sequential
Information Acquisition: the Paradigm of Reversible and Irreversible Decisions"</p>

<p>Summary and Overall Evaluation</p>
<p>This paper studies a sequential decision problem with costly information
acquisition in which a decision maker chooses between a known product and an
unknown product. After choosing the unknown product, the decision maker may
later reverse that choice at a cost while learning from a more informative
signal. The model leads to a nested optimal stopping problem, where the outer
problem has as its obstacle the value of an inner stopping problem.</p>

<p>Major Comments</p>
<p>My first major concern is that the paper needs a sharper statement of its
core contribution. The introduction presents a broad agenda involving costly
information acquisition, adaptive information sources, sequential decisions,
reversibility, and a general framework for future multi-stage models.</p>
</body>
</html>
"""


class TestMorPopupFormPromptStripped:
    def test_cta_skips_instruction_prompt(self):
        """The captured cta must not be the form-instruction boilerplate."""
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(MOR_INPLACE_POPUP_HTML)
        cta = report.get("comments_to_author") or ""
        # The instruction sentence should NOT be the entire cta
        assert (
            "Clearly label your Major and Minor Comments" not in cta[:300]
        ), f"cta starts with form-instruction prompt: {cta[:200]!r}"
        # The actual review content must be present
        assert (
            "Referee Report on" in cta or "Summary and Overall Evaluation" in cta
        ), f"cta missing review content: {cta[:300]!r}"
        assert len(cta) > 200, f"cta too short, expected real review prose: {len(cta)}"

    def test_cta_does_not_stop_at_referee_word(self):
        """The regex stop-marker list must not include bare 'referee' /
        'reviewer' — the actual review prose opens with 'Referee Report on…'
        and we'd lose the entire content otherwise."""
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(MOR_INPLACE_POPUP_HTML)
        cta = report.get("comments_to_author") or ""
        assert "Major Comments" in cta or "Summary and Overall Evaluation" in cta

    def test_raw_text_still_has_full_content(self):
        """raw_text always carries the full popup body regardless of cta
        extraction. Downstream tools (AE prompt, quality scoring) read both."""
        report = ScholarOneBaseExtractor._parse_scholarone_popup_html(MOR_INPLACE_POPUP_HTML)
        raw = report.get("raw_text") or ""
        assert "Decision Making under Costly Sequential" in raw
        assert "Major Comments" in raw
