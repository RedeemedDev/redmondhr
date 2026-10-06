"""Sample/demo employees — clearly marked with is_demo=1."""
from __future__ import annotations

from datetime import date, timedelta

from app import crud
from app.database import init_db


def _iso(d: date) -> str:
    return d.isoformat()


def load_demo_data(force: bool = False) -> int:
    """Insert demo employees if DB empty (or force=True). Returns count inserted."""
    init_db()
    if not force and crud.employee_count() > 0:
        return 0

    today = date.today()
    samples = [
        {
            "name": "[DEMO] Avery Chen",
            "date_of_birth": _iso(date(today.year, today.month, min(today.day + 5, 28))),
            "phone": "613-555-0101",
            "address": "12 Maple St, Redmond, ON K1A 0B1",
            "drivers_license_number": "C1234-56789-01234",
            "drivers_license_expiry": _iso(today + timedelta(days=12)),
            "health_card_number": "1234-567-890-XX",
            "health_card_expiry": _iso(today - timedelta(days=3)),
            "company_start_date": _iso(date(today.year - 3, today.month, min(today.day + 10, 28))),
            "date_of_hire": _iso(date(today.year - 3, today.month, min(today.day + 10, 28))),
            "wage": "$28.50/hr",
            "notes": "Demo employee — delete anytime.",
            "role": "mover_year_2",
            "specialty": "az",
            "millwright_level": "",
        },
        {
            "name": "[DEMO] Jordan Patel",
            "date_of_birth": _iso(date(1990, 6, 15)),
            "phone": "613-555-0102",
            "address": "45 Oak Ave, Redmond, ON K1A 1C2",
            "drivers_license_number": "P9876-54321-09876",
            "drivers_license_expiry": _iso(today + timedelta(days=45)),
            "health_card_number": "9876-543-210-YY",
            "health_card_expiry": _iso(today + timedelta(days=20)),
            "company_start_date": _iso(date(today.year - 1, today.month, min(today.day + 3, 28))),
            "date_of_hire": _iso(date(today.year - 1, today.month, min(today.day + 3, 28))),
            "wage": "$32.00/hr",
            "notes": "Demo — anniversary soon (uses company start date).",
            "role": "mover_year_3",
            "specialty": "millwright",
            "millwright_level": "year_3",
        },
        {
            "name": "[DEMO] Sam Rivera",
            "date_of_birth": _iso(date(1985, today.month, min(today.day + 18, 28))),
            "phone": "613-555-0103",
            "address": "8 Pine Rd, Redmond, ON K1A 2D3",
            "drivers_license_number": "R5555-11111-22222",
            "drivers_license_expiry": _iso(today - timedelta(days=10)),
            "health_card_number": "5555-111-222-ZZ",
            "health_card_expiry": _iso(today + timedelta(days=90)),
            "company_start_date": _iso(date(2019, 3, 1)),
            "date_of_hire": _iso(date(2019, 3, 1)),
            "wage": "$35.00/hr",
            "notes": "Demo — DL overdue for notification testing.",
            "role": "team_lead",
            "specialty": "none",
            "millwright_level": "",
        },
        {
            "name": "[DEMO] Casey Nguyen",
            "date_of_birth": _iso(date(1998, 4, 22)),
            "phone": "613-555-0104",
            "address": "22 Birch Lane, Redmond, ON K1A 3E4",
            "drivers_license_number": "N4444-33333-22222",
            "drivers_license_expiry": _iso(today + timedelta(days=100)),
            "health_card_number": "4444-333-222-AA",
            "health_card_expiry": _iso(today + timedelta(days=120)),
            # Recent start so orientation (+21d) and/or probation (+3mo) land in window
            "company_start_date": _iso(today - timedelta(days=10)),
            "date_of_hire": _iso(today - timedelta(days=10)),
            "wage": "$24.00/hr",
            "notes": "Demo — recent hire for orientation / probation reminders.",
            "role": "mover_year_1",
            "specialty": "none",
            "millwright_level": "",
        },
    ]

    count = 0
    for s in samples:
        crud.create_employee(s, is_demo=True)
        count += 1
    return count
