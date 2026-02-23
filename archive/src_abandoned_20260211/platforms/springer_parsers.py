"""Pure HTML parsers for Springer-like editorial pages (JOTA, MAFE, NACO)."""

from __future__ import annotations

import re
from typing import Any


def parse_list_html(html: str, manuscript_pattern: str) -> list[dict[str, str]]:
    pat = re.compile(manuscript_pattern)
    items: list[dict[str, str]] = []
    # Rows might be <li> or <tr>; support both
    blocks = re.split(r"<(?:tr|li)[^>]*>", html, flags=re.I)
    for block in blocks:
        if "</tr>" not in block and "</li>" not in block:
            continue
        texts = [
            re.sub(r"<[^>]+>", "", s).strip()
            for s in re.findall(
                r"<(?:a|td|span|div)[^>]*>(.*?)</(?:a|td|span|div)>", block, flags=re.I | re.S
            )
        ]
        if not texts:
            continue
        ms_id = None
        for t in texts:
            if pat.search(t):
                ms_id = t
                break
        if not ms_id:
            continue
        title = ""
        status = ""
        for t in texts:
            if t and t != ms_id:
                title = t
                break
        if len(texts) > 2:
            status = texts[-1]
        items.append({"external_id": ms_id, "title": title, "status_text": status})
    return items


def parse_details_html(html: str) -> dict[str, Any]:
    """Parse a Springer details page for file links (e.g., PDF) and basic authors list.

    Returns dict with optional keys: authors (list of strings), files (list of {filename,url}).
    """
    out: dict[str, Any] = {"authors": [], "files": []}
    # Authors as list items or table cells labelled 'Authors'
    names: list[str] = []
    for frag in re.findall(r"(?is)<li[^>]*class=\"author[^\"]*\"[^>]*>(.*?)</li>", html):
        name = re.sub(r"<[^>]+>", "", frag).strip()
        if name:
            names.append(name)
    if not names:
        # fallback simple table parsing
        for cell in re.findall(r"(?is)<td[^>]*>(.*?)</td>", html):
            t = re.sub(r"<[^>]+>", "", cell).strip()
            if t and any(k in t.lower() for k in ["author", "authors"]) is False:
                # naive heuristic: skip header cells
                pass
    out["authors"] = names

    files: list[dict[str, str]] = []
    for href, text in re.findall(r"(?is)<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", html):
        low = f"{href} {text}".lower()
        if any(ext in low for ext in [".pdf", ".doc", ".docx", ".zip"]):
            fname = None
            m = re.search(r"/([^/]+)$", href)
            if m:
                fname = m.group(1)
            if not fname:
                fname = re.sub(r"<[^>]+>", "", text).strip().replace(" ", "_") or "file"
            files.append({"filename": fname, "url": href})
    out["files"] = files
    return out


def parse_referees_html(html: str) -> list[dict[str, Any]]:
    """Parse a basic referees section for Springer pages (heuristic)."""
    refs: list[dict[str, Any]] = []
    # Look for list items or rows that contain reviewer names and status
    row_re = re.compile(r"(?is)<tr[^>]*>.*?</tr>")
    for mm in row_re.finditer(html):
        row = mm.group(0)
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", row)
        if len(cells) >= 2:
            vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            name = vals[0]
            status = vals[1]
            if name and any(
                k in status.lower()
                for k in ["invited", "agreed", "returned", "declined", "overdue"]
            ):
                refs.append({"name": name, "status": status})
    return refs


def parse_audit_trail_html(html: str) -> list[dict[str, Any]]:
    """Parse a simple timeline table for Springer pages: date, event, status."""
    events: list[dict[str, Any]] = []
    row_re = re.compile(
        r"(?is)<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>"
    )
    for mm in row_re.finditer(html):
        dt, ev, st = (re.sub(r"<[^>]+>", "", g).strip() for g in mm.groups())
        if dt and ev:
            events.append({"datetime": dt, "event": ev, "status": st})
    return events
