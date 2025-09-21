from pathlib import Path

from src.platforms.springer_parsers import parse_details_html, parse_list_html


def _read_fixture(name: str) -> str:
    return (Path("tests/fixtures") / name).read_text()


def test_springer_list_parsing():
    html = _read_fixture("springer_list_simple.html")
    items = parse_list_html(html, r"JOTA-\d{4}-\d{4}|MAFE-\d{4}-\d{4}|NACO-\d{4}-\d{4}")
    ids = {i["external_id"] for i in items}
    assert {"JOTA-2025-1111", "MAFE-2025-2222", "NACO-2025-3333"}.issubset(ids)


def test_springer_details_parse():
    html = _read_fixture("springer_details_simple.html")
    d = parse_details_html(html)
    assert len(d.get("authors", [])) >= 2
    files = d.get("files", [])
    assert any(f["filename"].endswith(".pdf") for f in files)
