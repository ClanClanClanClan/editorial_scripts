"""Pure HTML parsers for SIAM-like editorial pages (SICON, SIFIN).

These are heuristic and operate on fixture HTML for unit tests.
"""

from __future__ import annotations

import re
from typing import Any


def parse_list_html(html: str, manuscript_pattern: str) -> list[dict[str, str]]:
    pat = re.compile(manuscript_pattern)
    items: list[dict[str, str]] = []
    # Scan table rows
    for row in re.split(r"<tr[^>]*>", html, flags=re.I):
        if "</tr>" not in row:
            continue
        # Extract all anchor and cell texts
        texts = [
            re.sub(r"<[^>]+>", "", s).strip()
            for s in re.findall(r"<(?:a|td)[^>]*>(.*?)</(?:a|td)>", row, flags=re.I | re.S)
        ]
        if not texts:
            continue
        external_id = None
        # Try matching in any cell text
        for t in texts:
            m = pat.search(t)
            if m:
                external_id = m.group(0)
                break
        # Fallback: match on raw row text without tags
        if not external_id:
            plain = re.sub(r"<[^>]+>", " ", row)
            m2 = pat.search(plain)
            if m2:
                external_id = m2.group(0)
        if not external_id:
            continue
        # Heuristic: assume next texts correspond to title/status
        title = ""
        status = ""
        if len(texts) >= 2:
            # choose the first non-id as title
            for t in texts:
                if t != external_id:
                    title = t
                    break
        if len(texts) >= 3:
            status = texts[-1]

        items.append(
            {
                "external_id": external_id,
                "title": title,
                "status_text": status,
            }
        )
    return items


def parse_authors_html(html: str) -> list[dict[str, Any]]:
    """Parse a simple authors table with columns: Name, Email, Affiliation."""
    authors: list[dict[str, Any]] = []
    for row in re.split(r"<tr[^>]*>", html, flags=re.I):
        if "</tr>" not in row:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = vals[0]
        email = vals[1]
        aff = vals[2] if len(vals) > 2 else ""
        if name:
            authors.append({"name": name, "email": email, "affiliation": aff})
    return authors


def parse_details_html(html: str) -> dict[str, Any]:
    """Parse a SIAM manuscript details page for authors and file links.

    Returns a dict with optional keys: authors (list), files (list of dicts with filename, url).
    """
    data: dict[str, Any] = {"authors": [], "files": []}
    try:
        data["authors"] = parse_authors_html(html)
    except Exception:
        pass

    # Extract basic file anchors (pdf, doc, zip)
    files: list[dict[str, str]] = []
    for href, text in re.findall(r"(?is)<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", html):
        low = f"{href} {text}".lower()
        if any(ext in low for ext in [".pdf", ".doc", ".docx", ".zip"]):
            # Infer filename from href or text
            fname = None
            m = re.search(r"/([^/]+)$", href)
            if m:
                fname = m.group(1)
            if not fname:
                fname = re.sub(r"<[^>]+>", "", text).strip().replace(" ", "_") or "file"
            files.append({"filename": fname, "url": href})
    data["files"] = files
    return data


def parse_referees_html(html: str) -> list[dict[str, Any]]:
    """Parse a basic referees table for SIAM pages.

    Columns expected: Name, Status, Invited, Agreed, Due, Returned
    """
    refs: list[dict[str, Any]] = []
    # Try to isolate a section labelled Reviewers
    m = re.search(r"(?is)(<h[23][^>]*>\s*Reviewers\s*</h[23]>.*)$", html)
    segment = m.group(1) if m else html
    for row in re.split(r"<tr[^>]*>", segment, flags=re.I):
        if "</tr>" not in row:
            continue
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", row)
        if len(cells) < 2:
            continue
        vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = vals[0]
        status = vals[1] if len(vals) > 1 else ""
        invited = vals[2] if len(vals) > 2 else ""
        agreed = vals[3] if len(vals) > 3 else ""
        due = vals[4] if len(vals) > 4 else ""
        returned = vals[5] if len(vals) > 5 else ""
        if name:
            refs.append(
                {
                    "name": name,
                    "status": status,
                    "invited": invited,
                    "agreed": agreed,
                    "due": due,
                    "returned": returned,
                }
            )
    return refs


def parse_audit_trail_html(html: str) -> list[dict[str, Any]]:
    """Parse a simple timeline events table for SIAM pages.

    Expects rows with Date, Event, Status.
    """
    events: list[dict[str, Any]] = []
    row_re = re.compile(
        r"(?is)<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>"
    )
    for mm in row_re.finditer(html):
        dt, ev, st = (re.sub(r"<[^>]+>", "", g).strip() for g in mm.groups())
        if dt and ev:
            events.append({"datetime": dt, "event": ev, "status": st})
    return events
