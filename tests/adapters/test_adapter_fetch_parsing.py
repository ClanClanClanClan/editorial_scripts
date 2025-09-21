import asyncio
from pathlib import Path


class _StubPage:
    def __init__(self, html: str):
        self._html = html

    async def content(self) -> str:
        return self._html


async def _mf_parse_with_stub(html: str):
    from src.ecc.adapters.journals.mf import MFAdapter

    a = MFAdapter(headless=True)
    a.page = _StubPage(html)
    return await a._parse_manuscript_list()


async def _mor_parse_with_stub(html: str):
    from src.ecc.adapters.journals.mor import MORAdapter

    a = MORAdapter(headless=True)
    a.page = _StubPage(html)
    return await a._parse_manuscript_list()


def _read_fixture(name: str) -> str:
    return (Path("tests/fixtures") / name).read_text()


def test_mf_mor_adapter_parsing_from_fixture():
    html = _read_fixture("scholarone_list_simple.html")
    mf_items = asyncio.run(_mf_parse_with_stub(html))
    mor_items = asyncio.run(_mor_parse_with_stub(html))
    assert any(i.external_id == "MAFI-2025-5678" for i in mf_items)
    assert any(i.external_id == "MOR-2025-1234" for i in mor_items)


def test_siam_springer_adapter_fetch_with_stub(monkeypatch):
    # SICON (SIAM)
    from src.ecc.adapters.journals.sicon import SICONAdapter

    a = SICONAdapter(headless=True)
    html = _read_fixture("siam_list_simple.html")
    a.page = _StubPage(html)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(a, "navigate_with_retry", _noop)
    items = asyncio.run(a.fetch_manuscripts(["Under Review"]))
    assert any(i.external_id == "SICON-2025-0123" for i in items)

    # JOTA (Springer)
    from src.ecc.adapters.journals.jota import JOTAAdapter

    b = JOTAAdapter(headless=True)
    html2 = _read_fixture("springer_list_simple.html")
    b.page = _StubPage(html2)
    monkeypatch.setattr(b, "navigate_with_retry", _noop)
    items2 = asyncio.run(b.fetch_manuscripts(["Under Review"]))
    assert any(i.external_id == "JOTA-2025-1111" for i in items2)
