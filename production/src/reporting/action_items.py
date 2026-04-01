"""Compute actionable editorial items from extraction data."""

import datetime
import json
import re
from dataclasses import asdict, dataclass, field
from email.utils import parsedate_to_datetime
from pathlib import Path

from reporting.cross_journal_report import (
    INACTIVE_REFEREE_STATUSES,
    JOURNALS,
    _dedup_referees,
    load_journal_data,
)

FS_REVIEW_DEADLINE_DAYS = 90
DEFAULT_REVIEW_DEADLINE_DAYS = 42
STALE_INVITATION_DAYS = 45

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

TERMINAL_MS_STATUSES = {
    "reject",
    "rejected",
    "submission transferred",
    "transferred",
    "accept",
    "accepted",
    "withdrawn",
    "declined by editor",
    "completed reject",
    "completed accept",
    "completed withdrawn",
    "completed",
    "my assignments with final disposition",
}

SEASONAL_SLOWDOWN = {
    "summer": {
        "start_month": 7,
        "start_day": 1,
        "end_month": 8,
        "end_day": 31,
        "label": "Summer Mode",
    },
    "holiday": {
        "start_month": 12,
        "start_day": 20,
        "end_month": 1,
        "end_day": 5,
        "label": "Holiday Mode",
    },
}
SEASONAL_EXTRA_DAYS = 14


def get_seasonal_mode(today=None):
    if today is None:
        today = datetime.date.today()
    for _key, period in SEASONAL_SLOWDOWN.items():
        sm, sd = period["start_month"], period["start_day"]
        em, ed = period["end_month"], period["end_day"]
        if sm <= em:
            if (today.month, today.day) >= (sm, sd) and (today.month, today.day) <= (
                em,
                ed,
            ):
                return {"label": period["label"]}
        else:
            if (today.month, today.day) >= (sm, sd) or (today.month, today.day) <= (
                em,
                ed,
            ):
                return {"label": period["label"]}
    return None


HARMONIZED_MS_STATUSES = {
    "all referees assigned": "Under Review",
    "awaiting reviewer scores": "Under Review",
    "awaiting reviewer reports": "Under Review",
    "overdue reviewer reports": "Under Review (Overdue)",
    "potential referees assigned": "Under Review",
    "revision r1 under review": "R1 Under Review",
    "revision r2 under review": "R2 Under Review",
    "waiting for potential referee assignment": "Awaiting Assignment",
    "new submission": "Awaiting Assignment",
    "under review": "Under Review",
    "submissions under review": "Under Review",
    "refs assigned": "Under Review",
}


@dataclass
class RefereeAction:
    priority: str
    action_type: str
    journal: str
    manuscript_id: str
    manuscript_title: str
    referee_name: str | None = None
    referee_email: str | None = None
    status: str = ""
    days_overdue: int | None = None
    days_remaining: int | None = None
    due_date: str | None = None
    reminders_sent: int = 0
    message: str = ""
    is_revision: bool = False


@dataclass
class RefereeDetail:
    name: str
    email: str | None
    normalized_status: str
    raw_status: str
    invited: str | None = None
    agreed: str | None = None
    due: str | None = None
    returned: str | None = None
    reminders: int = 0
    days_remaining: int | None = None
    days_overdue: int | None = None


@dataclass
class ManuscriptSummary:
    journal: str
    manuscript_id: str
    title: str
    status: str
    submission_date: str | None = None
    days_in_system: int | None = None
    referees_agreed: int = 0
    referees_completed: int = 0
    referees_pending_response: int = 0
    referees_declined: int = 0
    reports_received: int = 0
    reports_pending: int = 0
    next_due_date: str | None = None
    days_until_next_due: int | None = None
    needs_ae_decision: bool = False
    needs_referee_assignment: bool = False
    referee_details: list = field(default_factory=list)


def _parse_date(s: str | None) -> datetime.date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in (
        "%Y-%m-%d",
        "%d %b %Y",
        "%b %d %Y",
        "%m/%d/%Y",
        "%d-%b-%Y",
        "%d %B %Y",
    ):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s)
    if m:
        try:
            return datetime.datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y"
            ).date()
        except ValueError:
            pass
    m2 = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m2:
        try:
            return datetime.datetime.strptime(
                f"{m2.group(1)} {m2.group(2)} {m2.group(3)}", "%B %d %Y"
            ).date()
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(s).date()
    except Exception:
        pass
    return None


def _display_name(ref: dict) -> str:
    oa = (ref.get("web_profile") or {}).get("openalex") or {}
    display = oa.get("display_name")
    if display:
        return display
    raw = ref.get("name") or "Unknown"
    if "," in raw:
        parts = raw.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return raw


def _clean_raw_status(raw: str) -> str:
    if not raw:
        return ""
    first_line = raw.split("\n")[0].strip()
    first_line = re.sub(r"\s+", " ", first_line)
    return first_line


def _effective_dates(ref: dict) -> dict:
    dates = ref.get("dates") or {}
    ps = ref.get("platform_specific") or {}
    return {
        "invited": dates.get("invited") or ps.get("contact_date"),
        "agreed": dates.get("agreed") or ps.get("acceptance_date"),
        "due": dates.get("due") or ps.get("due_date"),
        "returned": dates.get("returned") or ps.get("received_date"),
    }


def _normalize_referee_status(ref: dict, journal: str) -> str:
    ps = ref.get("platform_specific") or {}
    sd = ref.get("status_details") or {}
    raw = ps.get("status") or ref.get("status") or sd.get("status") or ""
    raw = _clean_raw_status(raw)
    raw_lower = raw.lower().strip()
    dates = _effective_dates(ref)

    if raw_lower in INACTIVE_REFEREE_STATUSES or raw_lower in {
        s.lower() for s in INACTIVE_REFEREE_STATUSES
    }:
        if "terminated" in raw_lower:
            return "terminated"
        return "declined"
    if (
        "declined" in raw_lower
        or "un-invited" in raw_lower
        or "un-assigned" in raw_lower
        or "no response" in raw_lower
    ):
        if "terminated" in raw_lower:
            return "terminated"
        return "declined"

    if raw_lower in ("complete", "completed", "review complete"):
        return "completed"
    if raw_lower == "report submitted":
        return "completed"
    if sd.get("review_received"):
        return "completed"
    if dates.get("returned"):
        return "completed"
    rec = ref.get("recommendation") or ""
    if (rec.lower() not in ("unknown", "n/a", "none", "")) or ps.get("reports"):
        return "completed"

    if raw_lower in ("agreed", "awaiting report", "accepted"):
        return "agreed"
    if sd.get("agreed_to_review"):
        return "agreed"
    if dates.get("agreed") and not dates.get("returned"):
        return "agreed"

    if sd.get("declined"):
        return "declined"

    if raw_lower in ("invited", "contacted", "pending"):
        return "pending"
    if sd.get("no_response"):
        return "declined"
    if dates.get("invited") and not dates.get("agreed") and not dates.get("returned"):
        return "pending"

    if raw_lower in ("overdue",):
        return "agreed"

    if raw_lower:
        return raw_lower
    return "unknown"


def _get_revision_date(ms: dict) -> datetime.date | None:
    ps = ms.get("platform_specific") or {}
    rev_hist = ps.get("revision_history")
    if not rev_hist:
        return None
    latest = rev_hist[-1]
    sub_date = latest.get("submitted_date")
    if sub_date:
        return _parse_date(sub_date)
    return None


def _has_current_round_report(ref: dict, ms: dict, revision_date: datetime.date) -> bool:
    ref_name = (ref.get("name") or "").lower().strip()
    if not ref_name:
        return False
    ps = ms.get("platform_specific") or {}
    reports = ps.get("referee_reports", [])
    for rpt in reports:
        rpt_referee = (rpt.get("referee") or "").lower().strip()
        if not rpt_referee:
            continue
        name_parts = ref_name.split()
        rpt_parts = rpt_referee.split()
        if not (set(name_parts) & set(rpt_parts)):
            continue
        rpt_date = _parse_date(rpt.get("date"))
        if rpt_date and rpt_date >= revision_date:
            return True
    return False


def _apply_revision_awareness(norm: str, ref: dict, ms: dict, journal: str) -> str:
    if journal != "fs":
        return norm
    if norm != "completed":
        return norm
    ps = ms.get("platform_specific") or {}
    rev_round = ps.get("revision_round")
    if not rev_round or rev_round < 1:
        return norm
    revision_date = _get_revision_date(ms)
    if not revision_date:
        return norm
    if _has_current_round_report(ref, ms, revision_date):
        return "completed"
    returned = _parse_date((ref.get("dates") or {}).get("returned"))
    if returned and returned < revision_date:
        return "agreed"
    if not returned:
        return "agreed"
    return norm


def _get_due_date(ref: dict, journal: str, ms: dict | None = None) -> datetime.date | None:
    dates = _effective_dates(ref)
    if dates.get("due"):
        d = _parse_date(dates["due"])
        if d:
            return d

    ps_ref = ref.get("platform_specific") or {}
    if ps_ref.get("due_date"):
        d = _parse_date(str(ps_ref["due_date"]))
        if d:
            return d

    if journal == "fs":
        revision_date = _get_revision_date(ms) if ms else None
        agreed_str = dates.get("agreed")
        if agreed_str:
            agreed = _parse_date(agreed_str)
            if agreed:
                base = agreed
                if revision_date and agreed < revision_date:
                    response_str = ps_ref.get("response_date")
                    response = _parse_date(response_str) if response_str else None
                    if response and response >= revision_date:
                        base = response
                    else:
                        base = revision_date
                return base + datetime.timedelta(days=FS_REVIEW_DEADLINE_DAYS)
        invited_str = dates.get("invited")
        if invited_str:
            invited = _parse_date(invited_str)
            if invited:
                return invited + datetime.timedelta(days=FS_REVIEW_DEADLINE_DAYS)
        return None

    agreed_str = dates.get("agreed")
    if agreed_str:
        agreed = _parse_date(agreed_str)
        if agreed:
            return agreed + datetime.timedelta(days=DEFAULT_REVIEW_DEADLINE_DAYS)

    return None


def _get_reminders(ref: dict, ms: dict | None = None, journal: str = "") -> int:
    counts: list[int] = []

    stats = ref.get("statistics") or {}
    r = stats.get("reminders_received")
    if r is not None:
        counts.append(r)

    if ms and journal == "fs":
        ps = ms.get("platform_specific") or {}
        tm = ps.get("timeline_metrics") or {}
        rr = tm.get("reminders_received") or {}
        ref_name = ref.get("name", "")
        if ref_name in rr:
            counts.append(rr[ref_name])

    if ms:
        ta = ms.get("timeline_analytics") or {}
        rm = ta.get("referee_metrics") or {}
        if rm:
            ref_email = (ref.get("email") or "").strip().lower()
            ref_name_lower = (ref.get("name") or "").strip().lower()
            for key, val in rm.items():
                if not isinstance(val, dict):
                    continue
                k = key.strip().lower()
                if (ref_email and k == ref_email) or (ref_name_lower and k == ref_name_lower):
                    v = val.get("reminders_received", 0)
                    if v:
                        counts.append(v)
                    break

    return max(counts) if counts else 0


def _get_manuscript_status(ms: dict) -> str:
    status = ms.get("status")
    if status:
        return status
    cat = ms.get("category")
    if cat:
        return cat
    ps = ms.get("platform_specific") or {}
    meta = ps.get("metadata") or {}
    if meta.get("current_stage"):
        return meta["current_stage"]
    return "Unknown"


def harmonize_status(raw_status: str) -> str:
    key = raw_status.lower().strip()
    return HARMONIZED_MS_STATUSES.get(key, raw_status)


def _has_ae_report(journal: str, manuscript_id: str) -> bool:
    ae_dir = Path(__file__).resolve().parents[2] / "outputs" / journal / "ae_reports"
    return any(ae_dir.glob(f"ae_{manuscript_id}_*.json"))


def _load_desk_rejection(journal: str, ms_id: str) -> dict | None:
    rec_dir = Path(__file__).resolve().parents[2] / "outputs" / journal / "recommendations"
    if not rec_dir.exists():
        return None
    files = sorted(rec_dir.glob(f"rec_{ms_id}_*.json"), reverse=True)
    if not files:
        return None
    try:
        with open(files[0]) as f:
            data = json.load(f)
        dr = data.get("desk_rejection")
        if dr and dr.get("recommend_desk_reject"):
            return dr
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _is_terminal(ms: dict) -> bool:
    ps = ms.get("platform_specific") or {}
    is_current = ps.get("is_current")
    if is_current is not None and not is_current:
        return True
    cat = (ms.get("category") or "").lower().strip()
    if cat in TERMINAL_MS_STATUSES:
        return True
    status = _get_manuscript_status(ms).lower().strip()
    return status in TERMINAL_MS_STATUSES


def compute_action_items(journals: list[str] | None = None) -> list[RefereeAction]:
    today = datetime.date.today()
    seasonal = get_seasonal_mode(today)
    extra_days = SEASONAL_EXTRA_DAYS if seasonal else 0
    items = []
    target = journals or JOURNALS

    for journal in target:
        data = load_journal_data(journal)
        if not data:
            continue
        for ms in data.get("manuscripts", []):
            if _is_terminal(ms):
                continue
            ms_id = ms.get("manuscript_id", "?")
            ms_title = ms.get("title", "")
            ms_status = _get_manuscript_status(ms)
            is_revision = (
                "revision" in ms_status.lower()
                or "r1" in ms_status.lower()
                or "r2" in ms_status.lower()
            )
            referees = _dedup_referees(ms.get("referees", []))

            active_refs = []
            completed_count = 0
            agreed_count = 0
            stale_pending_count = 0

            for ref in referees:
                norm = _normalize_referee_status(ref, journal)
                if norm in ("declined", "terminated"):
                    continue

                norm = _apply_revision_awareness(norm, ref, ms, journal)

                if norm == "pending":
                    inv_str = _effective_dates(ref).get("invited")
                    inv_d = _parse_date(inv_str)
                    if inv_d and (today - inv_d).days > STALE_INVITATION_DAYS:
                        stale_pending_count += 1
                        continue

                active_refs.append((ref, norm))
                if norm == "completed":
                    completed_count += 1
                elif norm == "agreed":
                    agreed_count += 1

                due = _get_due_date(ref, journal, ms)
                reminders = _get_reminders(ref, ms, journal)
                ref_name = _display_name(ref)
                ref_email = ref.get("email")

                if norm == "agreed" and due:
                    days_left = (due - today).days
                    if days_left < -extra_days:
                        items.append(
                            RefereeAction(
                                priority="high" if seasonal else "critical",
                                action_type="overdue_report",
                                journal=journal.upper(),
                                manuscript_id=ms_id,
                                manuscript_title=ms_title,
                                referee_name=ref_name,
                                referee_email=ref_email,
                                status=norm,
                                days_overdue=abs(days_left),
                                due_date=due.isoformat(),
                                reminders_sent=reminders,
                                message=f"{ref_name} is {abs(days_left)} days overdue ({reminders} reminders sent)",
                                is_revision=is_revision,
                            )
                        )
                    elif days_left <= 14:
                        pri = "medium"
                        if is_revision and days_left <= 7:
                            pri = "high"
                        items.append(
                            RefereeAction(
                                priority=pri,
                                action_type="due_soon",
                                journal=journal.upper(),
                                manuscript_id=ms_id,
                                manuscript_title=ms_title,
                                referee_name=ref_name,
                                referee_email=ref_email,
                                status=norm,
                                days_remaining=days_left,
                                due_date=due.isoformat(),
                                reminders_sent=reminders,
                                message=f"{ref_name}'s report due in {days_left} days",
                                is_revision=is_revision,
                            )
                        )

                elif norm == "pending":
                    invited_str = _effective_dates(ref).get("invited")
                    invited = _parse_date(invited_str)
                    if invited:
                        wait_days = (today - invited).days
                        if wait_days > 7:
                            items.append(
                                RefereeAction(
                                    priority="high",
                                    action_type="pending_invitation",
                                    journal=journal.upper(),
                                    manuscript_id=ms_id,
                                    manuscript_title=ms_title,
                                    referee_name=ref_name,
                                    referee_email=ref_email,
                                    status=norm,
                                    days_overdue=wait_days,
                                    reminders_sent=reminders,
                                    message=f"{ref_name} hasn't responded in {wait_days} days",
                                    is_revision=is_revision,
                                )
                            )

            total_expected = completed_count + agreed_count
            if completed_count >= 2 and agreed_count == 0 and total_expected >= 2:
                ae_report_exists = _has_ae_report(journal, ms_id)
                if ae_report_exists:
                    msg = f"All {completed_count} reports received — AE draft ready"
                    action = "ae_report_ready"
                else:
                    msg = f"All {completed_count} reports received — AE recommendation needed"
                    action = "needs_ae_decision"
                items.append(
                    RefereeAction(
                        priority="critical",
                        action_type=action,
                        journal=journal.upper(),
                        manuscript_id=ms_id,
                        manuscript_title=ms_title,
                        status=ms_status,
                        message=msg,
                        is_revision=is_revision,
                    )
                )

            needs_assignment = ms_status.lower() in (
                "waiting for potential referee assignment",
                "new submission",
            ) or (total_expected == 0 and "under review" not in ms_status.lower())
            if needs_assignment and not _is_terminal(ms):
                stage = (
                    (ms.get("platform_specific") or {}).get("metadata", {}).get("current_stage", "")
                )
                if "waiting" in stage.lower() or total_expected == 0:
                    items.append(
                        RefereeAction(
                            priority="low",
                            action_type="needs_assignment",
                            journal=journal.upper(),
                            manuscript_id=ms_id,
                            manuscript_title=ms_title,
                            status=ms_status,
                            message="Needs referee assignment",
                            is_revision=is_revision,
                        )
                    )

            total_assigned = total_expected + stale_pending_count
            if total_expected > 0 and total_assigned < 2 and "under review" in ms_status.lower():
                if stale_pending_count > 0:
                    msg = f"{stale_pending_count} referee(s) haven't responded"
                else:
                    msg = f"Only {total_expected} active referee(s) — consider assigning more"
                items.append(
                    RefereeAction(
                        priority="high",
                        action_type="needs_more_referees",
                        journal=journal.upper(),
                        manuscript_id=ms_id,
                        manuscript_title=ms_title,
                        status=ms_status,
                        message=msg,
                        is_revision=is_revision,
                    )
                )

            desk_reject = _load_desk_rejection(journal, ms_id)
            if desk_reject:
                reasons = desk_reject.get("reasons", [])
                reason_str = "; ".join(reasons[:3]) if reasons else "Model recommends desk reject"
                items.append(
                    RefereeAction(
                        priority="high",
                        action_type="desk_reject_review",
                        journal=journal.upper(),
                        manuscript_id=ms_id,
                        manuscript_title=ms_title,
                        status=ms_status,
                        message=f"Desk rejection recommended: {reason_str}",
                        is_revision=is_revision,
                    )
                )

    items.sort(
        key=lambda x: (
            PRIORITY_ORDER.get(x.priority, 9),
            -(x.days_overdue or 0),
        )
    )
    return items


def compute_manuscript_summaries(
    journals: list[str] | None = None,
) -> list[ManuscriptSummary]:
    today = datetime.date.today()
    summaries = []
    target = journals or JOURNALS

    for journal in target:
        data = load_journal_data(journal)
        if not data:
            continue
        for ms in data.get("manuscripts", []):
            if _is_terminal(ms):
                continue

            ms_id = ms.get("manuscript_id", "?")
            ms_title = ms.get("title", "")
            ms_status = _get_manuscript_status(ms)
            sub_date_str = ms.get("submission_date")
            sub_date = _parse_date(sub_date_str)
            days_in = (today - sub_date).days if sub_date else None

            referees = _dedup_referees(ms.get("referees", []))
            ref_details = []
            agreed = completed = pending = declined = 0
            next_due = None

            for ref in referees:
                norm = _normalize_referee_status(ref, journal)
                norm = _apply_revision_awareness(norm, ref, ms, journal)
                raw = (ref.get("platform_specific") or {}).get("status") or ref.get("status", "")
                raw = _clean_raw_status(raw)
                eff_dates = _effective_dates(ref)
                due = _get_due_date(ref, journal, ms)
                reminders = _get_reminders(ref, ms, journal)

                days_remaining = None
                days_overdue = None
                if due and norm == "agreed":
                    delta = (due - today).days
                    if delta < 0:
                        days_overdue = abs(delta)
                    else:
                        days_remaining = delta

                    if next_due is None or due < next_due:
                        next_due = due

                if norm == "agreed":
                    agreed += 1
                elif norm == "completed":
                    completed += 1
                elif norm == "pending":
                    pending += 1
                elif norm in ("declined", "terminated"):
                    declined += 1

                ref_details.append(
                    asdict(
                        RefereeDetail(
                            name=_display_name(ref),
                            email=ref.get("email"),
                            normalized_status=norm,
                            raw_status=raw or norm,
                            invited=eff_dates.get("invited"),
                            agreed=eff_dates.get("agreed"),
                            due=due.isoformat() if due else None,
                            returned=eff_dates.get("returned"),
                            reminders=reminders,
                            days_remaining=days_remaining,
                            days_overdue=days_overdue,
                        )
                    )
                )

            reports_received = completed
            reports_pending = agreed
            needs_ae = completed >= 2 and agreed == 0
            needs_assign = ms_status.lower() in (
                "waiting for potential referee assignment",
                "new submission",
            )

            summaries.append(
                ManuscriptSummary(
                    journal=journal.upper(),
                    manuscript_id=ms_id,
                    title=ms_title,
                    status=harmonize_status(ms_status),
                    submission_date=sub_date_str,
                    days_in_system=days_in,
                    referees_agreed=agreed,
                    referees_completed=completed,
                    referees_pending_response=pending,
                    referees_declined=declined,
                    reports_received=reports_received,
                    reports_pending=reports_pending,
                    next_due_date=next_due.isoformat() if next_due else None,
                    days_until_next_due=(next_due - today).days if next_due else None,
                    needs_ae_decision=needs_ae,
                    needs_referee_assignment=needs_assign,
                    referee_details=ref_details,
                )
            )

    summaries.sort(
        key=lambda s: (
            not s.needs_ae_decision,
            not s.needs_referee_assignment,
            s.days_until_next_due if s.days_until_next_due is not None else 9999,
        )
    )
    return summaries
