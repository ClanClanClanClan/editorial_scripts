"""Email notifications for editorial events."""

import base64
import json
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
CONFIG_PATH = CONFIG_DIR / "notification_prefs.json"
TOKEN_FILE = CONFIG_DIR / "gmail_token.json"
TOKEN_PICKLE = CONFIG_DIR / "gmail_token.pickle"

SENDER = "dylansmb@gmail.com"
DEFAULT_RECIPIENT = "dylan.possamai@math.ethz.ch"

EVENT_EMAIL_DEFAULTS = {
    "ALL_REPORTS_IN": True,
    "NEW_MANUSCRIPT": True,
    "STATUS_CHANGED": False,
    "OVERDUE_REMINDER": True,
}


def _load_config():
    config = dict(EVENT_EMAIL_DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return config


def _save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _get_gmail_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return None

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    elif TOKEN_PICKLE.exists():
        import pickle

        with open(TOKEN_PICKLE, "rb") as f:
            creds = pickle.load(f)  # nosec B301 — local OAuth token, not untrusted data

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                return None
        else:
            return None

    return build("gmail", "v1", credentials=creds)


def send_notification(subject, body, to_email=None):
    service = _get_gmail_service()
    if service is None:
        return False

    to = to_email or DEFAULT_RECIPIENT
    message = MIMEText(body, "html")
    message["to"] = to
    message["from"] = SENDER
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception as e:
        print(f"Email send failed: {e}", file=sys.stderr)
        return False


def _journal_label(journal_code: str) -> str:
    """Short subject-line label. Prefers a human-readable name from
    JOURNAL_NAME_MAP, falling back to the raw code. Strips noisy variants
    (e.g. MF_WILEY → "Mathematical Finance" but kept compact in subjects).
    """
    if not journal_code:
        return ""
    code = journal_code.upper()
    try:
        from core.output_schema import JOURNAL_NAME_MAP

        full = JOURNAL_NAME_MAP.get(code)
        if full:
            return full
    except Exception:
        pass
    return code


def format_event_email(event):
    event_type = event.get("type", "UNKNOWN")
    raw_journal = event.get("journal", "").upper()
    journal = _journal_label(raw_journal)
    ms_id = event.get("manuscript_id", "")
    timestamp = event.get("timestamp", datetime.now().isoformat())

    if event_type == "ALL_REPORTS_IN":
        subject = f"[{journal}] All reports in — {ms_id}"
        body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#10b981">All Referee Reports Received</h2>
<table style="font-size:14px;border-collapse:collapse">
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Journal</td><td style="font-weight:600">{journal}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Manuscript</td><td style="font-weight:600">{ms_id}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Time</td><td>{timestamp}</td></tr>
</table>
<p style="margin-top:16px;color:#374151">An AE recommendation report will be generated automatically. Check the dashboard for details.</p>
</div>"""

    elif event_type == "NEW_MANUSCRIPT":
        subject = f"[{journal}] New manuscript — {ms_id}"
        body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#4361ee">New Manuscript Submitted</h2>
<table style="font-size:14px;border-collapse:collapse">
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Journal</td><td style="font-weight:600">{journal}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Manuscript</td><td style="font-weight:600">{ms_id}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Time</td><td>{timestamp}</td></tr>
</table>
<p style="margin-top:16px;color:#374151">The referee recommendation pipeline has been triggered. Candidates will appear on the dashboard shortly.</p>
</div>"""

    elif event_type == "STATUS_CHANGED":
        details = event.get("details", "")
        subject = f"[{journal}] Status changed — {ms_id}"
        body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#f59e0b">Manuscript Status Changed</h2>
<table style="font-size:14px;border-collapse:collapse">
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Journal</td><td style="font-weight:600">{journal}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Manuscript</td><td style="font-weight:600">{ms_id}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Time</td><td>{timestamp}</td></tr>
{f'<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Details</td><td>{details}</td></tr>' if details else ''}
</table>
</div>"""

    elif event_type == "OVERDUE_REMINDER":
        referee = event.get("referee", "Unknown")
        days_overdue = event.get("days_overdue", 0)
        subject = f"[{journal}] Overdue review — {ms_id} ({referee})"
        body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#ef4444">Overdue Referee Report</h2>
<table style="font-size:14px;border-collapse:collapse">
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Journal</td><td style="font-weight:600">{journal}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Manuscript</td><td style="font-weight:600">{ms_id}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Referee</td><td style="font-weight:600">{referee}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280">Days overdue</td><td style="color:#ef4444;font-weight:600">{days_overdue}</td></tr>
</table>
</div>"""

    else:
        subject = f"[{journal}] {event_type} — {ms_id}"
        body = f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2>Editorial Event</h2>
<pre style="background:#f3f4f6;padding:12px;border-radius:6px;font-size:13px">{json.dumps(event, indent=2, default=str)}</pre>
</div>"""

    return subject, body


def verify_send_scope():
    service = _get_gmail_service()
    if service is None:
        return {"ok": False, "error": "Gmail service unavailable (missing libraries or token)"}
    try:
        service.users().messages().list(userId="me", maxResults=1).execute()
    except Exception as e:
        return {"ok": False, "error": f"Gmail read failed: {e}"}
    try:
        draft = MIMEText("Send scope verification (not actually sent)", "plain")
        draft["to"] = SENDER
        draft["from"] = SENDER
        draft["subject"] = "scope-check"
        raw = base64.urlsafe_b64encode(draft.as_bytes()).decode()
        service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return {"ok": True, "scopes": ["gmail.readonly", "gmail.send"]}
    except Exception as e:
        err = str(e)
        if "insufficient" in err.lower() or "403" in err:
            return {
                "ok": False,
                "error": "gmail.send scope not granted. Re-run: rm config/gmail_token.json && python3 scripts/setup_gmail_oauth.py",
            }
        return {"ok": False, "error": f"Draft creation failed: {e}"}


def send_event_notification(event):
    config = _load_config()
    event_type = event.get("type", "")
    if not config.get(event_type, False):
        return False
    subject, body = format_event_email(event)
    return send_notification(subject, body)
