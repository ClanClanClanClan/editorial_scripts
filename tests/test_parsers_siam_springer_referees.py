from pathlib import Path

from src.platforms.siam_parsers import parse_audit_trail_html as siam_audit
from src.platforms.siam_parsers import parse_referees_html
from src.platforms.springer_parsers import parse_audit_trail_html as springer_audit
from src.platforms.springer_parsers import parse_referees_html as springer_refs


def _read(name: str) -> str:
    return (Path("tests/fixtures") / name).read_text()


def test_siam_referees_and_timeline():
    html = _read("siam_details_with_reviewers.html")
    refs = parse_referees_html(html)
    assert any(r["name"] == "Ref One" for r in refs)
    events = siam_audit(html)
    assert any("Reminder sent" in e["event"] for e in events)


def test_springer_referees_and_timeline():
    html = _read("springer_details_with_reviewers.html")
    refs = springer_refs(html)
    assert any(r["status"].lower().startswith("invited") for r in refs)
    events = springer_audit(html)
    assert any("Invitation sent" in e["event"] for e in events)
