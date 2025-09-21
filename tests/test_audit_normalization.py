from src.ecc.core.audit_normalization import normalize_events


def test_normalize_audit_trail_basic():
    raw = [
        {
            "datetime": "01-Jan-2025 10:00",
            "event": "Invitation sent",
            "status": "Completed",
            "letter": {"raw": "a", "has_attachment": True},
        },
        {"datetime": "02-Jan-2025", "event": "Reminder", "status": "Queued"},
    ]
    norm = normalize_events(raw)
    assert isinstance(norm, list)
    required = {"datetime", "event", "status", "letter"}
    assert all(required.issubset(set(ev.keys())) for ev in norm)
    # Datetime must be string containing at least one digit (loose convention)
    assert all(
        isinstance(ev["datetime"], str) and any(ch.isdigit() for ch in ev["datetime"])
        for ev in norm
    )
    # Event and status are strings
    assert all(isinstance(ev["event"], str) and isinstance(ev["status"], str) for ev in norm)
    # ISO parsing present when possible
    assert any("datetime_iso" in ev for ev in norm)
    # Letter is either None or dict
    assert all((ev["letter"] is None) or isinstance(ev["letter"], dict) for ev in norm)
