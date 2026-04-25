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

_SAFE_ID = _re.compile(r"^[\w\-.]+$")
_SAFE_NAME = _re.compile(r"^[\w\s,.\-']+$")
VALID_JOURNALS = {"mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco", "mf_wiley"}

app = Flask(__name__)


def _validate_params(**kwargs):
    for _name, val in kwargs.items():
        if not val:
            continue
        pattern = _SAFE_NAME if _name == "name" else _SAFE_ID
        if not pattern.match(val):
            return False
    return True


@app.route("/")
def serve_dashboard():
    if DASHBOARD_PATH.exists():
        return send_file(DASHBOARD_PATH)
    return "Dashboard not generated yet. Run: python3 scripts/generate_dashboard.py", 404


@app.route("/api/ae-report", methods=["POST"])
def generate_ae_report():
    import os

    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    provider = data.get("provider")
    if not provider:
        provider = "claude" if os.environ.get("ANTHROPIC_API_KEY") else "prompt"

    if not journal or not manuscript_id:
        return jsonify({"error": "journal and manuscript_id required"}), 400
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400

    from pipeline.ae_report import generate

    result = generate(journal, manuscript_id, provider=provider)
    if result:
        return jsonify(result)
    return jsonify({"error": "Generation failed"}), 500


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

    parsed = None
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        json_match = _re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    if not parsed:
        return jsonify({"error": "Could not parse JSON from response"}), 400

    ae_dir = PROJECT_DIR / "production" / "outputs" / journal / "ae_reports"
    ae_dir.mkdir(parents=True, exist_ok=True)

    existing_files = sorted(ae_dir.glob(f"ae_{manuscript_id}_*.json"), reverse=True)
    if existing_files:
        try:
            with open(existing_files[0]) as f:
                existing = json.load(f)
            existing.update(parsed)
            parsed = existing
        except (json.JSONDecodeError, OSError):
            pass

    import datetime

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ae_dir / f"ae_{manuscript_id}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(parsed, f, indent=2, default=str)

    return jsonify({"status": "ok", "path": str(out_path), "report": parsed})


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
    if not _validate_params(journal=journal):
        return jsonify({"error": "Invalid journal parameter"}), 400

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
            timeout=600,
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "started", "journal": journal})


@app.route("/api/referee/search")
def search_referees():
    q = request.args.get("q", "")
    if not q or len(q) < 2:
        return jsonify({"error": "query too short"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return jsonify(db.search_referees(q))
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/top")
def get_top_referees():
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return jsonify(db.get_top_referees(min_invitations=2, limit=20))
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/decliners")
def get_chronic_decliners():
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return jsonify(db.get_chronic_decliners(min_invitations=2))
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/overdue")
def get_overdue_offenders():
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return jsonify(db.get_overdue_repeat_offenders(min_overdue=2))
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/<name>")
def get_referee_profile(name):
    if not _validate_params(name=name):
        return jsonify({"error": "Invalid name parameter"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        profile = db.get_profile(name)
        if profile:
            profile["assignments"] = db.get_referee_assignments(name, limit=10)
            return jsonify(profile)
        return jsonify({"error": "Referee not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/<name>/assignments")
def get_referee_assignments(name):
    if not _validate_params(name=name):
        return jsonify({"error": "Invalid name parameter"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return jsonify(db.get_referee_assignments(name))
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/<name>/journal-stats")
def get_referee_journal_stats(name):
    if not _validate_params(name=name):
        return jsonify({"error": "Invalid name parameter"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        journal = request.args.get("journal")
        if journal and not _validate_params(journal=journal):
            return jsonify({"error": "Invalid journal parameter"}), 400
        db = RefereeDB()
        if journal:
            stats = db.get_journal_stats(name, journal)
            return jsonify(stats or {})
        from pipeline import normalize_name_orderless

        key = normalize_name_orderless(name)
        with db._lock:
            with db._connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM referee_journal_stats WHERE referee_key=?",
                    (key,),
                ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/referee/<name>/note", methods=["GET", "POST"])
def referee_note(name):
    if not _validate_params(name=name):
        return jsonify({"error": "Invalid name parameter"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        if request.method == "POST":
            data = request.get_json() or {}
            note = data.get("note", "")
            db.set_referee_note(name, note)
            return jsonify({"status": "ok"})
        note = db.get_referee_note(name)
        return jsonify({"note": note or ""})
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500


@app.route("/api/pipeline/run", methods=["POST"])
def run_pipeline():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    if not journal or not manuscript_id:
        return jsonify({"error": "journal and manuscript_id required"}), 400
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400

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
            if q in ms_id.lower() or q in title.lower():
                results.append(
                    {
                        "journal": journal.upper(),
                        "manuscript_id": ms_id,
                        "title": title,
                        "status": ms.get("status", ""),
                    }
                )
    return jsonify(results)


@app.route("/api/events")
def get_events():
    from core.event_dispatcher import get_pending_events

    events = get_pending_events()
    return jsonify(events)


@app.route("/api/record-decision", methods=["POST"])
def record_decision():
    data = request.get_json() or {}
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    decision = data.get("decision", "")
    notes = data.get("notes", "")
    if not journal or not manuscript_id or not decision:
        return jsonify({"error": "journal, manuscript_id, and decision required"}), 400
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400
    valid = {"accept", "minor_revision", "major_revision", "reject", "desk_reject"}
    if decision.lower() not in valid:
        return jsonify({"error": f"Invalid decision. Must be one of: {valid}"}), 400
    try:
        from pipeline.decision_letters import draft_letters

        result = draft_letters(journal, manuscript_id, decision.replace("_", " ").title(), notes)
        return jsonify({"status": "ok", "letters": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/author-history/<name>")
def get_author_history(name):
    if len(name) < 2:
        return jsonify({"error": "Name too short"}), 400
    from reporting.cross_journal_report import find_author_across_journals

    results = find_author_across_journals(name)
    return jsonify(results)


@app.route("/api/notification-config", methods=["GET", "POST"])
def notification_config():
    from core.email_notifications import _load_config, _save_config

    if request.method == "POST":
        data = request.get_json() or {}
        config = _load_config()
        config.update(data)
        _save_config(config)
        return jsonify({"status": "ok"})
    return jsonify(_load_config())


@app.route("/api/send-reminders", methods=["POST"])
def send_reminders():
    from reporting.action_items import compute_action_items

    items = compute_action_items()
    overdue = [i for i in items if i.action_type == "overdue_report" and i.referee_email]
    sent = 0
    failed = 0
    for item in overdue:
        try:
            from core.email_notifications import send_notification

            subject = f"Reminder: Review for {item.manuscript_id} ({item.journal})"
            body = (
                f"Dear {item.referee_name},\n\n"
                f"This is a gentle reminder regarding your review of {item.manuscript_id}.\n"
                f"The report was due {item.days_overdue} days ago.\n\n"
                f"Best regards"
            )
            if send_notification(subject, body, item.referee_email):
                from pipeline.referee_db import RefereeDB

                RefereeDB().increment_reminder(
                    item.referee_name,
                    item.journal.lower(),
                    item.manuscript_id,
                )
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return jsonify({"status": "ok", "reminders_sent": sent, "reminders_failed": failed})


@app.route("/api/annual-report", methods=["POST"])
def annual_report():
    data = request.get_json() or {}
    start = data.get("start_date", "")
    end = data.get("end_date", "")
    if not start or not end:
        return jsonify({"error": "start_date and end_date required"}), 400
    try:
        from reporting.annual_report import generate_annual_report

        report = generate_annual_report(start, end)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/similarity/<journal>/<manuscript_id>")
def get_similarity(journal, manuscript_id):
    if not _validate_params(journal=journal, manuscript_id=manuscript_id):
        return jsonify({"error": "Invalid parameters"}), 400
    outputs_dir = PROJECT_DIR / "production" / "outputs"
    journal_dir = outputs_dir / journal.lower()
    files = (
        sorted(journal_dir.glob(f"{journal.lower()}_extraction_*.json"))
        if journal_dir.exists()
        else []
    )
    if not files:
        return jsonify({"error": "No extraction data"}), 404
    try:
        with open(files[-1]) as f:
            data = json.load(f)
        ms = None
        for m in data.get("manuscripts", []):
            if m.get("manuscript_id") == manuscript_id:
                ms = m
                break
        if not ms:
            return jsonify({"error": "Manuscript not found"}), 404
        from pipeline.manuscript_similarity import find_similar_manuscripts

        results = find_similar_manuscripts(ms.get("title", ""), ms.get("abstract", ""))
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def record_feedback():
    data = request.get_json() or {}
    referee_name = data.get("referee_name", "")
    journal = data.get("journal", "").lower()
    manuscript_id = data.get("manuscript_id", "")
    was_used = data.get("was_used", False)
    quality_score = data.get("quality_score")
    if not referee_name or not journal or not manuscript_id:
        return jsonify({"error": "referee_name, journal, and manuscript_id required"}), 400
    try:
        if quality_score is not None:
            quality_score = float(quality_score)
    except (ValueError, TypeError):
        return jsonify({"error": "quality_score must be a number"}), 400
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        db.record_feedback(referee_name, journal, manuscript_id, was_used, quality_score)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/model-health")
def model_health():
    models_dir = PROJECT_DIR / "production" / "models"
    health = {}
    for name in ("response_predictor.joblib", "outcome_predictor.joblib"):
        p = models_dir / name
        health[name] = {
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
            "modified": p.stat().st_mtime if p.exists() else None,
        }
    faiss_path = models_dir / "referee_index.faiss"
    health["referee_index.faiss"] = {
        "exists": faiss_path.exists(),
        "size_bytes": faiss_path.stat().st_size if faiss_path.exists() else 0,
        "modified": faiss_path.stat().st_mtime if faiss_path.exists() else None,
    }
    meta_path = models_dir / "training_metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                health["training_metadata"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            health["training_metadata"] = None
    else:
        health["training_metadata"] = None
    return jsonify(health)


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
