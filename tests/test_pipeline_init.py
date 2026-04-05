"""Tests for pipeline __init__ utilities."""

import pytest
from pipeline import normalize_name, normalize_name_orderless


class TestNormalizeName:
    def test_basic(self):
        assert normalize_name("John Smith") == "john smith"

    def test_accented(self):
        assert normalize_name("José García") == "jose garcia"

    def test_empty(self):
        assert normalize_name("") == ""

    def test_whitespace(self):
        assert normalize_name("  Alice  ") == "alice"


class TestNormalizeNameOrderless:
    def test_reorders_parts(self):
        assert normalize_name_orderless("Smith John") == "john smith"

    def test_same_result_for_reordered(self):
        assert normalize_name_orderless("Emma Hubert") == normalize_name_orderless("Hubert Emma")

    def test_comma_separated(self):
        assert normalize_name_orderless("HUBERT, Emma") == normalize_name_orderless("Emma Hubert")

    def test_all_caps(self):
        assert normalize_name_orderless("JOHN SMITH") == "john smith"

    def test_mixed_case_reorder(self):
        assert normalize_name_orderless("SMITH John") == normalize_name_orderless("John Smith")

    def test_accented_reorder(self):
        assert normalize_name_orderless("García José") == normalize_name_orderless("José García")

    def test_empty(self):
        assert normalize_name_orderless("") == ""

    def test_single_name(self):
        assert normalize_name_orderless("Alice") == "alice"

    def test_multiple_commas(self):
        assert normalize_name_orderless("Smith, J., Jr.") == "j jr smith"

    def test_semicolons_stripped(self):
        assert normalize_name_orderless("Smith; John") == "john smith"

    def test_periods_stripped(self):
        assert normalize_name_orderless("Smith. J.") == "j smith"

    def test_three_part_name(self):
        a = normalize_name_orderless("Jean-Pierre De La Fontaine")
        b = normalize_name_orderless("De La Fontaine Jean-Pierre")
        assert a == b
