"""Employee and document CRUD operations."""
from __future__ import annotations

import re
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from app.config import UPLOADS_DIR, ensure_data_dirs
from app.database import db_session, row_to_dict, rows_to_list

EMPLOYEE_FIELDS = [
    "name",
    "date_of_birth",
    "phone",
    "address",
    "drivers_license_number",
    "drivers_license_expiry",
    "health_card_number",
    "health_card_expiry",
    "company_start_date",
    "date_of_hire",
    "wage",
    "notes",
    "role",
    "specialty",
    "millwright_level",
]

DOC_TYPES = ("review", "disciplinary", "other")
HISTORY_TYPES = ("wage", "promotion")

# Locked role / specialty / millwright level model
ROLE_CHOICES = [
    ("mover_year_1", "Mover Year 1"),
    ("mover_year_2", "Mover Year 2"),
    ("mover_year_3", "Mover Year 3"),
    ("team_lead", "Team Lead"),
]
ROLE_LABELS = dict(ROLE_CHOICES)
ROLE_SORT_ORDER = {
    "mover_year_1": 1,
    "mover_year_2": 2,
    "mover_year_3": 3,
    "team_lead": 4,
}

SPECIALTY_CHOICES = [
    ("none", "None"),
    ("az", "AZ"),
    ("millwright", "Millwright"),
]
SPECIALTY_LABELS = dict(SPECIALTY_CHOICES)
# List/sort: Millwrights first, then AZ, then None
SPECIALTY_SORT_ORDER = {
    "millwright": 1,
    "az": 2,
    "none": 3,
}

MILLWRIGHT_LEVEL_CHOICES = [
    ("year_2", "Year 2"),
    ("year_3", "Year 3"),
    ("year_4", "Year 4"),
    ("full_cert", "Full Cert"),
]
MILLWRIGHT_LEVEL_LABELS = dict(MILLWRIGHT_LEVEL_CHOICES)
# Seniority ascending: Year 2 < Year 3 < Year 4 < Full Cert
MILLWRIGHT_LEVEL_SORT_ORDER = {
    "year_2": 1,
    "year_3": 2,
    "year_4": 3,
    "full_cert": 4,
}

VALID_ROLES = set(ROLE_LABELS)
VALID_SPECIALTIES = set(SPECIALTY_LABELS)
VALID_MILLWRIGHT_LEVELS = set(MILLWRIGHT_LEVEL_LABELS)


def role_label(value: str | None) -> str:
    if not value:
        return "—"
    return ROLE_LABELS.get(value, value)


def specialty_label(value: str | None, *, for_list: bool = False) -> str:
    v = (value or "none").strip() or "none"
    if for_list and v == "none":
        return "—"
    return SPECIALTY_LABELS.get(v, v)


def millwright_level_label(value: str | None) -> str:
    if not value:
        return "—"
    return MILLWRIGHT_LEVEL_LABELS.get(value, value)



def sync_hire_and_start_dates(data: dict[str, Any]) -> dict[str, Any]:
    """Write one hire/start input into both date_of_hire and company_start_date."""
    out = dict(data)
    hire = (out.get("date_of_hire") or "").strip()
    start = (out.get("company_start_date") or "").strip()
    shared = hire or start
    out["date_of_hire"] = shared or None
    out["company_start_date"] = shared or None
    return out


def normalize_employee_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Validate/normalize role, specialty, millwright_level; sync hire/start dates."""
    out = sync_hire_and_start_dates(data)
    role = (out.get("role") or "").strip()
    if role and role not in VALID_ROLES:
        role = ""
    out["role"] = role or None

    specialty = (out.get("specialty") or "none").strip() or "none"
    if specialty not in VALID_SPECIALTIES:
        specialty = "none"
    out["specialty"] = specialty

    level = (out.get("millwright_level") or "").strip() or None
    if specialty != "millwright":
        level = None
    elif level and level not in VALID_MILLWRIGHT_LEVELS:
        level = None
    out["millwright_level"] = level
    return out


def _sort_key_role(emp: dict) -> tuple:
    role = emp.get("role") or ""
    return (ROLE_SORT_ORDER.get(role, 99), (emp.get("name") or "").lower())


def _sort_key_specialty(emp: dict) -> tuple:
    specialty = (emp.get("specialty") or "none").strip() or "none"
    level = emp.get("millwright_level") or ""
    # Millwrights sub-ranked by level; non-millwrights get 0 for level slot
    level_rank = (
        MILLWRIGHT_LEVEL_SORT_ORDER.get(level, 0) if specialty == "millwright" else 0
    )
    return (
        SPECIALTY_SORT_ORDER.get(specialty, 99),
        level_rank,
        (emp.get("name") or "").lower(),
    )


def _sort_key_name(emp: dict) -> tuple:
    return ((emp.get("name") or "").lower(),)


def _shared_hire_date(emp: dict) -> str | None:
    """Prefer date_of_hire, fall back to company_start_date (kept in sync on save)."""
    for key in ("date_of_hire", "company_start_date"):
        val = (emp.get(key) or "").strip()
        if val:
            return val
    return None


def _sort_key_hire(emp: dict) -> tuple:
    # Chronological; nulls last; then name
    d = _shared_hire_date(emp)
    if not d:
        return (1, "", (emp.get("name") or "").lower())
    return (0, d, (emp.get("name") or "").lower())


def _wage_sort_number(wage: str | None) -> float | None:
    """Parse leading number from wage text like '$28.50/hr'."""
    s = (wage or "").strip()
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _sort_key_wage(emp: dict) -> tuple:
    # Numeric-ish when possible; else string; nulls last; then name
    raw = (emp.get("wage") or "").strip()
    name = (emp.get("name") or "").lower()
    if not raw:
        return (1, 0.0, "", name)
    num = _wage_sort_number(raw)
    if num is not None:
        return (0, 0, num, name)
    return (0, 1, raw.lower(), name)


def list_employees(
    include_demo: bool = True,
    sort: str = "name",
    direction: str = "asc",
) -> list[dict]:
    """List employees sorted by column.

    Natural ascending meanings:
      name: A→Z
      hire: earliest→latest (nulls last)
      role: Year 1 → Team Lead
      specialty: Millwright (Y2→…→Full Cert) → AZ → None
      wage: low→high when parseable (nulls last)

    direction 'desc' (or 'order=desc') reverses that natural order.
    """
    with db_session() as conn:
        if include_demo:
            rows = conn.execute("SELECT * FROM employees").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM employees WHERE is_demo = 0"
            ).fetchall()
        employees = rows_to_list(rows)

    sort = (sort or "name").strip().lower()
    direction = (direction or "asc").strip().lower()
    if direction in ("desc", "descending", "down"):
        reverse = True
    else:
        reverse = False

    if sort in ("hire", "hire_date"):
        key = _sort_key_hire
    elif sort == "wage":
        key = _sort_key_wage
    elif sort == "role":
        key = _sort_key_role
    elif sort == "specialty":
        key = _sort_key_specialty
    else:
        key = _sort_key_name
    employees.sort(key=key, reverse=reverse)
    return employees


def get_employee(employee_id: int) -> dict | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        return row_to_dict(row)


def _add_history_row(
    conn,
    employee_id: int,
    event_type: str,
    effective_date: str,
    amount: str | None = None,
    note: str | None = None,
) -> None:
    if event_type not in HISTORY_TYPES:
        event_type = "wage"
    conn.execute(
        """
        INSERT INTO wage_history (employee_id, effective_date, event_type, amount, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            employee_id,
            effective_date,
            event_type,
            amount or None,
            note or None,
        ),
    )


def add_wage_history(
    employee_id: int,
    event_type: str,
    effective_date: str,
    amount: str | None = None,
    note: str | None = None,
) -> None:
    with db_session() as conn:
        _add_history_row(conn, employee_id, event_type, effective_date, amount, note)


def list_wage_history(employee_id: int) -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM wage_history
            WHERE employee_id = ?
            ORDER BY effective_date DESC, created_at DESC, id DESC
            """,
            (employee_id,),
        ).fetchall()
        return rows_to_list(rows)


def ensure_wage_history_backfill(employee_id: int) -> None:
    """If employee has a wage but no history rows, seed one."""
    emp = get_employee(employee_id)
    if not emp:
        return
    wage = (emp.get("wage") or "").strip()
    if not wage:
        return
    history = list_wage_history(employee_id)
    if history:
        return
    effective = (
        (emp.get("company_start_date") or "").strip()
        or (emp.get("date_of_hire") or "").strip()
        or date.today().isoformat()
    )
    add_wage_history(employee_id, "wage", effective, amount=wage, note="Initial wage (backfill)")


def create_employee(data: dict[str, Any], is_demo: bool = False) -> int:
    data = normalize_employee_fields(data)
    values = [data.get(f) or None for f in EMPLOYEE_FIELDS]
    with db_session() as conn:
        cur = conn.execute(
            f"""
            INSERT INTO employees ({', '.join(EMPLOYEE_FIELDS)}, is_demo)
            VALUES ({', '.join('?' for _ in EMPLOYEE_FIELDS)}, ?)
            """,
            (*values, 1 if is_demo else 0),
        )
        eid = int(cur.lastrowid)
        wage = (data.get("wage") or "").strip()
        if wage:
            effective = (
                (data.get("company_start_date") or "").strip()
                or (data.get("date_of_hire") or "").strip()
                or date.today().isoformat()
            )
            _add_history_row(conn, eid, "wage", effective, amount=wage, note="Starting wage")
        return eid


def update_employee(
    employee_id: int,
    data: dict[str, Any],
    *,
    history_effective_date: str | None = None,
    promoted_to_team_lead: bool = False,
    history_note: str | None = None,
) -> bool:
    existing = get_employee(employee_id)
    if not existing:
        return False

    data = normalize_employee_fields(data)
    old_wage = (existing.get("wage") or "").strip()
    new_wage = (data.get("wage") or "").strip()
    effective = (history_effective_date or "").strip() or date.today().isoformat()

    sets = ", ".join(f"{f} = ?" for f in EMPLOYEE_FIELDS)
    values = [data.get(f) or None for f in EMPLOYEE_FIELDS]
    with db_session() as conn:
        cur = conn.execute(
            f"""
            UPDATE employees
            SET {sets}, updated_at = datetime('now')
            WHERE id = ?
            """,
            (*values, employee_id),
        )
        if cur.rowcount == 0:
            return False

        if new_wage and new_wage != old_wage:
            _add_history_row(
                conn,
                employee_id,
                "wage",
                effective,
                amount=new_wage,
                note=(history_note or None),
            )

        if promoted_to_team_lead:
            note = (history_note or "").strip() or "Promoted to Team Lead"
            if "team lead" not in note.lower():
                note = f"Promoted to Team Lead — {note}" if note else "Promoted to Team Lead"
            _add_history_row(
                conn,
                employee_id,
                "promotion",
                effective,
                amount=new_wage or old_wage or None,
                note=note,
            )

        return True


def delete_employee(employee_id: int) -> bool:
    """Delete employee and their uploaded files."""
    docs = list_documents(employee_id)
    with db_session() as conn:
        conn.execute("DELETE FROM wage_history WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM documents WHERE employee_id = ?", (employee_id,))
        cur = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        deleted = cur.rowcount > 0
    for doc in docs:
        path = UPLOADS_DIR / doc["stored_filename"]
        if path.is_file():
            path.unlink(missing_ok=True)
    return deleted


def employee_count() -> int:
    with db_session() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM employees").fetchone()
        return int(row["c"]) if row else 0


def list_documents(employee_id: int) -> list[dict]:
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE employee_id = ?
            ORDER BY uploaded_at DESC
            """,
            (employee_id,),
        ).fetchall()
        return rows_to_list(rows)


def get_document(doc_id: int) -> dict | None:
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return row_to_dict(row)


def add_document(
    employee_id: int,
    doc_type: str,
    original_filename: str,
    source_path: Path,
    notes: str | None = None,
) -> int:
    ensure_data_dirs()
    if doc_type not in DOC_TYPES:
        doc_type = "other"
    ext = Path(original_filename).suffix
    stored = f"{employee_id}_{uuid.uuid4().hex}{ext}"
    dest = UPLOADS_DIR / stored
    shutil.copy2(source_path, dest)
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO documents (employee_id, doc_type, original_filename, stored_filename, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (employee_id, doc_type, original_filename, stored, notes or None),
        )
        return int(cur.lastrowid)


def delete_document(doc_id: int) -> bool:
    doc = get_document(doc_id)
    if not doc:
        return False
    with db_session() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    path = UPLOADS_DIR / doc["stored_filename"]
    if path.is_file():
        path.unlink(missing_ok=True)
    return True
