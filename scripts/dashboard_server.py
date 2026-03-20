#!/usr/bin/env python3
"""Lightweight dashboard API server.

Serves the static dashboard and provides API endpoints for triggering
actions from the dashboard UI.

Usage:
    python3 scripts/dashboard_server.py          # Start on port 8421
    python3 scripts/dashboard_server.py --port 9000
"""

import json
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_file

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "production" / "src"))

DASHBOARD_PATH = PROJECT_DIR / "production" / "outputs" / "dashboard.html"

app = Flask(__name__)


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


@app.route("/api/referee/<name>")
def get_referee_profile(name):
    from pipeline.referee_db import RefereeDB

    db = RefereeDB()
    profile = db.get_profile(name)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "Referee not found"}), 404


@app.route("/api/events")
def get_events():
    from core.event_dispatcher import get_pending_events

    events = get_pending_events()
    return jsonify(events)


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
