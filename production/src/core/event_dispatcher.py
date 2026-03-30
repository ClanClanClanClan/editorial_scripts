"""Event dispatcher — detects state changes after extraction and emits events."""

import fcntl
import json
from datetime import datetime
from pathlib import Path

from core.state_store import StateStore

EVENTS_DIR = Path(__file__).resolve().parents[2] / "events"
PENDING_FILE = EVENTS_DIR / "pending.jsonl"
PROCESSED_FILE = EVENTS_DIR / "processed.jsonl"


def _append_event(event: dict, path: Path = PENDING_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "a+") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            with open(path, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def process_extraction(data: dict, journal: str, source_file: str | None = None) -> list[dict]:
    store = StateStore()
    events = []

    for manuscript in data.get("manuscripts", []):
        ms_id = manuscript.get("manuscript_id", "")
        if not ms_id:
            continue

        event = store.update_state(manuscript, journal)
        if event:
            event["timestamp"] = datetime.now().isoformat()
            event["extraction_ts"] = data.get("extraction_timestamp", "")
            if source_file:
                event["source_file"] = source_file
            events.append(event)
            _append_event(event)

            event_type = event["type"]
            if event_type == "NEW_MANUSCRIPT":
                print(f"  📌 New manuscript: {journal.upper()}/{ms_id}")
            elif event_type == "ALL_REPORTS_IN":
                print(
                    f"  ✅ All reports in: {journal.upper()}/{ms_id} "
                    f"({event.get('completed', '?')} reports)"
                )
            elif event_type == "STATUS_CHANGED":
                changes = event.get("changes", {})
                parts = []
                if changes.get("new_reports"):
                    parts.append(f"{changes['new_reports']} new report(s)")
                if changes.get("new_acceptances"):
                    parts.append(f"{changes['new_acceptances']} new acceptance(s)")
                if changes.get("new_declines"):
                    parts.append(f"{changes['new_declines']} new decline(s)")
                if changes.get("new_status"):
                    parts.append(f"status → {changes['new_status']}")
                desc = ", ".join(parts) if parts else "state changed"
                print(f"  🔄 {journal.upper()}/{ms_id}: {desc}")

    if events:
        print(f"\n📢 {len(events)} event(s) detected for {journal.upper()}")
    return events


def get_pending_events() -> list[dict]:
    if not PENDING_FILE.exists():
        return []
    events = []
    for line in PENDING_FILE.read_text().strip().split("\n"):
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def mark_processed(events: list[dict]):
    for event in events:
        event["processed_at"] = datetime.now().isoformat()
        _append_event(event, PROCESSED_FILE)

    if PENDING_FILE.exists():
        lock_path = PENDING_FILE.with_suffix(".lock")
        with open(lock_path, "a+") as lock_f:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
            try:
                remaining = get_pending_events()
                processed_ids = {
                    (e.get("manuscript_id"), e.get("journal"), e.get("timestamp")) for e in events
                }
                kept = [
                    e
                    for e in remaining
                    if (e.get("manuscript_id"), e.get("journal"), e.get("timestamp"))
                    not in processed_ids
                ]
                tmp_path = PENDING_FILE.with_suffix(".tmp")
                tmp_path.write_text(
                    "\n".join(json.dumps(e, default=str) for e in kept) + "\n" if kept else ""
                )
                tmp_path.rename(PENDING_FILE)
            finally:
                fcntl.flock(lock_f, fcntl.LOCK_UN)
