#!/usr/bin/env python3
"""Lightweight dashboard API server.

Serves the static dashboard and provides API endpoints for triggering
actions from the dashboard UI.

Usage:
    python3 scripts/dashboard_server.py          # Start on port 8421
    python3 scripts/dashboard_server.py --port 9000
"""

import json
import re as _re
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "production" / "src"))

DASHBOARD_PATH = PROJECT_DIR / "production" / "outputs" / "dashboard.html"

app = Flask(__name__)

_SAFE_ID = _re.compile(r"^[\w\-.]+$")
VALID_JOURNALS = {"mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"}


def _validate_params(**kwargs):
    for _name, val in kwargs.items():
        if val and not _SAFE_ID.match(val):
            return False
    return True


@app.route("/")
def serve_dashboard():
    if DASHBOARD_PATH.exists():
        return send_file(DASHBOARD_PATH)
    return "Dashboard not generated yet. Run: python3 scripts/generate_dashboard.py", 404


@app.route("/api/ae-report", methods=["POST"])
def generate_ae_report():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    provider = data.get("provider", "claude")

    if not journal or not manuscript_id:
        return jsonify({"error": "journal and manuscript_id required"}), 400

    from pipeline.ae_report import generate

    result = generate(journal, manuscript_id, provider=provider)
    if result:
        return jsonify(result)
    return jsonify({"error": "Generation failed"}), 500


@app.route("/api/ae-reports/<journal>/<manuscript_id>")
def get_ae_report(journal, manuscript_id):
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400
    ae_dir = PROJECT_DIR / "production" / "outputs" / journal.lower() / "ae_reports"
    files = sorted(ae_dir.glob(f"ae_{manuscript_id}_*.json"), reverse=True)
    if not files:
        return jsonify({"error": "No AE report found"}), 404

    with open(files[0]) as f:
        return jsonify(json.load(f))


@app.route("/api/ae-report/paste", methods=["POST"])
def paste_ae_report():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    response_text = data.get("response", "")

    if not journal or not manuscript_id or not response_text:
        return jsonify({"error": "journal, manuscript_id, and response required"}), 400
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400

    ae_dir = PROJECT_DIR / "production" / "outputs" / journal / "ae_reports"
    files = sorted(ae_dir.glob(f"ae_{manuscript_id}_*.json"), reverse=True)
    if not files:
        return jsonify({"error": "No AE report found to update"}), 404

    report_path = files[0]
    with open(report_path) as f:
        report = json.load(f)

    json_match = _re.search(r"\{[\s\S]*\}", response_text)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            report.update(parsed)
        except json.JSONDecodeError:
            return jsonify({"error": "Could not parse JSON from response"}), 400
    else:
        return jsonify({"error": "No JSON found in response"}), 400

    report["status"] = "complete"
    report["provider"] = "clipboard_pasted"

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    return jsonify(report)


@app.route("/api/ae-list")
def list_ae_candidates():
    from pipeline.ae_report import find_manuscripts_needing_ae_report

    journal = request.args.get("journal")
    candidates = find_manuscripts_needing_ae_report(journal)
    return jsonify(candidates)


@app.route("/api/refresh-dashboard", methods=["POST"])
def refresh_dashboard():
    try:
        subprocess.run(
            [sys.executable, str(PROJECT_DIR / "scripts" / "generate_dashboard.py")],
            cwd=str(PROJECT_DIR),
            check=True,
            capture_output=True,
            timeout=30,
        )
        return jsonify({"status": "ok"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr.decode()[:500]}), 500


@app.route("/api/run-extraction", methods=["POST"])
def run_extraction():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    if not journal:
        return jsonify({"error": "journal required"}), 400

    def _run():
        env_vars = {
            "PYTHONUNBUFFERED": "1",
            "EXTRACTOR_HEADLESS": "false" if journal in ("sicon", "sifin") else "true",
        }
        import os

        env = {**os.environ, **env_vars}
        subprocess.run(
            [sys.executable, "run_extractors.py", "--journal", journal],
            cwd=str(PROJECT_DIR),
            env=env,
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "started", "journal": journal})


@app.route("/api/referee/search")
def search_referees():
    from pipeline.referee_db import RefereeDB

    q = request.args.get("q", "")
    if not q or len(q) < 2:
        return jsonify({"error": "query too short"}), 400
    db = RefereeDB()
    return jsonify(db.search_referees(q))


@app.route("/api/referee/top")
def get_top_referees():
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    return jsonify(db.get_top_referees(min_invitations=2, limit=20))


@app.route("/api/referee/decliners")
def get_chronic_decliners():
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    return jsonify(db.get_chronic_decliners(min_invitations=2))


@app.route("/api/referee/overdue")
def get_overdue_offenders():
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    return jsonify(db.get_overdue_repeat_offenders(min_overdue=2))


@app.route("/api/referee/<name>")
def get_referee_profile(name):
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    profile = db.get_profile(name)
    if profile:
        profile["assignments"] = db.get_referee_assignments(name, limit=10)
        return jsonify(profile)
    return jsonify({"error": "Referee not found"}), 404


@app.route("/api/referee/<name>/assignments")
def get_referee_assignments(name):
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    return jsonify(db.get_referee_assignments(name))


@app.route("/api/referee/<name>/journal-stats")
def get_referee_journal_stats(name):
    from pipeline import normalize_name
    from pipeline.referee_db import RefereeDB

    journal = request.args.get("journal")
    db = RefereeDB()
    if journal:
        stats = db.get_journal_stats(name, journal)
        return jsonify(stats or {})
    key = normalize_name(name)
    with db._lock:
        with db._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM referee_journal_stats WHERE referee_key=?",
                (key,),
            ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/pipeline/run", methods=["POST"])
def run_pipeline():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    if not journal or not manuscript_id:
        return jsonify({"error": "journal and manuscript_id required"}), 400

    def _run():
        try:
            from pipeline.referee_pipeline import RefereePipeline

            pipeline = RefereePipeline(use_llm=False)
            pipeline.run_single(journal, manuscript_id)
        except Exception as e:
            print(f"Pipeline error for {journal}/{manuscript_id}: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "started", "journal": journal, "manuscript_id": manuscript_id})


@app.route("/api/pipeline/recommendations/<journal>/<manuscript_id>")
def get_pipeline_recommendation(journal, manuscript_id):
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400
    rec_dir = PROJECT_DIR / "production" / "outputs" / journal.lower() / "recommendations"
    files = sorted(rec_dir.glob(f"rec_{manuscript_id}_*.json"), reverse=True)
    if not files:
        return jsonify({"error": "No recommendation found"}), 404
    with open(files[0]) as f:
        return jsonify(json.load(f))


@app.route("/api/manuscripts/search")
def search_manuscripts():
    q = (request.args.get("q", "") or "").lower()
    if not q or len(q) < 2:
        return jsonify({"error": "query too short"}), 400

    results = []
    outputs_dir = PROJECT_DIR / "production" / "outputs"
    for journal_dir in outputs_dir.iterdir():
        if not journal_dir.is_dir():
            continue
        journal = journal_dir.name
        files = sorted(journal_dir.glob(f"{journal}_extraction_*.json"))
        if not files:
            continue
        try:
            with open(files[-1]) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for ms in data.get("manuscripts", []):
            ms_id = ms.get("manuscript_id", "")
            title = ms.get("title", "")
            authors = ms.get("authors", [])
            authors_text = " ".join(
                a.get("name", "") if isinstance(a, dict) else str(a) for a in authors
            ).lower()
            if q in ms_id.lower() or q in title.lower() or q in authors_text:
                results.append(
                    {
                        "journal": journal.upper(),
                        "manuscript_id": ms_id,
                        "title": title,
                        "status": ms.get("status", ""),
                        "authors": [
                            a.get("name", "") if isinstance(a, dict) else str(a) for a in authors
                        ],
                    }
                )
    return jsonify(results)


@app.route("/api/events")
def get_events():
    from core.event_dispatcher import get_pending_events

    events = get_pending_events()
    return jsonify(events)


@app.route("/api/feedback", methods=["POST"])
def record_feedback():
    data = request.get_json() or {}
    referee_name = data.get("referee_name", "")
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    was_used = data.get("was_used")

    if not referee_name or not journal or not manuscript_id or was_used is None:
        return (
            jsonify({"error": "referee_name, journal, manuscript_id, and was_used required"}),
            400,
        )

    quality_score = data.get("quality_score")
    if quality_score is not None:
        try:
            quality_score = float(quality_score)
        except (ValueError, TypeError):
            return jsonify({"error": "quality_score must be a number"}), 400

    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    db.record_feedback(referee_name, journal, manuscript_id, bool(was_used), quality_score)
    return jsonify({"status": "ok"})


@app.route("/api/model-health")
def model_health():
    models_dir = PROJECT_DIR / "production" / "models"
    result = {}
    for name in ("training_metadata.json", "training_results.json"):
        path = models_dir / name
        if path.exists():
            try:
                with open(path) as f:
                    result[name.replace(".json", "")] = json.load(f)
            except (json.JSONDecodeError, OSError):
                result[name.replace(".json", "")] = None
        else:
            result[name.replace(".json", "")] = None
    return jsonify(result)


VALID_DECISIONS = {"accept", "minor_revision", "major_revision", "reject", "desk_reject"}
_NOTIFICATION_CONFIG_PATH = PROJECT_DIR / "production" / "cache" / "notification_config.json"
_REFEREE_NOTES_PATH = PROJECT_DIR / "production" / "cache" / "referee_notes.json"


@app.route("/api/record-decision", methods=["POST"])
def record_decision():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    decision = data.get("decision", "").lower()
    notes = data.get("notes", "")

    if not journal or not manuscript_id or not decision:
        return jsonify({"error": "journal, manuscript_id, and decision required"}), 400
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400
    if decision not in VALID_DECISIONS:
        return (
            jsonify(
                {"error": f"Invalid decision. Must be one of: {', '.join(sorted(VALID_DECISIONS))}"}
            ),
            400,
        )

    from pipeline.training import record_outcome

    record_outcome(journal, manuscript_id, decision)

    letters = {}
    try:
        from pipeline.decision_letters import draft_letters

        letters = draft_letters(journal, manuscript_id, decision, notes=notes)
    except ImportError:
        pass

    return jsonify({"status": "ok", "decision": decision, "letters": letters})


@app.route("/api/author-history/<name>")
def get_author_history(name):
    if not name or len(name) < 2:
        return jsonify({"error": "name too short"}), 400

    results = []
    outputs_dir = PROJECT_DIR / "production" / "outputs"
    name_lower = name.lower()
    for journal_dir in outputs_dir.iterdir():
        if not journal_dir.is_dir():
            continue
        journal = journal_dir.name
        if journal not in VALID_JOURNALS:
            continue
        files = sorted(journal_dir.glob(f"{journal}_extraction_*.json"))
        if not files:
            continue
        try:
            with open(files[-1]) as f:
                jdata = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for ms in jdata.get("manuscripts", []):
            authors = ms.get("authors", [])
            for a in authors:
                a_name = a.get("name", "") if isinstance(a, dict) else str(a)
                if name_lower in a_name.lower():
                    results.append(
                        {
                            "journal": journal.upper(),
                            "manuscript_id": ms.get("manuscript_id", ""),
                            "title": ms.get("title", ""),
                            "status": ms.get("status", ""),
                            "author_name": a_name,
                        }
                    )
                    break
    return jsonify(results)


@app.route("/api/notification-config", methods=["GET", "POST"])
def notification_config():
    if request.method == "GET":
        if _NOTIFICATION_CONFIG_PATH.exists():
            try:
                with open(_NOTIFICATION_CONFIG_PATH) as f:
                    return jsonify(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        return jsonify({"email_enabled": False, "email_address": "", "events": []})

    data = request.get_json() or {}
    _NOTIFICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_NOTIFICATION_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "ok"})


@app.route("/api/send-reminders", methods=["POST"])
def send_reminders():
    from reporting.action_items import compute_action_items

    items = compute_action_items()
    overdue = [i for i in items if i.action_type == "overdue_report"]

    sent = []
    for item in overdue:
        try:
            from core.email_notifications import send_reminder

            send_reminder(
                referee_name=item.referee_name,
                referee_email=item.referee_email,
                journal=item.journal,
                manuscript_id=item.manuscript_id,
                days_overdue=item.days_overdue,
            )
            item.reminders_sent += 1
            sent.append(
                {
                    "referee": item.referee_name,
                    "journal": item.journal,
                    "manuscript_id": item.manuscript_id,
                    "days_overdue": item.days_overdue,
                }
            )
        except Exception as e:
            sent.append(
                {
                    "referee": item.referee_name,
                    "error": str(e),
                }
            )

    return jsonify({"reminders_sent": len([s for s in sent if "error" not in s]), "details": sent})


@app.route("/api/referee/<name>/note", methods=["GET", "POST"])
def referee_note(name):
    if not name:
        return jsonify({"error": "name required"}), 400

    notes = {}
    if _REFEREE_NOTES_PATH.exists():
        try:
            with open(_REFEREE_NOTES_PATH) as f:
                notes = json.load(f)
        except (json.JSONDecodeError, OSError):
            notes = {}

    if request.method == "GET":
        return jsonify({"name": name, "note": notes.get(name, "")})

    data = request.get_json() or {}
    note_text = data.get("note", "")
    notes[name] = note_text
    _REFEREE_NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_REFEREE_NOTES_PATH, "w") as f:
        json.dump(notes, f, indent=2)
    return jsonify({"status": "ok", "name": name, "note": note_text})


@app.route("/api/annual-report", methods=["POST"])
def annual_report():
    data = request.get_json() or {}
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date required"}), 400

    try:
        from reporting.cross_journal_report import generate_cross_journal_report

        report = generate_cross_journal_report(start_date=start_date, end_date=end_date)
        return jsonify(report)
    except ImportError:
        return jsonify({"error": "cross_journal_report module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/similarity/<journal>/<manuscript_id>")
def get_similarity(journal, manuscript_id):
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400

    journal = journal.lower()
    outputs_dir = PROJECT_DIR / "production" / "outputs" / journal
    files = sorted(outputs_dir.glob(f"{journal}_extraction_*.json"))
    if not files:
        return jsonify({"error": "No extraction data found"}), 404

    try:
        with open(files[-1]) as f:
            jdata = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Failed to load extraction data"}), 500

    manuscript = None
    for ms in jdata.get("manuscripts", []):
        if ms.get("manuscript_id") == manuscript_id:
            manuscript = ms
            break
    if not manuscript:
        return jsonify({"error": "Manuscript not found"}), 404

    try:
        from pipeline.manuscript_similarity import find_similar_manuscripts

        similar = find_similar_manuscripts(
            manuscript.get("title", ""),
            manuscript.get("abstract", ""),
            top_k=5,
        )
        return jsonify(similar or [])
    except ImportError:
        return jsonify({"error": "manuscript_similarity module not available"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Dashboard API server")
    parser.add_argument("--port", type=int, default=8421)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"Dashboard server starting on http://{args.host}:{args.port}")
    print(f"Dashboard: {DASHBOARD_PATH}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
