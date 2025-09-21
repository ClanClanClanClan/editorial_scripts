from pathlib import Path

from src.platforms.scholarone_parsers import (
    parse_audit_trail_html,
    parse_authors_html,
    parse_manuscript_list_html,
    parse_referees_html,
)


def _read_fixture(name: str) -> str:
    p = Path("tests/fixtures") / name
    return p.read_text()


def test_parse_manuscript_list_html_simple():
    html = _read_fixture("scholarone_list_simple.html")
    items_mor = parse_manuscript_list_html(html, r"MOR-\d{4}-\d{4}")
    items_mf = parse_manuscript_list_html(html, r"MAFI-\d{4}-\d{4}")

    assert any(i["external_id"] == "MOR-2025-1234" for i in items_mor)
    assert any(i["external_id"] == "MAFI-2025-5678" for i in items_mf)
    # Check extracted fields
    mor = next(i for i in items_mor if i["external_id"] == "MOR-2025-1234")
    assert mor["title"] == "Sample Title A"
    assert "Awaiting" in mor["status_text"]


def test_parse_audit_trail_html_simple():
    html = _read_fixture("scholarone_audit_simple.html")
    events = parse_audit_trail_html(html)
    assert len(events) >= 2
    first = events[0]
    assert "Decision Letter" in first["event"]
    assert first["letter"] and first["letter"]["has_attachment"] is True


def test_parse_authors_and_referees_from_details():
    html = _read_fixture("scholarone_details_simple.html")
    authors = parse_authors_html(html)
    refs = parse_referees_html(html)
    assert len(authors) == 2
    assert authors[0]["name"] == "Jane Doe"
    assert any(r["name"] == "Referee Alpha" for r in refs)
