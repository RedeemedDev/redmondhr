"""Employee and document CRUD operations."""
from __future__ import annotations

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
    "address",
    "drivers_license_number",
    "drivers_license_expiry",
    "health_card_number",
    "health_card_expiry",
    "company_start_date",
    "date_of_hire",
    "wage",
    "notes",
    "training_stage",
    "training_due_date",
]

DOC_TYPES = ("review", "disciplinary", "other")
HISTORY_TYPES = ("wage", "promotion")


def list_employees(include_demo: bool = True) -> list[dict]:
    with db_session() as conn:
        if include_demo:
            rows = conn.execute(
                "SELECT * FROM employees ORDER BY name COLLATE NOCASE"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM employees WHERE is_demo = 0 ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return rows_to_list(rows)


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