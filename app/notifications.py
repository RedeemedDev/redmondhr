"""Notification and report helpers for expiry / milestone windows.

Anniversary uses company_start_date (documented in UI and README).
Default window is 30 days; overdue items are always included.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def add_months(d: date, months: int) -> date:
    """Add calendar months, clamping day to end of target month when needed."""
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _next_anniversary(event: date, today: date) -> date:
    """Return the next occurrence of month/day on or after today."""
    try:
        candidate = event.replace(year=today.year)
    except ValueError:
        # Feb 29 → Feb 28 in non-leap years
        candidate = event.replace(year=today.year, day=28)
    if candidate < today:
        try:
            candidate = event.replace(year=today.year + 1)
        except ValueError:
            candidate = event.replace(year=today.year + 1, day=28)
    return candidate


def _days_until(target: date, today: date) -> int:
    return (target - today).days


def classify_window(days: int) -> str:
    if days < 0:
        return "overdue"
    if days == 0:
        return "today"
    return "upcoming"


def build_notifications(
    employees: list[dict[str, Any]],
    window_days: int = 30,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Build notification list for DL, health card, birthday, anniversary,
    follow-up orientation, and probation end.

    Training-stage due reminders were removed (role/specialty model).
    """
    today = today or date.today()
    end = today + timedelta(days=window_days)
    items: list[dict[str, Any]] = []

    for emp in employees:
        eid = emp["id"]
        name = emp["name"]

        # Absolute expiry dates
        for field, label, kind in (
            ("drivers_license_expiry", "Driver's license expiry", "dl_expiry"),
            ("health_card_expiry", "Health card expiry", "health_card_expiry"),
        ):
            d = _parse_date(emp.get(field))
            if not d:
                continue
            # Include overdue always; upcoming within window
            if d <= end:
                days = _days_until(d, today)
                items.append(
                    {
                        "employee_id": eid,
                        "employee_name": name,
                        "kind": kind,
                        "label": label,
                        "event_date": d.isoformat(),
                        "days": days,
                        "status": classify_window(days),
                        "detail": None,
                        "event_key": f"{kind}:{eid}:{d.isoformat()}",
                    }
                )

        # Birthday (recurring)
        dob = _parse_date(emp.get("date_of_birth"))
        if dob:
            nxt = _next_anniversary(dob, today)
            if nxt <= end:
                days = _days_until(nxt, today)
                turning_age = nxt.year - dob.year
                items.append(
                    {
                        "employee_id": eid,
                        "employee_name": name,
                        "kind": "birthday",
                        "label": "Birthday",
                        "event_date": nxt.isoformat(),
                        "days": days,
                        "status": classify_window(days),
                        "detail": f"turning {turning_age}",
                        "event_key": f"birthday:{eid}:{nxt.isoformat()}",
                    }
                )

        # Work anniversary — uses company_start_date
        start = _parse_date(emp.get("company_start_date"))
        if start:
            nxt = _next_anniversary(start, today)
            if nxt <= end:
                anniv_years = nxt.year - start.year
                days = _days_until(nxt, today)
                items.append(
                    {
                        "employee_id": eid,
                        "employee_name": name,
                        "kind": "anniversary",
                        "label": "Work anniversary",
                        "event_date": nxt.isoformat(),
                        "days": days,
                        "status": classify_window(days),
                        "detail": f"{anniv_years} year{'s' if anniv_years != 1 else ''}",
                        "event_key": f"anniversary:{eid}:{nxt.isoformat()}",
                    }
                )

            # Follow-Up Orientation — company_start_date + 21 days
            orientation_due = start + timedelta(days=21)
            if orientation_due <= end:
                days = _days_until(orientation_due, today)
                items.append(
                    {
                        "employee_id": eid,
                        "employee_name": name,
                        "kind": "follow_up_orientation",
                        "label": "Follow-Up Orientation",
                        "event_date": orientation_due.isoformat(),
                        "days": days,
                        "status": classify_window(days),
                        "detail": "3 weeks after start",
                        "event_key": f"follow_up_orientation:{eid}:{orientation_due.isoformat()}",
                    }
                )

            # Probation Over — company_start_date + 3 calendar months
            probation_due = add_months(start, 3)
            if probation_due <= end:
                days = _days_until(probation_due, today)
                items.append(
                    {
                        "employee_id": eid,
                        "employee_name": name,
                        "kind": "probation_over",
                        "label": "Probation Over",
                        "event_date": probation_due.isoformat(),
                        "days": days,
                        "status": classify_window(days),
                        "detail": "3 months after start",
                        "event_key": f"probation_over:{eid}:{probation_due.isoformat()}",
                    }
                )

    # Sort: overdue first, then soonest
    items.sort(key=lambda x: (0 if x["status"] == "overdue" else 1, x["days"], x["employee_name"]))
    return items


def filter_by_kind(items: list[dict], kinds: set[str]) -> list[dict]:
    return [i for i in items if i["kind"] in kinds]


def list_dismissed_keys(conn) -> set[str]:
    rows = conn.execute("SELECT event_key FROM dismissed_reminders").fetchall()
    return {r["event_key"] for r in rows}


def dismiss_reminder(conn, event_key: str, employee_id: int, kind: str, event_date: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO dismissed_reminders (event_key, employee_id, kind, event_date)
        VALUES (?, ?, ?, ?)
        """,
        (event_key, employee_id, kind, event_date),
    )


def filter_dismissed(items: list[dict], dismissed: set[str]) -> list[dict]:
    return [i for i in items if i.get("event_key") not in dismissed]
