#!/usr/bin/env python3
"""Send a weekly editorial digest email via Gmail API."""

import base64
import json
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
TOKEN_FILE = CONFIG_DIR / "gmail_token.json"
TOKEN_PICKLE = CONFIG_DIR / "gmail_token.pickle"

RECIPIENT = "dylan.possamai@math.ethz.ch"
SENDER = "dylansmb@gmail.com"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "production" / "src"))


def _get_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    elif TOKEN_PICKLE.exists():
        import pickle

        with open(TOKEN_PICKLE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Gmail credentials not valid. Run: python3 scripts/setup_gmail_oauth.py")
            sys.exit(1)

    return build("gmail", "v1", credentials=creds)


def _load_dashboard_data():
    from reporting.cross_journal_report import (
        JOURNAL_NAMES,
        JOURNALS,
        PLATFORMS,
        compute_journal_stats,
        load_journal_data,
    )

    stats = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data:
            stats.append(compute_journal_stats(journal, data))
        else:
            stats.append(
                {
                    "journal": journal.upper(),
                    "journal_name": JOURNAL_NAMES.get(journal, journal),
                    "platform": PLATFORMS.get(journal, ""),
                    "manuscripts": 0,
                    "referees": 0,
                    "authors": 0,
                    "enrichment_pct": 0,
                    "extraction_date": "",
                    "age_days": None,
                }
            )

    models_path = (
        Path(__file__).resolve().parent.parent / "production" / "models" / "training_metadata.json"
    )
    training = None
    if models_path.exists():
        try:
            with open(models_path) as f:
                training = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    feedback = None
    try:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        feedback = trainer.get_feedback_stats()
    except (ImportError, OSError):
        pass

    outputs_dir = Path(__file__).resolve().parent.parent / "production" / "outputs"
    rec_count = 0
    for journal in JOURNALS:
        rec_dir = outputs_dir / journal / "recommendations"
        if rec_dir.exists():
            rec_count += len(list(rec_dir.glob("rec_*.json")))

    return stats, training, feedback, rec_count


def _build_html_email(stats, training, feedback, rec_count):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_ms = sum(s["manuscripts"] for s in stats)
    total_refs = sum(s["referees"] for s in stats)
    active = sum(1 for s in stats if s["manuscripts"] > 0)

    rows = ""
    for s in stats:
        age = s.get("age_days")
        if age is None:
            freshness = '<span style="color:#9ca3af">No data</span>'
        elif age <= 7:
            freshness = f'<span style="color:#10b981">{age}d ago</span>'
        elif age <= 14:
            freshness = f'<span style="color:#f59e0b">{age}d ago</span>'
        else:
            freshness = f'<span style="color:#ef4444">{age}d ago</span>'

        rows += f"""<tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600">{s['journal']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{s.get('platform','')}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{s['manuscripts']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{s['referees']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{s.get('enrichment_pct',0):.0f}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:center">{freshness}</td>
        </tr>"""

    stale = [s for s in stats if s.get("age_days") and s["age_days"] > 7]
    alerts_html = ""
    if stale:
        names = ", ".join(s["journal"] for s in stale)
        alerts_html = f"""
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px 16px;margin-bottom:20px;color:#991b1b;font-size:14px">
            Stale data (&gt;7 days): {names}
        </div>"""

    training_html = ""
    if training:
        trained_at = training.get("trained_at", "?")[:16].replace("T", " ")
        ei = training.get("expertise_index", {})
        rp = training.get("response_predictor", {})
        training_html = f"""
        <div style="margin-top:20px">
            <h3 style="font-size:16px;margin-bottom:8px;color:#374151">ML Models</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr><td style="padding:4px 0;color:#6b7280">Last trained</td><td style="padding:4px 0;font-weight:600">{trained_at}</td></tr>
                <tr><td style="padding:4px 0;color:#6b7280">Expertise index</td><td style="padding:4px 0">{ei.get('n_referees',0)} referees</td></tr>
                <tr><td style="padding:4px 0;color:#6b7280">Response predictor</td><td style="padding:4px 0">{rp.get('cv_accuracy',0):.1%} accuracy ({rp.get('n_samples',0)} samples)</td></tr>
            </table>
        </div>"""

    feedback_html = ""
    if feedback:
        total_fb = sum(s["total"] for s in feedback.values())
        fb_rows = ""
        for j, s in sorted(feedback.items()):
            decisions = ", ".join(f"{k}: {v}" for k, v in s["decisions"].items())
            fb_rows += f"<tr><td style='padding:4px 8px'>{j.upper()}</td><td style='padding:4px 8px'>{s['total']}</td><td style='padding:4px 8px;color:#6b7280'>{decisions}</td></tr>"
        feedback_html = f"""
        <div style="margin-top:20px">
            <h3 style="font-size:16px;margin-bottom:8px;color:#374151">Feedback ({total_fb} outcomes)</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px">{fb_rows}</table>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:640px;margin:0 auto;padding:20px;color:#1f2937;line-height:1.6">

<div style="text-align:center;padding:24px 0;border-bottom:2px solid #e5e7eb;margin-bottom:24px">
    <h1 style="font-size:22px;font-weight:700;margin:0;color:#111827">Editorial Weekly Digest</h1>
    <p style="color:#6b7280;font-size:14px;margin:4px 0 0">{now}</p>
</div>

<div style="display:flex;gap:16px;margin-bottom:20px;text-align:center;flex-wrap:wrap">
    <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:12px;min-width:120px">
        <div style="font-size:24px;font-weight:700;color:#4361ee">{active}/{len(stats)}</div>
        <div style="font-size:12px;color:#6b7280">Journals Active</div>
    </div>
    <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:12px;min-width:120px">
        <div style="font-size:24px;font-weight:700;color:#4361ee">{total_ms}</div>
        <div style="font-size:12px;color:#6b7280">Manuscripts</div>
    </div>
    <div style="flex:1;background:#f3f4f6;border-radius:8px;padding:12px;min-width:120px">
        <div style="font-size:24px;font-weight:700;color:#4361ee">{total_refs}</div>
        <div style="font-size:12px;color:#6b7280">Referees</div>
    </div>
</div>

{alerts_html}

<h3 style="font-size:16px;margin-bottom:8px;color:#374151">Journal Status</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
    <thead>
        <tr style="background:#f9fafb">
            <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">Journal</th>
            <th style="padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">Platform</th>
            <th style="padding:8px 12px;text-align:center;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">MSS</th>
            <th style="padding:8px 12px;text-align:center;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">Refs</th>
            <th style="padding:8px 12px;text-align:center;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">Enrich</th>
            <th style="padding:8px 12px;text-align:center;font-size:11px;text-transform:uppercase;color:#6b7280;border-bottom:2px solid #e5e7eb">Fresh</th>
        </tr>
    </thead>
    <tbody>{rows}</tbody>
</table>

{training_html}
{feedback_html}

<div style="text-align:center;padding:20px 0;margin-top:24px;border-top:1px solid #e5e7eb;color:#9ca3af;font-size:12px">
    {rec_count} pipeline recommendations generated &middot; editorial-scripts
</div>

</body>
</html>"""


def main():
    print("Building digest data...")
    stats, training, feedback, rec_count = _load_dashboard_data()

    print("Composing email...")
    html = _build_html_email(stats, training, feedback, rec_count)

    total_ms = sum(s["manuscripts"] for s in stats)
    subject = f"Editorial Digest — {datetime.now().strftime('%b %d')} — {total_ms} manuscripts"

    message = MIMEText(html, "html")
    message["to"] = RECIPIENT
    message["from"] = SENDER
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    print(f"Sending to {RECIPIENT}...")
    service = _get_gmail_service()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Digest sent: {subject}")


if __name__ == "__main__":
    main()
