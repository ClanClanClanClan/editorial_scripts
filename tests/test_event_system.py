"""Tests for the event system: state_store, event_dispatcher, event_processor."""

import json
import sqlite3
from unittest.mock import MagicMock, call, patch

import pytest
from core.event_dispatcher import get_pending_events, mark_processed, process_extraction
from core.state_store import StateStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ms(ms_id, status="Under Review", referees=None):
    return {"manuscript_id": ms_id, "status": status, "referees": referees or []}


def _ref(name, status="Awaiting Report", recommendation="", review_received=False, comments=""):
    ref = {"name": name, "status": status, "recommendation": recommendation}
    if review_received:
        ref["status_details"] = {"review_received": True}
    if comments:
        ref["report"] = {"comments_to_author": comments}
    return ref


def _completed_ref(name, rec="Accept"):
    return _ref(name, status="Review Complete", recommendation=rec)


def _declined_ref(name):
    return _ref(name, status="Declined")


# ---------------------------------------------------------------------------
# StateStore tests
# ---------------------------------------------------------------------------


class TestStateStoreInit:
    def test_creates_db_file(self, tmp_path):
        db = tmp_path / "sub" / "state.db"
        StateStore(db_path=db)
        assert db.exists()

    def test_creates_table(self, tmp_path):
        db = tmp_path / "state.db"
        StateStore(db_path=db)
        conn = sqlite3.connect(str(db))
        tables = [
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        conn.close()
        assert "manuscript_state" in tables


class TestComputeHash:
    def test_deterministic(self):
        ms = _ms("X-1", referees=[_ref("Alice")])
        h1 = StateStore._compute_hash(ms, "mf")
        h2 = StateStore._compute_hash(ms, "mf")
        assert h1 == h2

    def test_differs_on_status_change(self):
        ms1 = _ms("X-1", status="Under Review")
        ms2 = _ms("X-1", status="Decision Pending")
        assert StateStore._compute_hash(ms1, "mf") != StateStore._compute_hash(ms2, "mf")

    def test_differs_on_referee_change(self):
        ms1 = _ms("X-1", referees=[_ref("Alice", status="Awaiting Report")])
        ms2 = _ms("X-1", referees=[_ref("Alice", status="Review Complete")])
        assert StateStore._compute_hash(ms1, "mf") != StateStore._compute_hash(ms2, "mf")

    def test_empty_manuscript(self):
        h = StateStore._compute_hash({}, "mf")
        assert isinstance(h, str) and len(h) == 32


class TestGetState:
    def test_returns_none_for_unknown(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        assert store.get_state("NOPE", "mf") is None

    def test_returns_dict_after_insert(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1"), "mf")
        state = store.get_state("X-1", "mf")
        assert state is not None
        assert state["manuscript_id"] == "X-1"
        assert state["journal"] == "mf"


class TestUpdateState:
    def test_no_manuscript_id_returns_none(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        assert store.update_state({"status": "foo"}, "mf") is None

    def test_new_manuscript_event(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        event = store.update_state(_ms("X-1"), "mf")
        assert event == {"type": "NEW_MANUSCRIPT", "manuscript_id": "X-1", "journal": "mf"}

    def test_no_change_returns_none(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        ms = _ms("X-1", referees=[_ref("Alice")])
        store.update_state(ms, "mf")
        assert store.update_state(ms, "mf") is None

    def test_status_changed_event(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1", status="Under Review"), "mf")
        event = store.update_state(_ms("X-1", status="Decision Pending"), "mf")
        assert event["type"] == "STATUS_CHANGED"
        assert event["changes"]["new_status"] == "Decision Pending"
        assert event["changes"]["old_status"] == "Under Review"

    def test_all_reports_in_event(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1", referees=[_ref("Alice"), _ref("Bob")]), "mf")
        event = store.update_state(
            _ms("X-1", referees=[_completed_ref("Alice"), _completed_ref("Bob")]), "mf"
        )
        assert event["type"] == "ALL_REPORTS_IN"
        assert event["completed"] == 2

    def test_all_reports_in_needs_at_least_two(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1", referees=[_ref("Alice")]), "mf")
        event = store.update_state(_ms("X-1", referees=[_completed_ref("Alice")]), "mf")
        assert event["type"] == "STATUS_CHANGED"

    def test_new_reports_in_changes(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1", referees=[_ref("Alice"), _ref("Bob"), _ref("Carol")]), "mf")
        event = store.update_state(
            _ms("X-1", referees=[_completed_ref("Alice"), _ref("Bob"), _ref("Carol")]), "mf"
        )
        assert event["type"] == "STATUS_CHANGED"
        assert event["changes"]["new_reports"] == 1

    def test_declined_referees_dont_block_all_reports_in(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1", referees=[_ref("A"), _ref("B"), _ref("C")]), "mf")
        event = store.update_state(
            _ms("X-1", referees=[_completed_ref("A"), _completed_ref("B"), _declined_ref("C")]),
            "mf",
        )
        assert event["type"] == "ALL_REPORTS_IN"

    def test_journals_are_independent(self, tmp_path):
        store = StateStore(db_path=tmp_path / "state.db")
        store.update_state(_ms("X-1"), "mf")
        event = store.update_state(_ms("X-1"), "mor")
        assert event["type"] == "NEW_MANUSCRIPT"


# ---------------------------------------------------------------------------
# EventDispatcher tests
# ---------------------------------------------------------------------------


class TestProcessExtraction:
    def test_emits_events_to_pending_file(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        db = tmp_path / "state.db"
        written = []

        def fake_append(event, path=None):
            pending.parent.mkdir(parents=True, exist_ok=True)
            with open(pending, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
            written.append(event)

        with (
            patch("core.event_dispatcher._append_event", side_effect=fake_append),
            patch("core.event_dispatcher.StateStore", lambda: StateStore(db_path=db)),
        ):
            data = {"manuscripts": [_ms("X-1"), _ms("X-2")]}
            events = process_extraction(data, "mf")

        assert len(events) == 2
        assert all(e["type"] == "NEW_MANUSCRIPT" for e in events)
        lines = [x for x in pending.read_text().strip().split("\n") if x.strip()]
        assert len(lines) == 2

    def test_skips_empty_manuscript_id(self, tmp_path):
        db = tmp_path / "state.db"

        with (
            patch("core.event_dispatcher._append_event"),
            patch("core.event_dispatcher.StateStore", lambda: StateStore(db_path=db)),
        ):
            data = {"manuscripts": [{"status": "X"}]}
            events = process_extraction(data, "mf")

        assert events == []

    def test_no_events_for_unchanged(self, tmp_path):
        db = tmp_path / "state.db"

        with (
            patch("core.event_dispatcher._append_event"),
            patch("core.event_dispatcher.StateStore", lambda: StateStore(db_path=db)),
        ):
            data = {"manuscripts": [_ms("X-1")]}
            process_extraction(data, "mf")
            events = process_extraction(data, "mf")

        assert events == []


class TestGetPendingEvents:
    def test_returns_empty_when_no_file(self, tmp_path):
        with patch("core.event_dispatcher.PENDING_FILE", tmp_path / "nope.jsonl"):
            assert get_pending_events() == []

    def test_reads_jsonl(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        pending.write_text(json.dumps({"type": "NEW_MANUSCRIPT", "manuscript_id": "X-1"}) + "\n")
        with patch("core.event_dispatcher.PENDING_FILE", pending):
            events = get_pending_events()
        assert len(events) == 1
        assert events[0]["manuscript_id"] == "X-1"

    def test_skips_bad_json(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        pending.write_text('{"good": true}\nBADLINE\n{"also": "good"}\n')
        with patch("core.event_dispatcher.PENDING_FILE", pending):
            events = get_pending_events()
        assert len(events) == 2


class TestMarkProcessed:
    def test_moves_events_to_processed(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        processed = tmp_path / "processed.jsonl"
        event = {
            "type": "NEW_MANUSCRIPT",
            "manuscript_id": "X-1",
            "journal": "mf",
            "timestamp": "T1",
        }
        pending.write_text(json.dumps(event) + "\n")

        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", processed),
        ):
            mark_processed([event])

        assert processed.exists()
        proc_events = [
            json.loads(x) for x in processed.read_text().strip().split("\n") if x.strip()
        ]
        assert len(proc_events) == 1
        assert proc_events[0]["processed_at"]
        remaining = pending.read_text().strip()
        assert remaining == ""

    def test_keeps_unprocessed_events(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        processed = tmp_path / "processed.jsonl"
        ev1 = {"type": "NEW_MANUSCRIPT", "manuscript_id": "X-1", "journal": "mf", "timestamp": "T1"}
        ev2 = {"type": "STATUS_CHANGED", "manuscript_id": "X-2", "journal": "mf", "timestamp": "T2"}
        pending.write_text(json.dumps(ev1) + "\n" + json.dumps(ev2) + "\n")

        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", processed),
        ):
            mark_processed([ev1])

        remaining = [json.loads(x) for x in pending.read_text().strip().split("\n") if x.strip()]
        assert len(remaining) == 1
        assert remaining[0]["manuscript_id"] == "X-2"


# ---------------------------------------------------------------------------
# EventProcessor tests
# ---------------------------------------------------------------------------


class TestProcessAll:
    def _write_pending(self, path, events):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(e, default=str) for e in events) + "\n")

    def test_no_events(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", tmp_path / "processed.jsonl"),
        ):
            from core.event_processor import process_all

            result = process_all()
        assert result == []

    def test_all_reports_in_triggers_ae_report(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        processed = tmp_path / "processed.jsonl"
        event = {
            "type": "ALL_REPORTS_IN",
            "manuscript_id": "X-1",
            "journal": "sicon",
            "timestamp": "T1",
            "completed": 2,
        }
        self._write_pending(pending, [event])

        mock_generate = MagicMock(return_value={"recommendation": "Accept"})

        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", processed),
            patch("core.event_processor.get_pending_events") as mock_get,
            patch("core.event_processor.mark_processed") as _mock_mark,  # noqa: F841
            patch.dict("sys.modules", {"pipeline.ae_report": MagicMock(generate=mock_generate)}),
        ):
            mock_get.return_value = [event]
            from core.event_processor import process_all

            result = process_all(provider="claude")

        mock_generate.assert_called_once_with("sicon", "X-1", provider="claude")
        assert len(result) == 1

    def test_new_manuscript_triggers_pipeline(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        processed = tmp_path / "processed.jsonl"
        event = {
            "type": "NEW_MANUSCRIPT",
            "manuscript_id": "X-1",
            "journal": "mf",
            "timestamp": "T1",
        }
        self._write_pending(pending, [event])

        mock_pipeline_cls = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline_instance

        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", processed),
            patch("core.event_processor.get_pending_events") as mock_get,
            patch("core.event_processor.mark_processed") as _mock_mark,  # noqa: F841
            patch.dict(
                "sys.modules",
                {"pipeline.referee_pipeline": MagicMock(RefereePipeline=mock_pipeline_cls)},
            ),
        ):
            mock_get.return_value = [event]
            from core.event_processor import process_all

            result = process_all()

        mock_pipeline_cls.assert_called_once_with(use_llm=False)
        mock_pipeline_instance.run_single.assert_called_once_with("mf", "X-1", extraction_path=None)
        assert len(result) == 1

    def test_marks_all_processed(self, tmp_path):
        pending = tmp_path / "pending.jsonl"
        processed = tmp_path / "processed.jsonl"
        events = [
            {
                "type": "STATUS_CHANGED",
                "manuscript_id": "X-1",
                "journal": "mf",
                "timestamp": "T1",
                "changes": {},
            },
            {
                "type": "STATUS_CHANGED",
                "manuscript_id": "X-2",
                "journal": "mf",
                "timestamp": "T2",
                "changes": {},
            },
        ]
        self._write_pending(pending, events)

        with (
            patch("core.event_dispatcher.PENDING_FILE", pending),
            patch("core.event_dispatcher.PROCESSED_FILE", processed),
            patch("core.event_processor.get_pending_events") as mock_get,
            patch("core.event_processor.mark_processed") as _mock_mark,  # noqa: F841
        ):
            mock_get.return_value = events
            from core.event_processor import process_all

            process_all()
        assert len(_mock_mark.call_args[0][0]) == 2
