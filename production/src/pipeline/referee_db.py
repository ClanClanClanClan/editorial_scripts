"""Referee performance database — tracks historical referee behavior."""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from pipeline import MODELS_DIR, normalize_name

DB_PATH = MODELS_DIR / "referee_profiles.db"


class RefereeDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """CREATE TABLE IF NOT EXISTS referee_profiles (
                    referee_key TEXT PRIMARY KEY,
                    display_name TEXT,
                    email TEXT,
                    institution TEXT,
                    orcid TEXT,
                    h_index INTEGER,
                    first_seen TEXT,
                    last_seen TEXT,
                    total_invitations INTEGER DEFAULT 0,
                    total_accepted INTEGER DEFAULT 0,
                    total_declined INTEGER DEFAULT 0,
                    total_completed INTEGER DEFAULT 0,
                    total_no_response INTEGER DEFAULT 0,
                    avg_response_days REAL,
                    avg_review_days REAL,
                    avg_report_quality REAL,
                    journals_served TEXT DEFAULT '[]',
                    research_topics TEXT DEFAULT '[]',
                    updated_at TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS referee_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_key TEXT,
                    journal TEXT,
                    manuscript_id TEXT,
                    invited_date TEXT,
                    response TEXT,
                    response_date TEXT,
                    agreed_date TEXT,
                    due_date TEXT,
                    returned_date TEXT,
                    days_to_respond INTEGER,
                    days_to_complete INTEGER,
                    was_overdue INTEGER DEFAULT 0,
                    recommendation TEXT,
                    report_quality_score REAL,
                    report_word_count INTEGER,
                    reminders_received INTEGER DEFAULT 0,
                    created_at TEXT,
                    UNIQUE(referee_key, journal, manuscript_id)
                )"""
            )
            conn.commit()
            conn.close()

    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def record_assignment(
        self,
        referee_name: str,
        email: str | None,
        journal: str,
        manuscript_id: str,
        dates: dict,
        status: str,
        recommendation: str | None = None,
        institution: str | None = None,
        orcid: str | None = None,
        h_index: int | None = None,
        report_quality_score: float | None = None,
        report_word_count: int | None = None,
        reminders: int = 0,
        research_topics: list | None = None,
    ):
        key = normalize_name(referee_name)
        if not key:
            return

        invited = dates.get("invited")
        agreed = dates.get("agreed")
        returned = dates.get("returned")
        due = dates.get("due")
        response_date = dates.get("response_date") or agreed

        status_lower = (status or "").lower()
        if "decline" in status_lower or "terminated" in status_lower:
            response = "declined"
        elif (
            agreed
            or "agreed" in status_lower
            or "awaiting report" in status_lower
            or "report submitted" in status_lower
        ):
            response = "accepted"
        elif "no response" in status_lower or "pending" in status_lower:
            response = "no_response"
        else:
            response = "unknown"

        days_respond = None
        if invited and response_date:
            days_respond = self._days_between(invited, response_date)

        days_complete = None
        if agreed and returned:
            days_complete = self._days_between(agreed, returned)

        was_overdue = 0
        if due and returned:
            was_overdue = 1 if self._days_between(due, returned) > 0 else 0
        elif due and not returned and response == "accepted":
            from datetime import date

            try:
                due_date = self._parse_date(due)
                if due_date and due_date < date.today():
                    was_overdue = 1
            except Exception:
                pass

        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT OR REPLACE INTO referee_assignments
                   (referee_key, journal, manuscript_id, invited_date, response,
                    response_date, agreed_date, due_date, returned_date,
                    days_to_respond, days_to_complete, was_overdue,
                    recommendation, report_quality_score, report_word_count,
                    reminders_received, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    key,
                    journal.lower(),
                    manuscript_id,
                    invited,
                    response,
                    response_date,
                    agreed,
                    due,
                    returned,
                    days_respond,
                    days_complete,
                    was_overdue,
                    recommendation,
                    report_quality_score,
                    report_word_count,
                    reminders,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()

        self._update_profile(
            key,
            referee_name,
            email,
            institution,
            orcid,
            h_index,
            journal,
            research_topics,
        )

    def _update_profile(
        self,
        key: str,
        name: str,
        email: str | None,
        institution: str | None,
        orcid: str | None,
        h_index: int | None,
        journal: str,
        research_topics: list | None,
    ):
        with self._lock:
            conn = self._conn()

            rows = conn.execute(
                "SELECT * FROM referee_assignments WHERE referee_key=?", (key,)
            ).fetchall()

            total = len(rows)
            accepted = sum(1 for r in rows if r["response"] == "accepted")
            declined = sum(1 for r in rows if r["response"] == "declined")
            no_resp = sum(1 for r in rows if r["response"] == "no_response")
            completed = sum(1 for r in rows if r["returned_date"])

            respond_days = [r["days_to_respond"] for r in rows if r["days_to_respond"] is not None]
            review_days = [r["days_to_complete"] for r in rows if r["days_to_complete"] is not None]
            quality_scores = [
                r["report_quality_score"] for r in rows if r["report_quality_score"] is not None
            ]

            journals = list({r["journal"] for r in rows})

            existing = conn.execute(
                "SELECT * FROM referee_profiles WHERE referee_key=?", (key,)
            ).fetchone()
            first_seen = existing["first_seen"] if existing else datetime.now().isoformat()

            topics = research_topics or []
            if existing and existing["research_topics"]:
                try:
                    old_topics = json.loads(existing["research_topics"])
                    topics = list(set(old_topics + topics))
                except (json.JSONDecodeError, TypeError):
                    pass

            conn.execute(
                """INSERT OR REPLACE INTO referee_profiles
                   (referee_key, display_name, email, institution, orcid, h_index,
                    first_seen, last_seen,
                    total_invitations, total_accepted, total_declined,
                    total_completed, total_no_response,
                    avg_response_days, avg_review_days, avg_report_quality,
                    journals_served, research_topics, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    key,
                    name,
                    email or (existing["email"] if existing else None),
                    institution or (existing["institution"] if existing else None),
                    orcid or (existing["orcid"] if existing else None),
                    h_index or (existing["h_index"] if existing else None),
                    first_seen,
                    datetime.now().isoformat(),
                    total,
                    accepted,
                    declined,
                    completed,
                    no_resp,
                    sum(respond_days) / len(respond_days) if respond_days else None,
                    sum(review_days) / len(review_days) if review_days else None,
                    sum(quality_scores) / len(quality_scores) if quality_scores else None,
                    json.dumps(journals),
                    json.dumps(topics[:20]),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()

    def get_profile(self, name: str) -> dict | None:
        key = normalize_name(name)
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM referee_profiles WHERE referee_key=?", (key,)
            ).fetchone()
            conn.close()
            if row:
                result = dict(row)
                result["journals_served"] = json.loads(result.get("journals_served") or "[]")
                result["research_topics"] = json.loads(result.get("research_topics") or "[]")
                return result
            return None

    def get_track_record(self, name: str) -> dict:
        profile = self.get_profile(name)
        if not profile:
            return {}
        total = profile.get("total_invitations", 0)
        if total == 0:
            return {}
        return {
            "invitations": total,
            "acceptance_rate": round(profile["total_accepted"] / total, 2) if total else 0,
            "completion_rate": (
                round(profile["total_completed"] / profile["total_accepted"], 2)
                if profile["total_accepted"]
                else 0
            ),
            "avg_response_days": (
                round(profile["avg_response_days"], 1) if profile["avg_response_days"] else None
            ),
            "avg_review_days": (
                round(profile["avg_review_days"], 1) if profile["avg_review_days"] else None
            ),
            "avg_quality": (
                round(profile["avg_report_quality"], 2) if profile["avg_report_quality"] else None
            ),
            "journals": profile["journals_served"],
        }

    def get_top_referees(self, min_invitations: int = 3, limit: int = 20) -> list[dict]:
        with self._lock:
            conn = self._conn()
            rows = conn.execute(
                """SELECT * FROM referee_profiles
                   WHERE total_invitations >= ? AND total_completed > 0
                   ORDER BY avg_report_quality DESC, total_completed DESC
                   LIMIT ?""",
                (min_invitations, limit),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def get_chronic_decliners(self, min_invitations: int = 3) -> list[dict]:
        with self._lock:
            conn = self._conn()
            rows = conn.execute(
                """SELECT * FROM referee_profiles
                   WHERE total_invitations >= ?
                   AND CAST(total_declined AS REAL) / total_invitations > 0.7
                   ORDER BY total_declined DESC""",
                (min_invitations,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]

    @staticmethod
    def _days_between(d1: str, d2: str) -> int | None:
        try:
            p1 = RefereeDB._parse_date(d1)
            p2 = RefereeDB._parse_date(d2)
            if p1 and p2:
                return (p2 - p1).days
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_date(d: str):
        if not d:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(d[:10], fmt[: min(len(fmt), 10)]).date()
            except (ValueError, TypeError):
                continue
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
        except Exception:
            return None
