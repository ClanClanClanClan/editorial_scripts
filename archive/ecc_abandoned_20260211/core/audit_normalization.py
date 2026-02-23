"""Audit event normalization helpers.

Produces a consistent event schema across adapters:
  { 'datetime': str, 'event': str, 'status': str, 'letter': Optional[dict] }
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any


def _parse_datetime_iso(dt: str) -> str | None:
    s = (dt or "").strip()
    if not s:
        return None
    # Try a set of common formats
    fmts = [
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%b %d, %Y %H:%M",
    ]
    # Try RFC1123-like
    try:
        d = datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %Z")
        return d.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        pass
    # ISO with Z
    if s.endswith("Z"):
        try:
            d = datetime.strptime(s[:-1], "%Y-%m-%dT%H:%M:%S")
            return d.replace(tzinfo=UTC).strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            pass
    # ISO with offset +HH:MM or +HHMM
    m = re.search(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-])(\d{2}):?(\d{2})$", s)
    if m:
        base, sign, hh, mm = m.groups()
        try:
            d = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
            offset = int(hh) * 60 + int(mm)
            if sign == "-":
                offset = -offset
            tz = timezone(timedelta(minutes=offset))
            return d.replace(tzinfo=tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            pass
    for f in fmts:
        try:
            d = datetime.strptime(s, f)
            # Format as ISO without timezone
            if d.hour == 0 and d.minute == 0 and d.second == 0 and ("%H" not in f):
                return d.strftime("%Y-%m-%dT00:00:00")
            return d.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            continue
    return None


def normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    norm: list[dict[str, Any]] = []
    for ev in events or []:
        try:
            dt = str(ev.get("datetime", "")).strip()
            event = str(ev.get("event", "")).strip()
            status = str(ev.get("status", "")).strip()
            letter = ev.get("letter") if isinstance(ev.get("letter"), dict) else None
            norm_ev = {
                "datetime": dt,
                "event": event,
                "status": status,
                "letter": letter,
            }
            iso = _parse_datetime_iso(dt)
            if iso:
                norm_ev["datetime_iso"] = iso
            norm.append(norm_ev)
        except Exception:
            continue
    return norm
