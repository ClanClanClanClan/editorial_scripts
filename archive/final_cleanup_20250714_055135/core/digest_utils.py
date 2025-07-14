import html
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from datetime import datetime

def titlecase_name(name):
    import re
    if not name:
        return ""
    name = re.sub(r"\s+#\d+$", "", str(name))
    return " ".join([w.capitalize() for w in name.strip().split()])

def european_date(date_str):
    if not date_str:
        return ""
    try:
        dt = date_parser.parse(date_str)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)

def days_ago(date_str):
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        return (now - dt).days
    except Exception:
        return None

def time_since(date_str):
    if not date_str:
        return ""
    try:
        dt = date_parser.parse(date_str)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = relativedelta(now, dt)
        out = []
        if delta.years: out.append(f"{delta.years} years")
        if delta.months: out.append(f"{delta.months} months")
        if delta.days >= 7: out.append(f"{delta.days // 7} weeks")
        days = delta.days % 7
        if days: out.append(f"{days} days")
        if not out: out.append("today")
        return ", ".join(out)
    except Exception:
        return ""

def normalize_ref_status(status):
    s = (status or "").strip().lower()
    if s in {"agreed", "accepted", "overdue"}:
        return "Accepted"
    if s in {"contacted", "pending"}:
        return "Contacted"
    return status.capitalize()

def compute_lateness(status, due, accepted_date=None):
    s = (status or "").strip().lower()
    accepted_like = s in {"agreed", "accepted", "overdue"}
    if not due:
        return ""
    try:
        due_dt = date_parser.parse(due)
        now = datetime.now(due_dt.tzinfo) if due_dt.tzinfo else datetime.now()
        days_late = (now - due_dt).days
        if accepted_like and days_late > 0:
            return f"{days_late} days late"
        elif accepted_like and days_late == 0:
            return "Due today"
    except Exception:
        return ""
    return ""

def build_urgent_report_html(urgent_refs):
    if not urgent_refs:
        return ""
    urgent_html = (
        "<div style='border:2px solid red;background:#fff4f4;padding:10px;margin-bottom:20px'>"
        "<h3 style='color:red;margin:0'>URGENT: Action Required for These Referees</h3>"
        "<ul style='margin:7px'>"
    )
    for ms_id, name, status, date_, due in urgent_refs:
        urgent_html += (
            f"<li><b>{html.escape(str(name))}</b> (ms {html.escape(str(ms_id))}): Status {html.escape(str(status))}, "
            f"Contacted/Accepted {html.escape(european_date(date_))} "
            f"(Due {html.escape(european_date(due)) if due else '-'})</li>"
        )
    urgent_html += "</ul></div>"
    return urgent_html

def get_ref_date(ref, ms_id, status, flagged_emails, match_func):
    contacted = ref.get("Contacted Date", "") or ref.get("contacted_date", "")
    accepted = ref.get("Accepted Date", "") or ref.get("accepted_date", "")
    if accepted:
        return accepted
    elif contacted:
        return contacted
    else:
        name = ref.get("Referee Name", ref.get("name", ""))
        return match_func(titlecase_name(name), ms_id, status, flagged_emails)

def get_ref_email(ref, flagged_emails, ms_id, status, match_func):
    return (
        ref.get("Referee Email", "") or
        ref.get("Email", "") or
        ref.get("email", "") or
        ""
    )

def get_current_stage(referees):
    if not referees:
        return ""
    statuses = [normalize_ref_status(r.get("Status", r.get("status", ""))) for r in referees]
    if "Contacted" in statuses:
        return "Pending Referee Assignment"
    return "All Referees Assigned"

def build_html_digest(journal_name, ms_list, flagged_emails, unmatched_refs, urgent_refs, match_func):
    if ms_list is None:
        ms_list = []
    if isinstance(ms_list, dict):
        ms_list = [ms_list]
    color_scheme = {
        'header_bg': '#b2c9f7',
        'accepted_bg': '#eafbf0',
        'contacted_bg': '#fffbe6',
        'late_bg': '#ffe2e2',
        'urgent_bg': '#ff9090',
        'crosscheck_accepted': '#fffcb3',
        'crosscheck_contacted': '#ececec',
        'crosscheck_unmatched': '#ffd6d6',
    }
    out = []
    urgent_html = build_urgent_report_html(urgent_refs)
    if urgent_html:
        out.append(urgent_html)
    out.append(f"<h2 style='background:{color_scheme['header_bg']};padding:7px'>{html.escape(str(journal_name))}</h2>")
    out.append("<table border='1' cellpadding='4' style='border-collapse:collapse;font-size:13px'>")

    # --- Column headers ---
    if journal_name == "FS":
        out.append(
            "<tr style='background:#e2e2e2;font-weight:bold'>"
            "<th>Manuscript #</th><th>Title</th><th>Contact Author</th><th>Current Stage</th><th>Referee</th>"
            "<th>Status</th><th>Email</th><th>Contacted/Accepted Date</th><th>Elapsed</th><th>Due Date</th><th>Lateness</th>"
            "</tr>"
        )
    else:
        out.append(
            "<tr style='background:#e2e2e2;font-weight:bold'>"
            "<th>Manuscript #</th><th>Title</th><th>Current Stage</th><th>Referee</th><th>Status</th>"
            "<th>Email</th><th>Contacted/Accepted Date</th><th>Elapsed</th><th>Due Date</th><th>Lateness</th>"
            "</tr>"
        )

    for ms in ms_list:
        if not ms:
            continue
        ms_id = ms.get("Manuscript #", "")
        title = ms.get("Title", "")
        contact_author = ms.get("Contact Author", "") if journal_name == "FS" else ""
        refs = ms.get("Referees", [ms])
        current_stage = get_current_stage(refs)
        for ref in refs:
            name = titlecase_name(ref.get("Referee Name") if "Referee Name" in ref else ref.get("name", ""))
            status = ref.get("Status", ref.get("status", ""))
            norm_status = normalize_ref_status(status)
            due = ref.get("Due Date", ref.get("due", ""))
            email_ = get_ref_email(ref, flagged_emails, ms_id, status, match_func)
            date_ = get_ref_date(ref, ms_id, status, flagged_emails, match_func)
            elapsed = time_since(date_)
            elapsed_days = days_ago(date_)
            lateness = compute_lateness(status, due, ref.get("Accepted Date") or ref.get("accepted_date"))
            # Row background
            row_bg = color_scheme['accepted_bg'] if norm_status == "Accepted" else color_scheme['contacted_bg']
            if lateness:
                row_bg = color_scheme['late_bg']
            if norm_status == "Contacted" and elapsed_days is not None and elapsed_days > 7:
                row_bg = color_scheme['urgent_bg']
            elif norm_status == "Accepted" and elapsed_days is not None and elapsed_days > 120:
                row_bg = color_scheme['urgent_bg']
            # --- Output row ---
            if journal_name == "FS":
                out.append(
                    f"<tr style='background:{row_bg}'>" +
                    f"<td>{html.escape(str(ms_id))}</td>"
                    f"<td>{html.escape(str(title))}</td>"
                    f"<td>{html.escape(str(contact_author))}</td>"
                    f"<td>{html.escape(str(current_stage))}</td>"
                    f"<td>{html.escape(str(name))}</td>"
                    f"<td>{html.escape(str(status))}</td>"
                    f"<td>{html.escape(str(email_))}</td>"
                    f"<td>{html.escape(european_date(date_))}</td>"
                    f"<td>{html.escape(elapsed)}</td>"
                    f"<td>{html.escape(european_date(due))}</td>"
                    f"<td>{html.escape(lateness)}</td>"
                    "</tr>"
                )
            else:
                out.append(
                    f"<tr style='background:{row_bg}'>" +
                    f"<td>{html.escape(str(ms_id))}</td>"
                    f"<td>{html.escape(str(title))}</td>"
                    f"<td>{html.escape(str(current_stage))}</td>"
                    f"<td>{html.escape(str(name))}</td>"
                    f"<td>{html.escape(str(status))}</td>"
                    f"<td>{html.escape(str(email_))}</td>"
                    f"<td>{html.escape(european_date(date_))}</td>"
                    f"<td>{html.escape(elapsed)}</td>"
                    f"<td>{html.escape(european_date(due))}</td>"
                    f"<td>{html.escape(lateness)}</td>"
                    "</tr>"
                )
    out.append("</table>")

    # Crosscheck report: matched referees in yellow/grey, unmatched in red
    out.append("<div style='margin-top:12px;padding:7px;background:#f8f8f8;border:1px solid #aaa'>"
               "<b>Referee–Email Crosscheck</b><br><ul style='list-style-type:none;padding-left:0'>")
    matched = []
    unmatched = []
    for ms in ms_list:
        ms_id = ms.get("Manuscript #", "")
        refs = ms.get("Referees", [ms])
        for ref in refs:
            name = titlecase_name(ref.get("Referee Name") if "Referee Name" in ref else ref.get("name", ""))
            status = ref.get("Status", ref.get("status", "")).strip()
            norm_status = normalize_ref_status(status)
            email_ = get_ref_email(ref, flagged_emails, ms_id, status, match_func)
            if email_:
                color = color_scheme['crosscheck_accepted'] if norm_status == "Accepted" else color_scheme['crosscheck_contacted']
                matched.append((name, ms_id, norm_status, color, email_))
            else:
                unmatched.append((name, ms_id))
    for name, ms_id, norm_status, color, email_ in matched:
        out.append(
            f"<li style='background:{color};padding:2px 7px;margin-bottom:2px;border-radius:5px' title='{html.escape(email_)}'>"
            f"{html.escape(name)} (ms {html.escape(str(ms_id))}) — {html.escape(norm_status)}"
            "</li>"
        )
    for name, ms_id in unmatched:
        out.append(
            f"<li style='background:{color_scheme['crosscheck_unmatched']};padding:2px 7px;margin-bottom:2px;border-radius:5px'>"
            f"<b>{html.escape(name)}</b> (ms {html.escape(str(ms_id))}) — <b>NO MATCH IN EMAILS</b>"
            "</li>"
        )
    out.append("</ul></div>")
    return "\n".join(out)

def collect_unmatched_and_urgent(ms_list, flagged_emails, match_func):
    unmatched = []
    urgent = []
    if ms_list is None:
        return unmatched, urgent
    if isinstance(ms_list, dict):
        ms_list = [ms_list]
    for ms in ms_list:
        if not ms:
            continue
        ms_id = ms.get("Manuscript #", "")
        refs = ms.get("Referees", [ms])
        for ref in refs:
            name = titlecase_name(ref.get("Referee Name") if "Referee Name" in ref else ref.get("name", ""))
            status = ref.get("Status", ref.get("status", ""))
            norm_status = normalize_ref_status(status)
            due = ref.get("Due Date", ref.get("due", ""))
            date_ = get_ref_date(ref, ms_id, status, flagged_emails, match_func)
            elapsed_days = days_ago(date_)
            if norm_status == "Contacted" and (elapsed_days is not None and elapsed_days > 7):
                urgent.append((ms_id, name, status, date_, due))
            if norm_status == "Accepted" and (elapsed_days is not None and elapsed_days > 120):
                urgent.append((ms_id, name, status, date_, due))
            if not date_:
                unmatched.append((name, ms_id))
    return unmatched, urgent