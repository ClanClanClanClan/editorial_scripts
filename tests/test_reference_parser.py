"""Tests for reference list parsing from PDFs."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from pipeline.reference_parser import (
    _extract_author_names,
    _find_references_section,
    _parse_reference_entry,
    extract_references,
)


class TestFindReferencesSection:
    def test_extracts_text_after_references_heading(self):
        text = (
            "This is the main body.\n"
            "\n"
            "References\n"
            "\n"
            "[1] Smith, A. (2023). A great paper. J. Math. 1, 1-10.\n"
            "[2] Jones, B. (2024). Another paper. Math. Finance 2, 5-15.\n"
        )
        section = _find_references_section(text)
        assert section is not None
        assert "Smith" in section
        assert "Jones" in section

    def test_bibliography_heading(self):
        text = (
            "Main text here.\n"
            "\n"
            "Bibliography\n"
            "\n"
            "1. Author, X. (2020). Some title. Pub.\n"
        )
        section = _find_references_section(text)
        assert section is not None
        assert "Author" in section

    def test_returns_none_without_section(self):
        text = "This paper has no references section at all."
        assert _find_references_section(text) is None


class TestParseReferenceEntry:
    def test_extracts_author_and_year(self):
        entry = "Smith, A. (2023). Title of the paper about stochastic control. J. Math. 1, 1-10."
        result = _parse_reference_entry(entry)
        assert result is not None
        assert result["year"] == 2023
        assert len(result["authors"]) >= 1

    def test_too_short_returns_none(self):
        assert _parse_reference_entry("Short") is None


class TestExtractAuthorNames:
    def test_and_format(self):
        entry = "Smith, A. and Jones, B. (2023). A paper."
        names = _extract_author_names(entry)
        assert len(names) >= 2

    def test_comma_format(self):
        entry = "Smith A, Jones B, 2021. Some paper title here."
        names = _extract_author_names(entry)
        assert len(names) >= 1


class TestExtractReferences:
    def test_returns_empty_for_no_references_section(self):
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Just a body with no references heading."
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            from importlib import reload

            import pipeline.reference_parser as rp

            reload(rp)
            result = rp.extract_references("/fake/path.pdf")
        assert result == []
