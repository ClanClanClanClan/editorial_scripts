import os

from src.ecc.adapters.journals.category_selectors import get_category_selector_patterns


def test_category_selector_overrides(monkeypatch):
    # Provide an override for JOTA via env JSON
    overrides = '{"JOTA": ["nav a:has-text("{category}")"]}'
    monkeypatch.setenv("ECC_CATEGORY_SELECTORS", overrides)
    pats = get_category_selector_patterns("JOTA", "Under Review")
    assert any("nav a:has-text(" in p for p in pats)


def test_category_file_config_loaded():
    # MAFE.json includes 'aside a:has-text' pattern
    pats = get_category_selector_patterns("MAFE", "Under Review")
    assert any("aside a:has-text(" in p for p in pats)
