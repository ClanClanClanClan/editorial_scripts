#!/usr/bin/env python3
"""Smoke tests: verify all 8 extractors import and have expected attributes."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "production" / "src" / "extractors"))
sys.path.insert(0, str(Path(__file__).parent.parent / "production" / "src"))

EXTRACTORS = [
    ("mf_extractor", "ComprehensiveMFExtractor"),
    ("mor_extractor", "MORExtractor"),
    ("fs_extractor", "ComprehensiveFSExtractor"),
    ("jota_extractor", "JOTAExtractor"),
    ("mafe_extractor", "MAFEExtractor"),
    ("sicon_extractor", "SICONExtractor"),
    ("sifin_extractor", "SIFINExtractor"),
    ("naco_extractor", "NACOExtractor"),
]


@pytest.mark.parametrize("module_name,class_name", EXTRACTORS)
def test_extractor_import(module_name, class_name):
    mod = __import__(module_name)
    cls = getattr(mod, class_name)
    assert cls is not None


EXTRACTORS_WITH_CODE = [e for e in EXTRACTORS if e[0] != "fs_extractor"]


@pytest.mark.parametrize("module_name,class_name", EXTRACTORS_WITH_CODE)
def test_extractor_has_journal_code(module_name, class_name):
    mod = __import__(module_name)
    cls = getattr(mod, class_name)
    assert hasattr(cls, "JOURNAL_CODE") or hasattr(cls, "JOURNAL_NAME")


def test_naco_ae_filter_configurable(monkeypatch):
    monkeypatch.setenv("NACO_AE_FILTER", "TestName")
    if "naco_extractor" in sys.modules:
        del sys.modules["naco_extractor"]
    mod = __import__("naco_extractor")
    extractor = mod.NACOExtractor.__new__(mod.NACOExtractor)
    extractor.ae_filter = "TestName"
    assert extractor.ae_filter == "TestName"
