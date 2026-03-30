"""Manuscript state store — tracks last-known state for change detection."""

import hashlib
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
DB_PATH = CACHE_DIR / "manuscript_state.db"


class StateStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """CREATE TABLE IF NOT EXISTS manuscript_state (
                    manuscript_id TEXT NOT NULL,
                    journal TEXT NOT NULL,
                    status TEXT,
                    referees_agreed INTEGER DEFAULT 0,
                    referees_completed INTEGER DEFAULT 0,
                    referees_declined INTEGER DEFAULT 0,
                    referees_pending INTEGER DEFAULT 0,
                    needs_ae_decision INTEGER DEFAULT 0,
                    state_hash TEXT,
                    last_extraction_ts TEXT,
                    PRIMARY KEY (manuscript_id, journal)
                )"""
            )
            conn.commit()
            conn.close()

    @staticmethod
    def _compute_hash(manuscript: dict, journal: str) -> str:
        key_data = {
            "status": manuscript.get("status", ""),
            "referees": [],
        }
        for ref in manuscript.get("referees", []):
            rec = ref.get("recommendation", "")
            if rec.lower() in (
                "",
                "unknown",
                "n/a",
                "pending",
                "in progress",
                "none",
                "awaiting",
            ):
                rec = ""
            key_data["referees"].append(
                {
                    "name": ref.get("name", ""),
                    "status": ref.get("status", ""),
                    "recommendation": rec,
                    "review_received": (ref.get("status_details") or {}).get(
                        "review_received", False
                    ),
                    "review_complete": (ref.get("status_details") or {}).get(
                        "review_complete", False
                    ),
                    "has_report_text": bool((ref.get("report") or {}).get("comments_to_author")),
                    "returned": bool((ref.get("dates") or {}).get("returned")),
                }
            )
        raw = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()

    def get_state(self, manuscript_id: str, journal: str) -> dict | None:
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM manuscript_state WHERE manuscript_id=? AND journal=?",
                (manuscript_id, journal),
            ).fetchone()
            conn.close()
            if row:
                return dict(row)
            return None

    def update_state(self, manuscript: dict, journal: str) -> dict | None:
        ms_id = manuscript.get("manuscript_id", "")
        if not ms_id:
            return None

        referees = manuscript.get("referees", [])
        completed = 0
        agreed = 0
        declined = 0
        pending = 0

        for ref in referees:
            status = (ref.get("status") or "").lower()
            sd = ref.get("status_details") or {}
            report = ref.get("report") or {}
            rec = ref.get("recommendation", "")

            is_complete = (
                status in ("report submitted", "review complete", "completed")
                or sd.get("review_received")
                or sd.get("review_complete")
                or bool(report.get("comments_to_author"))
                or (rec and rec.lower() not in ("unknown", "n/a", ""))
            )
            is_declined = "decline" in status or "terminated" in status

            if is_complete:
                completed += 1
            elif is_declined:
                declined += 1
            elif status in ("awaiting report", "agreed"):
                agreed += 1
            else:
                pending += 1

        needs_ae = 1 if completed >= 2 and agreed == 0 and pending == 0 else 0
        new_hash = self._compute_hash(manuscript, journal)
        old_state = self.get_state(ms_id, journal)

        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT OR REPLACE INTO manuscript_state
                   (manuscript_id, journal, status, referees_agreed, referees_completed,
                    referees_declined, referees_pending, needs_ae_decision, state_hash,
                    last_extraction_ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ms_id,
                    journal,
                    manuscript.get("status", ""),
                    agreed,
                    completed,
                    declined,
                    pending,
                    needs_ae,
                    new_hash,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()

        if old_state is None:
            return {"type": "NEW_MANUSCRIPT", "manuscript_id": ms_id, "journal": journal}

        if old_state["state_hash"] != new_hash:
            changes = {}
            if old_state.get("needs_ae_decision", 0) == 0 and needs_ae == 1:
                return {
                    "type": "ALL_REPORTS_IN",
                    "manuscript_id": ms_id,
                    "journal": journal,
                    "completed": completed,
                }
            if completed > old_state.get("referees_completed", 0):
                changes["new_reports"] = completed - old_state["referees_completed"]
            if agreed > old_state.get("referees_agreed", 0):
                changes["new_acceptances"] = agreed - old_state["referees_agreed"]
            if declined > old_state.get("referees_declined", 0):
                changes["new_declines"] = declined - old_state["referees_declined"]
            if old_state.get("status") != manuscript.get("status", ""):
                changes["old_status"] = old_state["status"]
                changes["new_status"] = manuscript.get("status", "")
            return {
                "type": "STATUS_CHANGED",
                "manuscript_id": ms_id,
                "journal": journal,
                "changes": changes,
            }

        return None
