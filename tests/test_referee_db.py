"""Tests for RefereeDB schema, methods, and learning features."""

import json
import sqlite3

import pytest
from pipeline.referee_db import RefereeDB


@pytest.fixture
def db(tmp_path):
    return RefereeDB(db_path=tmp_path / "test.db")


@pytest.fixture
def populated_db(db):
    db.record_assignment(
        "Alice Smith",
        "alice@mit.edu",
        "sicon",
        "M100",
        {
            "invited": "2025-01-01",
            "agreed": "2025-01-05",
            "due": "2025-03-01",
            "returned": "2025-02-20",
        },
        "Report Submitted",
        recommendation="Accept",
        institution="MIT",
        h_index=25,
        report_quality_score=4.2,
        report_word_count=800,
        reminders=0,
    )
    db.record_assignment(
        "Alice Smith",
        "alice@mit.edu",
        "sicon",
        "M200",
        {
            "invited": "2025-04-01",
            "agreed": "2025-04-03",
            "due": "2025-06-01",
            "returned": "2025-06-10",
        },
        "Report Submitted",
        recommendation="Minor Revision",
        institution="MIT",
        h_index=25,
        report_quality_score=3.8,
        report_word_count=600,
        reminders=1,
    )
    db.record_assignment(
        "Alice Smith",
        "alice@mit.edu",
        "mf",
        "MAFI-100",
        {
            "invited": "2025-07-01",
            "agreed": "2025-07-02",
            "due": "2025-09-01",
            "returned": "2025-08-20",
        },
        "Report Submitted",
        recommendation="Accept",
        institution="MIT",
        h_index=25,
        report_quality_score=4.5,
    )
    db.record_assignment(
        "Bob Jones",
        "bob@stanford.edu",
        "sicon",
        "M100",
        {"invited": "2025-01-01"},
        "Declined",
        institution="Stanford",
    )
    db.record_assignment(
        "Bob Jones",
        "bob@stanford.edu",
        "sicon",
        "M200",
        {"invited": "2025-04-01"},
        "Declined",
        institution="Stanford",
    )
    db.record_assignment(
        "Bob Jones",
        "bob@stanford.edu",
        "sicon",
        "M300",
        {"invited": "2025-07-01"},
        "Declined",
        institution="Stanford",
    )
    return db


class TestSchemaCreation:
    def test_tables_exist(self, db):
        conn = sqlite3.connect(str(db.db_path))
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        conn.close()
        assert "referee_profiles" in tables
        assert "referee_assignments" in tables
        assert "referee_journal_stats" in tables

    def test_profile_migration_columns(self, db):
        conn = sqlite3.connect(str(db.db_path))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(referee_profiles)").fetchall()}
        conn.close()
        assert "overdue_count" in cols
        assert "overdue_rate" in cols
        assert "quality_trend" in cols
        assert "response_trend" in cols
        assert "percentile_response" in cols
        assert "percentile_quality" in cols
        assert "percentile_speed" in cols

    def test_assignment_migration_columns(self, db):
        conn = sqlite3.connect(str(db.db_path))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(referee_assignments)").fetchall()}
        conn.close()
        assert "recommendation_used" in cols
        assert "feedback_score" in cols
        assert "reminder_effective" in cols

    def test_double_init_safe(self, tmp_path):
        db1 = RefereeDB(db_path=tmp_path / "test.db")
        db2 = RefereeDB(db_path=tmp_path / "test.db")
        assert db2 is not db1


class TestRecordAssignment:
    def test_basic_insert(self, db):
        db.record_assignment(
            "Test Ref",
            "test@test.com",
            "sicon",
            "M1",
            {"invited": "2025-01-01", "agreed": "2025-01-05"},
            "Agreed",
        )
        profile = db.get_profile("Test Ref")
        assert profile is not None
        assert profile["total_invitations"] == 1
        assert profile["total_accepted"] == 1

    def test_overdue_detection(self, db):
        db.record_assignment(
            "Late Ref",
            None,
            "mf",
            "M1",
            {
                "invited": "2025-01-01",
                "agreed": "2025-01-05",
                "due": "2025-03-01",
                "returned": "2025-03-15",
            },
            "Report Submitted",
        )
        profile = db.get_profile("Late Ref")
        assert profile["overdue_count"] == 1
        assert profile["overdue_rate"] == 1.0

    def test_decline_recorded(self, db):
        db.record_assignment("Decliner", None, "mf", "M1", {"invited": "2025-01-01"}, "Declined")
        profile = db.get_profile("Decliner")
        assert profile["total_declined"] == 1
        assert profile["total_accepted"] == 0


class TestJournalStats:
    def test_journal_stats_populated(self, populated_db):
        stats = populated_db.get_journal_stats("Alice Smith", "sicon")
        assert stats is not None
        assert stats["total_invitations"] == 2
        assert stats["total_completed"] == 2

    def test_journal_stats_different_journals(self, populated_db):
        sicon = populated_db.get_journal_stats("Alice Smith", "sicon")
        mf = populated_db.get_journal_stats("Alice Smith", "mf")
        assert sicon["total_invitations"] == 2
        assert mf["total_invitations"] == 1

    def test_journal_stats_missing(self, populated_db):
        assert populated_db.get_journal_stats("Alice Smith", "jota") is None


class TestTrackRecord:
    def test_full_track_record(self, populated_db):
        tr = populated_db.get_track_record("Alice Smith")
        assert tr["invitations"] == 3
        assert tr["acceptance_rate"] == 1.0
        assert tr["completion_rate"] == 1.0
        assert tr["avg_quality"] is not None
        assert tr["quality_trend"] is not None
        assert len(tr["quality_trend"]) == 3
        assert "overdue_rate" in tr

    def test_empty_track_record(self, db):
        assert db.get_track_record("Nobody") == {}


class TestOverdueOffenders:
    def test_finds_overdue_referees(self, db):
        for i in range(3):
            db.record_assignment(
                "Tardy Person",
                None,
                "sicon",
                f"M{i}",
                {
                    "invited": "2025-01-01",
                    "agreed": "2025-01-05",
                    "due": "2025-03-01",
                    "returned": "2025-03-15",
                },
                "Report Submitted",
            )
        offenders = db.get_overdue_repeat_offenders(min_overdue=2)
        assert len(offenders) >= 1
        assert offenders[0]["display_name"] == "Tardy Person"

    def test_no_offenders_when_on_time(self, populated_db):
        offenders = populated_db.get_overdue_repeat_offenders(min_overdue=3)
        assert len(offenders) == 0


class TestTopReferees:
    def test_returns_completed_referees(self, populated_db):
        top = populated_db.get_top_referees(min_invitations=1)
        names = [r["display_name"] for r in top]
        assert "Alice Smith" in names
        assert "Bob Jones" not in names

    def test_respects_min_invitations(self, populated_db):
        top = populated_db.get_top_referees(min_invitations=10)
        assert len(top) == 0


class TestChronicDecliners:
    def test_finds_decliners(self, populated_db):
        decliners = populated_db.get_chronic_decliners(min_invitations=3)
        names = [r["display_name"] for r in decliners]
        assert "Bob Jones" in names

    def test_good_referees_excluded(self, populated_db):
        decliners = populated_db.get_chronic_decliners(min_invitations=1)
        names = [r["display_name"] for r in decliners]
        assert "Alice Smith" not in names


class TestQualityTrend:
    def test_returns_recent_scores(self, populated_db):
        trend = populated_db.get_quality_trend("Alice Smith")
        assert len(trend) == 3
        assert all(isinstance(s, float) for s in trend)

    def test_empty_for_unknown(self, db):
        assert db.get_quality_trend("Nobody") == []


class TestAssignmentHistory:
    def test_returns_assignments(self, populated_db):
        assignments = populated_db.get_referee_assignments("Alice Smith")
        assert len(assignments) == 3

    def test_limit_works(self, populated_db):
        assignments = populated_db.get_referee_assignments("Alice Smith", limit=1)
        assert len(assignments) == 1


class TestSearchReferees:
    def test_search_by_name(self, populated_db):
        results = populated_db.search_referees("alice")
        assert len(results) == 1
        assert results[0]["display_name"] == "Alice Smith"

    def test_search_by_institution(self, populated_db):
        results = populated_db.search_referees("stanford")
        assert len(results) == 1
        assert results[0]["display_name"] == "Bob Jones"

    def test_search_by_email(self, populated_db):
        results = populated_db.search_referees("mit.edu")
        assert len(results) == 1

    def test_search_no_match(self, populated_db):
        assert populated_db.search_referees("zzzznotfound") == []


class TestRecordFeedback:
    def test_feedback_stored(self, populated_db):
        populated_db.record_feedback("Alice Smith", "sicon", "M100", True, 4.5)
        assignments = populated_db.get_referee_assignments("Alice Smith")
        sicon_m100 = [a for a in assignments if a["manuscript_id"] == "M100"][0]
        assert sicon_m100["recommendation_used"] == 1
        assert sicon_m100["feedback_score"] == 4.5


class TestPercentiles:
    def test_compute_percentiles(self, populated_db):
        populated_db.compute_percentiles()
        profile = populated_db.get_profile("Alice Smith")
        assert profile["percentile_quality"] is not None


class TestComputeAllJournalStats:
    def test_compute_all(self, populated_db):
        populated_db.compute_all_journal_stats()
        stats = populated_db.get_journal_stats("Alice Smith", "sicon")
        assert stats is not None
        assert stats["total_completed"] == 2
