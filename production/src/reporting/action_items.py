"""Compute actionable editorial items from extraction data."""

import datetime
import re
from dataclasses import asdict, dataclass, field

from reporting.cross_journal_report import (
    INACTIVE_REFEREE_STATUSES,
    JOURNALS,
    _dedup_referees,
    load_journal_data,
)

FS_REVIEW_DEADLINE_DAYS = 90

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
    return None


def _normalize_referee_status(ref: dict, journal: str) -> str:
    ps = ref.get("platform_specific") or {}
    raw = ps.get("status") or ref.get("status") or ""
    raw_lower = raw.lower().strip()
    dates = ref.get("dates") or {}
    sd = ref.get("status_details") or {}

    if raw_lower in INACTIVE_REFEREE_STATUSES or raw_lower in {
        s.lower() for s in INACTIVE_REFEREE_STATUSES
    }:
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

    if raw_lower in ("agreed", "awaiting report"):
        return "agreed"
    if sd.get("agreed_to_review"):
        return "agreed"
    if dates.get("agreed") and not dates.get("returned"):
        return "agreed"

    if raw_lower == "declined":
        return "declined"
    if sd.get("declined"):
        return "declined"

    if sd.get("no_response"):
        return "pending"
    if dates.get("invited") and not dates.get("agreed") and not dates.get("returned"):
        return "pending"

    if raw_lower:
        return raw_lower
    return "unknown"


def _get_due_date(ref: dict, journal: str) -> datetime.date | None:
    dates = ref.get("dates") or {}
    if dates.get("due"):
        d = _parse_date(dates["due"])
        if d:
            return d

    ps = ref.get("platform_specific") or {}
    if ps.get("due_date"):
        d = _parse_date(str(ps["due_date"]))
        if d:
            return d

    if journal == "fs":
        agreed_str = dates.get("agreed")
        if agreed_str:
            agreed = _parse_date(agreed_str)
            if agreed:
                return agreed + datetime.timedelta(days=FS_REVIEW_DEADLINE_DAYS)
        invited_str = dates.get("invited")
        if invited_str:
            invited = _parse_date(invited_str)
            if invited:
                return invited + datetime.timedelta(days=FS_REVIEW_DEADLINE_DAYS)

    return None


def _get_reminders(ref: dict) -> int:
    stats = ref.get("statistics") or {}
    r = stats.get("reminders_received")
    if r is not None:
        return r
    return 0


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


def _is_terminal(ms: dict) -> bool:
    status = _get_manuscript_status(ms).lower().strip()
    return status in TERMINAL_MS_STATUSES


def compute_action_items(journals: list[str] | None = None) -> list[RefereeAction]:
    today = datetime.date.today()
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
            referees = _dedup_referees(ms.get("referees", []))

            active_refs = []
            completed_count = 0
            agreed_count = 0

            for ref in referees:
                norm = _normalize_referee_status(ref, journal)
                if norm in ("declined", "terminated"):
                    continue

                active_refs.append((ref, norm))
                if norm == "completed":
                    completed_count += 1
                elif norm == "agreed":
                    agreed_count += 1

                due = _get_due_date(ref, journal)
                reminders = _get_reminders(ref)
                ref_name = ref.get("name", "Unknown")
                ref_email = ref.get("email")

                if norm == "agreed" and due:
                    days_left = (due - today).days
                    if days_left < 0:
                        items.append(
                            RefereeAction(
                                priority="critical",
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
                            )
                        )
                    elif days_left <= 14:
                        items.append(
                            RefereeAction(
                                priority="medium",
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
                            )
                        )

                elif norm == "pending":
                    dates = ref.get("dates") or {}
                    invited_str = dates.get("invited")
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
                                )
                            )

            total_expected = completed_count + agreed_count
            if completed_count >= 2 and agreed_count == 0 and total_expected >= 2:
                items.append(
                    RefereeAction(
                        priority="critical",
                        action_type="needs_ae_decision",
                        journal=journal.upper(),
                        manuscript_id=ms_id,
                        manuscript_title=ms_title,
                        status=ms_status,
                        message=f"All {completed_count} reports received — AE recommendation needed",
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
                        )
                    )

            if total_expected > 0 and total_expected < 2 and "under review" in ms_status.lower():
                items.append(
                    RefereeAction(
                        priority="high",
                        action_type="needs_more_referees",
                        journal=journal.upper(),
                        manuscript_id=ms_id,
                        manuscript_title=ms_title,
                        status=ms_status,
                        message=f"Only {total_expected} active referee(s) — consider assigning more",
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
                raw = (ref.get("platform_specific") or {}).get("status") or ref.get("status", "")
                dates = ref.get("dates") or {}
                due = _get_due_date(ref, journal)
                reminders = _get_reminders(ref)

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
                            name=ref.get("name", "Unknown"),
                            email=ref.get("email"),
                            normalized_status=norm,
                            raw_status=raw or norm,
                            invited=dates.get("invited"),
                            agreed=dates.get("agreed"),
                            due=due.isoformat() if due else None,
                            returned=dates.get("returned"),
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
                    status=ms_status,
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
