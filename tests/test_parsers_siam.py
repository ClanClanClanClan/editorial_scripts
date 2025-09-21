from pathlib import Path

from src.platforms.siam_parsers import parse_authors_html, parse_details_html, parse_list_html


def _read_fixture(name: str) -> str:
    return (Path("tests/fixtures") / name).read_text()


def test_siam_list_parsing():
    html = _read_fixture("siam_list_simple.html")
    items = parse_list_html(html, r"SICON-\d{4}-\d{4}|SIFIN-\d{4}-\d{4}")
    ids = {i["external_id"] for i in items}
    assert "SICON-2025-0123" in ids
    assert "SIFIN-2025-0456" in ids


def test_siam_authors_parsing_simple_table():
    html = """
    <table>
      <tr><th>Name</th><th>Email</th><th>Affiliation</th></tr>
      <tr><td>Alice Smith</td><td>alice@example.org</td><td>SIAM University</td></tr>
      <tr><td>Bob Lee</td><td>bob@example.org</td><td>Control Dept</td></tr>
    </table>
    """
    authors = parse_authors_html(html)
    assert len(authors) == 2
    assert authors[0]["name"] == "Alice Smith"
    assert authors[0]["email"] == "alice@example.org"


def test_siam_details_parse():
    html = _read_fixture("siam_details_simple.html")
    d = parse_details_html(html)
    assert len(d.get("authors", [])) == 2
    files = d.get("files", [])
    assert any(f["filename"].endswith(".pdf") for f in files)
