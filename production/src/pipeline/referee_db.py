"""Referee performance database — tracks historical referee behavior."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from pipeline import MODELS_DIR, normalize_name

DB_PATH = MODELS_DIR / "referee_profiles.db"

_MIGRATION_COLUMNS_PROFILES = [
    ("overdue_count", "INTEGER DEFAULT 0"),
    ("overdue_rate", "REAL"),
    ("quality_trend", "TEXT DEFAULT '[]'"),
    ("response_trend", "TEXT DEFAULT '[]'"),
    ("percentile_response", "REAL"),
    ("percentile_quality", "REAL"),
    ("percentile_speed", "REAL"),
    ("last_invited_date", "TEXT"),
    ("notes", "TEXT"),
]

_MIGRATION_COLUMNS_ASSIGNMENTS = [
    ("recommendation_used", "INTEGER DEFAULT 0"),
    ("feedback_score", "REAL"),
    ("reminder_effective", "INTEGER"),
]


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
                    display_name TEXT, email TEXT, institution TEXT, orcid TEXT,
                    h_index INTEGER, first_seen TEXT, last_seen TEXT,
                    total_invitations INTEGER DEFAULT 0, total_accepted INTEGER DEFAULT 0,
                    total_declined INTEGER DEFAULT 0, total_completed INTEGER DEFAULT 0,
                    total_no_response INTEGER DEFAULT 0,
                    avg_response_days REAL, avg_review_days REAL, avg_report_quality REAL,
                    journals_served TEXT DEFAULT '[]', research_topics TEXT DEFAULT '[]',
                    updated_at TEXT)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS referee_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_key TEXT, journal TEXT, manuscript_id TEXT,
                    invited_date TEXT, response TEXT, response_date TEXT,
                    agreed_date TEXT, due_date TEXT, returned_date TEXT,
                    days_to_respond INTEGER, days_to_complete INTEGER,
                    was_overdue INTEGER DEFAULT 0, recommendation TEXT,
                    report_quality_score REAL, report_word_count INTEGER,
                    reminders_received INTEGER DEFAULT 0, created_at TEXT,
                    UNIQUE(referee_key, journal, manuscript_id))"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS referee_journal_stats (
                    referee_key TEXT NOT NULL, journal TEXT NOT NULL,
                    total_invitations INTEGER DEFAULT 0, total_accepted INTEGER DEFAULT 0,
                    total_declined INTEGER DEFAULT 0, total_completed INTEGER DEFAULT 0,
                    avg_response_days REAL, avg_review_days REAL, avg_report_quality REAL,
                    overdue_count INTEGER DEFAULT 0, overdue_rate REAL, updated_at TEXT,
                    PRIMARY KEY (referee_key, journal))"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS model_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referee_key TEXT, journal TEXT, manuscript_id TEXT,
                    predicted_p_accept REAL, predicted_p_complete REAL,
                    actual_accepted INTEGER, actual_completed INTEGER,
                    actual_review_days INTEGER, predicted_at TEXT, resolved_at TEXT)"""
            )
            # SAFE: col/typedef from hardcoded constants, never user input.
            for col, typedef in _MIGRATION_COLUMNS_PROFILES:
                try:
                    conn.execute(f"ALTER TABLE referee_profiles ADD COLUMN {col} {typedef}")
                except sqlite3.OperationalError:
                    pass
            for col, typedef in _MIGRATION_COLUMNS_ASSIGNMENTS:
                try:
                    conn.execute(f"ALTER TABLE referee_assignments ADD COLUMN {col} {typedef}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
            conn.close()

    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self):
        conn = self._conn()
        try:
            yield conn
        finally:
            conn.close()

    def record_assignment(
        self,
        referee_name,
        email,
        journal,
        manuscript_id,
        dates,
        status,
        recommendation=None,
        institution=None,
        orcid=None,
        h_index=None,
        report_quality_score=None,
        report_word_count=None,
        reminders=0,
        research_topics=None,
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
        rec_lower = (recommendation or "").lower()
        has_recommendation = rec_lower and rec_lower not in ("unknown", "n/a", "none", "")
        if "decline" in status_lower or "terminated" in status_lower:
            response = "declined"
        elif (
            agreed
            or returned
            or has_recommendation
            or "agreed" in status_lower
            or "awaiting report" in status_lower
            or "report submitted" in status_lower
        ):
            response = "accepted"
        elif "no response" in status_lower or "pending" in status_lower:
            response = "no_response"
        else:
            response = "unknown"
        days_respond = (
            self._days_between(invited, response_date) if invited and response_date else None
        )
        days_complete = self._days_between(agreed, returned) if agreed and returned else None
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
            with self._connection() as conn:
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
        self._update_profile(
            key, referee_name, email, institution, orcid, h_index, journal, research_topics
        )

    def _update_profile(
        self, key, name, email, institution, orcid, h_index, journal, research_topics
    ):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_assignments WHERE referee_key=?", (key,)
                ).fetchall()
                total = len(rows)
                accepted = sum(1 for r in rows if r["response"] == "accepted")
                declined = sum(1 for r in rows if r["response"] == "declined")
                no_resp = sum(1 for r in rows if r["response"] == "no_response")
                completed = sum(1 for r in rows if r["returned_date"])
                overdue_count = sum(1 for r in rows if r["was_overdue"])
                respond_days = [
                    r["days_to_respond"] for r in rows if r["days_to_respond"] is not None
                ]
                review_days = [
                    r["days_to_complete"] for r in rows if r["days_to_complete"] is not None
                ]
                quality_scores = [
                    r["report_quality_score"] for r in rows if r["report_quality_score"] is not None
                ]
                quality_trend = quality_scores[-5:] if quality_scores else []
                response_trend = respond_days[-5:] if respond_days else []
                journals = list({r["journal"] for r in rows})
                invited_dates = [r["invited_date"] for r in rows if r["invited_date"]]
                last_invited = max(invited_dates) if invited_dates else None
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
                        first_seen, last_seen, total_invitations, total_accepted, total_declined,
                        total_completed, total_no_response, avg_response_days, avg_review_days,
                        avg_report_quality, overdue_count, overdue_rate, quality_trend, response_trend,
                        last_invited_date, journals_served, research_topics, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        key,
                        name,
                        email if email is not None else (existing["email"] if existing else None),
                        (
                            institution
                            if institution is not None
                            else (existing["institution"] if existing else None)
                        ),
                        orcid if orcid is not None else (existing["orcid"] if existing else None),
                        (
                            h_index
                            if h_index is not None
                            else (existing["h_index"] if existing else None)
                        ),
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
                        overdue_count,
                        round(overdue_count / completed, 2) if completed else None,
                        json.dumps(quality_trend),
                        json.dumps(response_trend),
                        last_invited,
                        json.dumps(journals),
                        json.dumps(topics[:20]),
                        datetime.now().isoformat(),
                    ),
                )
                self._update_journal_stats(conn, key, rows)
                conn.commit()

    def _update_journal_stats(self, conn, key, rows):
        for journal in {r["journal"] for r in rows}:
            j_rows = [r for r in rows if r["journal"] == journal]
            t, a, d, c, o = (
                len(j_rows),
                sum(1 for r in j_rows if r["response"] == "accepted"),
                sum(1 for r in j_rows if r["response"] == "declined"),
                sum(1 for r in j_rows if r["returned_date"]),
                sum(1 for r in j_rows if r["was_overdue"]),
            )
            rd = [r["days_to_respond"] for r in j_rows if r["days_to_respond"] is not None]
            vd = [r["days_to_complete"] for r in j_rows if r["days_to_complete"] is not None]
            qs = [
                r["report_quality_score"] for r in j_rows if r["report_quality_score"] is not None
            ]
            conn.execute(
                """INSERT OR REPLACE INTO referee_journal_stats
                   (referee_key, journal, total_invitations, total_accepted, total_declined,
                    total_completed, avg_response_days, avg_review_days, avg_report_quality,
                    overdue_count, overdue_rate, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    key,
                    journal,
                    t,
                    a,
                    d,
                    c,
                    sum(rd) / len(rd) if rd else None,
                    sum(vd) / len(vd) if vd else None,
                    sum(qs) / len(qs) if qs else None,
                    o,
                    round(o / c, 2) if c else None,
                    datetime.now().isoformat(),
                ),
            )

    def get_profile(self, name):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT * FROM referee_profiles WHERE referee_key=?", (key,)
                ).fetchone()
                if row:
                    result = dict(row)
                    for field in (
                        "journals_served",
                        "research_topics",
                        "quality_trend",
                        "response_trend",
                    ):
                        try:
                            result[field] = json.loads(result.get(field) or "[]")
                        except (json.JSONDecodeError, TypeError):
                            result[field] = []
                    return result
                return None

    def get_track_record(self, name):
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
            "overdue_rate": profile.get("overdue_rate"),
            "quality_trend": profile.get("quality_trend", []),
            "journals": profile["journals_served"],
        }

    def get_journal_stats(self, name, journal):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT * FROM referee_journal_stats WHERE referee_key=? AND journal=?",
                    (key, journal.lower()),
                ).fetchone()
                return dict(row) if row else None

    def get_top_referees(self, min_invitations=3, limit=20):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_profiles WHERE total_invitations >= ? AND total_completed > 0 ORDER BY avg_report_quality DESC, total_completed DESC LIMIT ?",
                    (min_invitations, limit),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def get_chronic_decliners(self, min_invitations=3):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_profiles WHERE total_invitations >= ? AND CAST(total_declined AS REAL) / total_invitations > 0.7 ORDER BY total_declined DESC",
                    (min_invitations,),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def get_overdue_repeat_offenders(self, min_overdue=2):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_profiles WHERE overdue_count >= ? ORDER BY overdue_rate DESC, overdue_count DESC",
                    (min_overdue,),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def get_quality_trend(self, name, window=5):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT report_quality_score FROM referee_assignments WHERE referee_key=? AND report_quality_score IS NOT NULL ORDER BY created_at DESC LIMIT ?",
                    (key, window),
                ).fetchall()
                return [r["report_quality_score"] for r in reversed(rows)]

    def get_referee_assignments(self, name, limit=20):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_assignments WHERE referee_key=? ORDER BY created_at DESC LIMIT ?",
                    (key, limit),
                ).fetchall()
                return [dict(r) for r in rows]

    def get_assignments_by_manuscript(self, journal, manuscript_id):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_assignments WHERE journal=? AND manuscript_id=?",
                    (journal.lower(), manuscript_id),
                ).fetchall()
                return [dict(r) for r in rows]

    def search_referees(self, query, limit=20):
        q = f"%{query.lower()}%"
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_profiles WHERE LOWER(display_name) LIKE ? OR LOWER(email) LIKE ? OR LOWER(institution) LIKE ? OR LOWER(COALESCE(notes, '')) LIKE ? ORDER BY total_invitations DESC LIMIT ?",
                    (q, q, q, q, limit),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def record_feedback(self, referee_name, journal, manuscript_id, was_used, feedback_score=None):
        key = normalize_name(referee_name)
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "UPDATE referee_assignments SET recommendation_used=?, feedback_score=? WHERE referee_key=? AND journal=? AND manuscript_id=?",
                    (1 if was_used else 0, feedback_score, key, journal.lower(), manuscript_id),
                )
                conn.commit()

    def get_recently_invited(self, days=60):
        from datetime import date, timedelta

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_profiles WHERE last_invited_date >= ? ORDER BY last_invited_date DESC",
                    (cutoff,),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def set_referee_note(self, name, note):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                cur = conn.execute(
                    "UPDATE referee_profiles SET notes=? WHERE referee_key=?", (note, key)
                )
                conn.commit()
                return cur.rowcount > 0

    def get_referee_note(self, name):
        key = normalize_name(name)
        with self._lock:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT notes FROM referee_profiles WHERE referee_key=?", (key,)
                ).fetchone()
                return row["notes"] if row else None

    def increment_reminder(self, referee_name, journal, manuscript_id):
        key = normalize_name(referee_name)
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "UPDATE referee_assignments SET reminders_received = reminders_received + 1 WHERE referee_key=? AND journal=? AND manuscript_id=?",
                    (key, journal.lower(), manuscript_id),
                )
                conn.commit()

    def compute_percentiles(self):
        with self._lock:
            with self._connection() as conn:
                profiles = conn.execute(
                    "SELECT referee_key, avg_response_days, avg_review_days, avg_report_quality FROM referee_profiles WHERE total_completed > 0"
                ).fetchall()
                if not profiles:
                    return
                response_vals = sorted(
                    [
                        (r["referee_key"], r["avg_response_days"])
                        for r in profiles
                        if r["avg_response_days"] is not None
                    ],
                    key=lambda x: x[1],
                )
                speed_vals = sorted(
                    [
                        (r["referee_key"], r["avg_review_days"])
                        for r in profiles
                        if r["avg_review_days"] is not None
                    ],
                    key=lambda x: x[1],
                )
                quality_vals = sorted(
                    [
                        (r["referee_key"], r["avg_report_quality"])
                        for r in profiles
                        if r["avg_report_quality"] is not None
                    ],
                    key=lambda x: x[1],
                )

                def _assign_percentiles(vals):
                    n = len(vals)
                    if n <= 1:
                        return {key: 50.0 for key, _ in vals}
                    result = {}
                    i = 0
                    while i < n:
                        j = i
                        while j < n and vals[j][1] == vals[i][1]:
                            j += 1
                        denom = max(n - 1, 1)
                        pct = round(((i + j - 1) / 2 / denom) * 100, 1)
                        for k in range(i, j):
                            result[vals[k][0]] = pct
                        i = j
                    return result

                resp_pct = _assign_percentiles(response_vals)
                speed_pct = _assign_percentiles(speed_vals)
                quality_pct = _assign_percentiles(quality_vals)
                for key in {p["referee_key"] for p in profiles}:
                    conn.execute(
                        "UPDATE referee_profiles SET percentile_response=?, percentile_speed=?, percentile_quality=? WHERE referee_key=?",
                        (resp_pct.get(key), speed_pct.get(key), quality_pct.get(key), key),
                    )
                conn.commit()

    def compute_all_journal_stats(self):
        with self._lock:
            with self._connection() as conn:
                keys = conn.execute(
                    "SELECT DISTINCT referee_key FROM referee_assignments"
                ).fetchall()
                for row in keys:
                    key = row["referee_key"]
                    assignments = conn.execute(
                        "SELECT * FROM referee_assignments WHERE referee_key=?", (key,)
                    ).fetchall()
                    self._update_journal_stats(conn, key, assignments)
                conn.commit()

    def get_top_referees_for_journal(self, journal, min_invitations=2, limit=10):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT rp.* FROM referee_profiles rp JOIN referee_journal_stats rjs ON rp.referee_key = rjs.referee_key WHERE rjs.journal = ? AND rjs.total_invitations >= ? AND rjs.total_completed > 0 ORDER BY rjs.avg_report_quality DESC, rjs.total_completed DESC LIMIT ?",
                    (journal.lower(), min_invitations, limit),
                ).fetchall()
                return [self._deserialize_profile(r) for r in rows]

    def get_journal_performance(self, journal):
        with self._lock:
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT AVG(days_to_complete) as avg_review_days, AVG(days_to_respond) as avg_response_days, SUM(CASE WHEN response='accepted' THEN 1 ELSE 0 END) * 1.0 / MAX(COUNT(*), 1) as acceptance_rate, SUM(was_overdue) * 1.0 / MAX(SUM(CASE WHEN returned_date IS NOT NULL THEN 1 ELSE 0 END), 1) as overdue_rate, COUNT(*) as total_assignments FROM referee_assignments WHERE journal = ?",
                    (journal.lower(),),
                ).fetchone()
                if row and row["total_assignments"] > 0:
                    return dict(row)
                return None

    def store_prediction(self, referee_name, journal, manuscript_id, p_accept):
        key = normalize_name(referee_name)
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO model_predictions (referee_key, journal, manuscript_id, predicted_p_accept, predicted_at) VALUES (?, ?, ?, ?, ?)",
                    (key, journal.lower(), manuscript_id, p_accept, datetime.now().isoformat()),
                )
                conn.commit()

    def _update_assignment_outcome(
        self, referee_key, journal, manuscript_id, response, returned_date
    ):
        with self._lock:
            with self._connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM referee_assignments WHERE referee_key = ? AND journal = ? AND manuscript_id = ?",
                    (referee_key, journal.lower(), manuscript_id),
                ).fetchone()
                if not existing:
                    return
                conn.execute(
                    "UPDATE referee_assignments SET response = ?, returned_date = ? WHERE referee_key = ? AND journal = ? AND manuscript_id = ?",
                    (response, returned_date, referee_key, journal.lower(), manuscript_id),
                )
                conn.commit()

    def resolve_predictions(self, journal=None):
        with self._lock:
            with self._connection() as conn:
                where = "WHERE resolved_at IS NULL"
                params = []
                if journal:
                    where += " AND journal = ?"
                    params.append(journal.lower())
                rows = conn.execute(
                    f"SELECT id, referee_key, journal, manuscript_id FROM model_predictions {where}",  # nosec B608
                    params,
                ).fetchall()  # nosec B608
                resolved = 0
                for row in rows:
                    asg = conn.execute(
                        "SELECT response, returned_date, days_to_complete FROM referee_assignments WHERE referee_key = ? AND journal = ? AND manuscript_id = ? ORDER BY created_at DESC LIMIT 1",
                        (row["referee_key"], row["journal"], row["manuscript_id"]),
                    ).fetchone()
                    if not asg or asg["response"] not in ("accepted", "declined"):
                        continue
                    actual_accepted = 1 if asg["response"] == "accepted" else 0
                    actual_completed = (
                        1 if asg["returned_date"] else (0 if actual_accepted == 1 else None)
                    )
                    conn.execute(
                        "UPDATE model_predictions SET actual_accepted = ?, actual_completed = ?, actual_review_days = ?, resolved_at = ? WHERE id = ?",
                        (
                            actual_accepted,
                            actual_completed,
                            asg["days_to_complete"],
                            datetime.now().isoformat(),
                            row["id"],
                        ),
                    )
                    resolved += 1
                conn.commit()
            return resolved

    def prediction_calibration(self):
        with self._lock:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT predicted_p_accept, actual_accepted FROM model_predictions WHERE resolved_at IS NOT NULL AND predicted_p_accept IS NOT NULL AND actual_accepted IS NOT NULL"
                ).fetchall()
        n = len(rows)
        if n == 0:
            return {"n_resolved": 0, "status": "no_data"}
        predictions = [r["predicted_p_accept"] for r in rows]
        actuals = [r["actual_accepted"] for r in rows]
        brier = sum((p - a) ** 2 for p, a in zip(predictions, actuals, strict=False)) / n
        base_rate = sum(actuals) / n
        brier_baseline = sum((base_rate - a) ** 2 for a in actuals) / n
        skill = 1 - brier / brier_baseline if brier_baseline > 0 else 0
        bins = [(0.0, 0.3, "low"), (0.3, 0.7, "mid"), (0.7, 1.001, "high")]
        calibration = []
        for lo, hi, label in bins:
            bucket = [(p, a) for p, a in zip(predictions, actuals, strict=False) if lo <= p < hi]
            if bucket:
                calibration.append(
                    {
                        "bin": label,
                        "n": len(bucket),
                        "mean_predicted": round(sum(p for p, _ in bucket) / len(bucket), 3),
                        "mean_actual": round(sum(a for _, a in bucket) / len(bucket), 3),
                    }
                )
        return {
            "n_resolved": n,
            "brier_score": round(brier, 4),
            "brier_skill": round(skill, 4),
            "base_acceptance_rate": round(base_rate, 3),
            "calibration": calibration,
            "status": "ok",
        }

    def _deserialize_profile(self, row):
        result = dict(row)
        for field in ("journals_served", "research_topics", "quality_trend", "response_trend"):
            try:
                result[field] = json.loads(result.get(field) or "[]")
            except (json.JSONDecodeError, TypeError):
                result[field] = []
        return result

    @staticmethod
    def _days_between(d1, d2):
        try:
            p1 = RefereeDB._parse_date(d1)
            p2 = RefereeDB._parse_date(d2)
            if p1 and p2:
                return (p2 - p1).days
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_date(d):
        if not d:
            return None
        d = d.strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(d, fmt).date()
            except (ValueError, TypeError):
                continue
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d").date()
        except Exception:
            return None
