import asyncio
from pathlib import Path


class _StubPage:
    def __init__(self, html: str):
        self._html = html

    async def content(self) -> str:
        return self._html


def _read_fixture(name: str) -> str:
    return (Path("tests/fixtures") / name).read_text()


def test_sicon_details_parsing_via_adapter(monkeypatch):
    from src.ecc.adapters.journals.sicon import SICONAdapter

    a = SICONAdapter(headless=True)
    html = _read_fixture("siam_details_simple.html")
    a.page = _StubPage(html)
    ms = asyncio.run(a.extract_manuscript_details("SICON-2025-0123"))
    assert ms.external_id == "SICON-2025-0123"
    assert len(ms.authors) == 2
    assert any(f.filename.endswith(".pdf") for f in ms.files)


def test_jota_details_parsing_via_adapter(monkeypatch):
    from src.ecc.adapters.journals.jota import JOTAAdapter

    a = JOTAAdapter(headless=True)
    html = _read_fixture("springer_details_simple.html")
    a.page = _StubPage(html)
    ms = asyncio.run(a.extract_manuscript_details("JOTA-2025-1111"))
    assert ms.external_id == "JOTA-2025-1111"
    assert len(ms.authors) >= 2
    assert any(f.filename.endswith(".pdf") for f in ms.files)
