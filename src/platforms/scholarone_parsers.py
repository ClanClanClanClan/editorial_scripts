"""Pure HTML parsers for ScholarOne pages (no browser dependency).

These functions accept HTML strings and return simple Python structures
that adapters can map onto domain models. Keeping parsing pure enables
offline unit tests using fixtures.
"""

from __future__ import annotations

import re
from typing import Any


def _split_rows(html: str) -> list[str]:
    # Naive row splitter; sufficient for controlled fixtures
    parts = re.split(r"<tr[^>]*>", html, flags=re.I)
    # Remove leading non-row content
    return [p for p in parts if "</tr>" in p]


def parse_manuscript_list_html(html: str, manuscript_pattern: str) -> list[dict[str, str]]:
    """Parse a ScholarOne manuscript list page into lightweight items.

    Returns list of dicts: {external_id, title, status_text}
    """
    items: list[dict[str, str]] = []
    rows = _split_rows(html)
    pat = re.compile(manuscript_pattern)

    for row in rows:
        try:
            # Find an anchor whose text matches the manuscript id pattern
            # Allow inner HTML decorations; extract inner text crudely
            anchor_texts = [
                re.sub(r"<[^>]+>", "", t).strip()
                for t in re.findall(r"<a[^>]*>(.*?)</a>", row, flags=re.I | re.S)
            ]
            external_id = None
            for t in anchor_texts:
                if pat.search(t):
                    external_id = t
                    break
            if not external_id:
                continue

            # Title: try 2nd cell text
            cells = [
                re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
            ]
            title = cells[1] if len(cells) > 1 else ""
            status_text = cells[2] if len(cells) > 2 else ""

            items.append(
                {
                    "external_id": external_id,
                    "title": title,
                    "status_text": status_text,
                }
            )
        except Exception:
            continue

    return items


def parse_audit_trail_html(html: str) -> list[dict[str, Any]]:
    """Parse an Audit Trail table into event dicts using a simple row pattern."""
    events: list[dict[str, Any]] = []
    # Find any table row that contains at least three <td> cells
    row_re = re.compile(r"(?is)<tr[^>]*>.*?</tr>")
    for mm in row_re.finditer(html):
        row = mm.group(0)
        tds = re.findall(r"(?is)<td[^>]*>(.*?)</td>", row)
        if len(tds) < 3:
            continue
        dt_raw, ev_cell, st_raw = tds[0], tds[1], tds[2]
        dt = re.sub(r"<[^>]+>", "", dt_raw).strip()
        st = re.sub(r"<[^>]+>", "", st_raw).strip()
        ev_text = re.sub(r"<[^>]+>", "", ev_cell).strip()
        letter = None
        if re.search(r"letter|view\s*letter|icon_paperclip", ev_cell, re.I):
            para = re.search(r"<p[^>]*>(.*?)</p>", ev_cell, flags=re.I | re.S)
            raw = re.sub(r"<[^>]+>", "", para.group(1)).strip() if para else ev_text
            has_attachment = bool(re.search(r"icon_paperclip", ev_cell, re.I))
            letter = {"raw": raw, "has_attachment": has_attachment}
        events.append(
            {
                "datetime": dt,
                "event": ev_text,
                "status": st,
                "letter": letter,
            }
        )
    return events


def parse_authors_html(html: str) -> list[dict[str, Any]]:
    """Parse authors table with columns like Name, Email, Affiliation.

    Returns list of dicts with keys: name, email, affiliation.
    """
    authors: list[dict[str, Any]] = []
    # Narrow to section between Authors and Reviewers if present
    start = re.search(r"(?is)<h[23][^>]*>\s*Authors\s*</h[23]>", html)
    end = re.search(r"(?is)<h[23][^>]*>\s*Reviewers\s*</h[23]>", html)
    segment = html
    if start:
        sidx = start.end()
        eidx = end.start() if end else len(html)
        segment = html[sidx:eidx]
    for row in re.split(r"<tr[^>]*>", segment, flags=re.I):
        if "</tr>" not in row:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = vals[0]
        email = vals[1]
        aff = vals[2] if len(vals) > 2 else ""
        if name and "@" in (email or ""):
            authors.append({"name": name, "email": email, "affiliation": aff})
    return authors


def parse_referees_html(html: str) -> list[dict[str, Any]]:
    """Parse a ScholarOne reviewer list table into referee dicts.

    Returns list with keys: name, status, invited, agreed, due, submitted
    (dates as raw strings where present).
    """
    refs: list[dict[str, Any]] = []
    # Narrow to section starting at Reviewers header if present
    m = re.search(r"(?is)<h[23][^>]*>\s*Reviewers\s*</h[23]>(.*)$", html)
    segment = m.group(1) if m else html
    for row in re.split(r"<tr[^>]*>", segment, flags=re.I):
        if "</tr>" not in row:
            continue
        # Try to detect reviewer name in anchor or bold text
        name = None
        for candidate in re.findall(
            r"<(?:a|b|strong)[^>]*>(.*?)</(?:a|b|strong)>", row, flags=re.I | re.S
        ):
            t = re.sub(r"<[^>]+>", "", candidate).strip()
            if t:
                name = t
                break
        if not name:
            continue
        # Extract columns
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        status = ""
        invited = agreed = due = submitted = ""
        if len(vals) >= 3:
            status = vals[2]
        # Search for dates keywords in row text
        low = re.sub(r"<[^>]+>", " ", row).lower()

        def _find_date(label: str, text: str = low) -> str:
            # label may contain alternations like 'returned|submitted'
            m = re.search(rf"(?:{label})\s*:\s*([^<\n]+)", text)
            return m.group(1).strip() if m else ""

        invited = _find_date("invited")
        agreed = _find_date("agreed")
        due = _find_date("due")
        submitted = _find_date("returned|submitted")
        refs.append(
            {
                "name": name,
                "status": status,
                "invited": invited,
                "agreed": agreed,
                "due": due,
                "submitted": submitted,
            }
        )
    return refs
