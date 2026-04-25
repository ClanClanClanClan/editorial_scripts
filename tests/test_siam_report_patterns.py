"""Tests for SIAM report comment-header parsing patterns.

The SIAM `_extract_referee_reports` method matches review comment headers
against several regex variants because SICON and SIFIN use different
formats. We test the regex set in isolation here.
"""

import re

COMMENT_HEADER_PATTERNS = [
    re.compile(r"(.+?)'s\s+Comments\s+\(Referee\s+#(\d+)\)\s*-\s*(.+)", re.IGNORECASE),
    re.compile(r"(.+?)'s\s+Comments\s*-\s*(.+)", re.IGNORECASE),
    re.compile(
        r"Comments\s+from\s+([^()-]+?)(?:\s*\(Referee\s+#(\d+)\))?(?:\s*-\s*(.+))?$",
        re.IGNORECASE,
    ),
]


def _match(text: str):
    for pat in COMMENT_HEADER_PATTERNS:
        m = pat.match(text)
        if m:
            return m
    return None


class TestNamedRefereeHeader:
    def test_full_format_with_referee_number(self):
        m = _match("Nicolás Hernández's Comments (Referee #2) - 2026-02-09")
        assert m is not None
        groups = m.groups()
        assert groups[0] == "Nicolás Hernández"
        assert groups[1] == "2"
        assert groups[2] == "2026-02-09"

    def test_format_without_referee_number(self):
        m = _match("Alice Smith's Comments - 2026-04-15")
        assert m is not None
        groups = m.groups()
        assert groups[0] == "Alice Smith"
        # Second pattern returns 2 groups
        assert groups[-1] == "2026-04-15"

    def test_lowercase_apostrophe_skipped(self):
        # The pattern is case-insensitive but the apostrophe must be ASCII.
        m = _match("alice smith's comments (referee #1) - 2026-04-15")
        assert m is not None


class TestCommentsFromHeader:
    def test_simple_format(self):
        m = _match("Comments from Bob Jones")
        assert m is not None
        assert m.group(1).strip() == "Bob Jones"

    def test_with_referee_number(self):
        m = _match("Comments from Bob Jones (Referee #3)")
        assert m is not None
        groups = m.groups()
        assert groups[0].strip() == "Bob Jones"
        # The trailing dash/date is optional
        assert groups[1] == "3"

    def test_with_date(self):
        m = _match("Comments from Bob Jones (Referee #3) - 2026-03-01")
        assert m is not None
        groups = m.groups()
        assert groups[0].strip() == "Bob Jones"
        assert groups[1] == "3"
        assert (groups[2] or "").strip() == "2026-03-01"


class TestNonMatchingText:
    def test_random_text_not_matched(self):
        assert _match("This is not a header") is None

    def test_partial_keyword_not_matched(self):
        assert _match("Comment received from author") is None

    def test_only_comments_word(self):
        assert _match("Comments") is None
