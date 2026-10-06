"""Employee CRUD and document upload routes."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import crud
from app.config import UPLOADS_DIR

router = APIRouter(tags=["employees"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _form_to_employee(form: dict) -> dict:
    # Single UI field date_of_hire; copy into both columns for notification logic.
    hire = form.get("date_of_hire") or form.get("company_start_date") or ""
    return {
        "name": (form.get("name") or "").strip(),
        "date_of_birth": form.get("date_of_birth") or "",
        "phone": (form.get("phone") or "").strip(),
        "address": (form.get("address") or "").strip(),
        "drivers_license_number": (form.get("drivers_license_number") or "").strip(),
        "drivers_license_expiry": form.get("drivers_license_expiry") or "",
        "health_card_number": (form.get("health_card_number") or "").strip(),
        "health_card_expiry": form.get("health_card_expiry") or "",
        "company_start_date": hire,
        "date_of_hire": hire,
        "wage": (form.get("wage") or "").strip(),
        "notes": (form.get("notes") or "").strip(),
        "role": (form.get("role") or "").strip(),
        "specialty": (form.get("specialty") or "none").strip() or "none",
        "millwright_level": (form.get("millwright_level") or "").strip(),
    }


def _form_context(**extra):
    ctx = {
        "role_choices": crud.ROLE_CHOICES,
        "specialty_choices": crud.SPECIALTY_CHOICES,
        "millwright_level_choices": crud.MILLWRIGHT_LEVEL_CHOICES,
        "role_label": crud.role_label,
        "specialty_label": crud.specialty_label,
        "millwright_level_label": crud.millwright_level_label,
    }
    ctx.update(extra)
    return ctx


@router.get("/employees", response_class=HTMLResponse)
async def employees_list(
    request: Request,
    q: str = "",
    sort: str = "name",
    dir: str = "",
    order: str = "",
):
    sort = (sort or "name").strip().lower()
    if sort == "hire_date":
        sort = "hire"
    if sort not in ("name", "role", "specialty", "hire", "wage"):
        sort = "name"
    # Prefer dir=; accept order= as alias when dir omitted
    direction = (dir or order or "asc").strip().lower()
    if direction in ("desc", "descending", "down"):
        direction = "desc"
    else:
        direction = "asc"
    employees = crud.list_employees(sort=sort, direction=direction)
    if q:
        ql = q.lower()
        employees = [e for e in employees if ql in (e.get("name") or "").lower()]
    return templates.TemplateResponse(
        "employees_list.html",
        _form_context(
            request=request,
            employees=employees,
            q=q,
            sort=sort,
            dir=direction,
        ),
    )


@router.get("/employees/new", response_class=HTMLResponse)
async def employee_new_form(request: Request):
    return templates.TemplateResponse(
        "employee_form.html",
        _form_context(
            request=request,
            employee=None,
            action="/employees/new",
            title="Add employee",
        ),
    )


@router.post("/employees/new")
async def employee_create(
    request: Request,
    name: str = Form(...),
    date_of_birth: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    drivers_license_number: str = Form(""),
    drivers_license_expiry: str = Form(""),
    health_card_number: str = Form(""),
    health_card_expiry: str = Form(""),
    date_of_hire: str = Form(""),
    wage: str = Form(""),
    notes: str = Form(""),
    role: str = Form(...),
    specialty: str = Form("none"),
    millwright_level: str = Form(""),
):
    data = _form_to_employee(
        {
            "name": name,
            "date_of_birth": date_of_birth,
            "phone": phone,
            "address": address,
            "drivers_license_number": drivers_license_number,
            "drivers_license_expiry": drivers_license_expiry,
            "health_card_number": health_card_number,
            "health_card_expiry": health_card_expiry,
            "date_of_hire": date_of_hire,
            "wage": wage,
            "notes": notes,
            "role": role,
            "specialty": specialty,
            "millwright_level": millwright_level,
        }
    )
    if not data["name"] or not data["role"]:
        return RedirectResponse("/employees/new", status_code=303)
    eid = crud.create_employee(data)
    return RedirectResponse(f"/employees/{eid}", status_code=303)


@router.get("/employees/{employee_id}", response_class=HTMLResponse)
async def employee_detail(request: Request, employee_id: int):
    employee = crud.get_employee(employee_id)
    if not employee:
        return RedirectResponse("/employees", status_code=303)
    crud.ensure_wage_history_backfill(employee_id)
    documents = crud.list_documents(employee_id)
    wage_history = crud.list_wage_history(employee_id)
    return templates.TemplateResponse(
        "employee_detail.html",
        _form_context(
            request=request,
            employee=employee,
            documents=documents,
            doc_types=crud.DOC_TYPES,
            wage_history=wage_history,
        ),
    )


@router.get("/employees/{employee_id}/edit", response_class=HTMLResponse)
async def employee_edit_form(request: Request, employee_id: int):
    employee = crud.get_employee(employee_id)
    if not employee:
        return RedirectResponse("/employees", status_code=303)
    return templates.TemplateResponse(
        "employee_form.html",
        _form_context(
            request=request,
            employee=employee,
            action=f"/employees/{employee_id}/edit",
            title=f"Edit — {employee['name']}",
        ),
    )


@router.post("/employees/{employee_id}/edit")
async def employee_update(
    employee_id: int,
    name: str = Form(...),
    date_of_birth: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    drivers_license_number: str = Form(""),
    drivers_license_expiry: str = Form(""),
    health_card_number: str = Form(""),
    health_card_expiry: str = Form(""),
    date_of_hire: str = Form(""),
    wage: str = Form(""),
    notes: str = Form(""),
    role: str = Form(...),
    specialty: str = Form("none"),
    millwright_level: str = Form(""),
    history_effective_date: str = Form(""),
    promoted_to_team_lead: str = Form(""),
    history_note: str = Form(""),
):
    if not crud.get_employee(employee_id):
        return RedirectResponse("/employees", status_code=303)
    data = _form_to_employee(
        {
            "name": name,
            "date_of_birth": date_of_birth,
            "phone": phone,
            "address": address,
            "drivers_license_number": drivers_license_number,
            "drivers_license_expiry": drivers_license_expiry,
            "health_card_number": health_card_number,
            "health_card_expiry": health_card_expiry,
            "date_of_hire": date_of_hire,
            "wage": wage,
            "notes": notes,
            "role": role,
            "specialty": specialty,
            "millwright_level": millwright_level,
        }
    )
    if not data["name"] or not data["role"]:
        return RedirectResponse(f"/employees/{employee_id}/edit", status_code=303)
    crud.update_employee(
        employee_id,
        data,
        history_effective_date=history_effective_date or None,
        promoted_to_team_lead=bool(promoted_to_team_lead),
        history_note=history_note or None,
    )
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.post("/employees/{employee_id}/history")
async def employee_add_history(
    employee_id: int,
    event_type: str = Form("wage"),
    effective_date: str = Form(""),
    amount: str = Form(""),
    note: str = Form(""),
):
    if not crud.get_employee(employee_id):
        return RedirectResponse("/employees", status_code=303)
    if event_type not in ("wage", "promotion"):
        event_type = "wage"
    if event_type == "promotion" and not (note or "").strip():
        note = "Promoted to Team Lead"
    from datetime import date

    effective = (effective_date or "").strip() or date.today().isoformat()
    crud.add_wage_history(
        employee_id,
        event_type,
        effective,
        amount=(amount or "").strip() or None,
        note=(note or "").strip() or None,
    )
    if event_type == "wage" and (amount or "").strip():
        emp = crud.get_employee(employee_id)
        if emp:
            emp["wage"] = (amount or "").strip()
            crud.update_employee(employee_id, emp)
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.post("/employees/{employee_id}/delete")
async def employee_delete(employee_id: int):
    crud.delete_employee(employee_id)
    return RedirectResponse("/employees", status_code=303)


@router.post("/employees/{employee_id}/documents")
async def upload_document(
    employee_id: int,
    doc_type: str = Form("other"),
    notes: str = Form(""),
    file: UploadFile = File(...),
):
    if not crud.get_employee(employee_id):
        return RedirectResponse("/employees", status_code=303)
    if not file.filename:
        return RedirectResponse(f"/employees/{employee_id}", status_code=303)
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        crud.add_document(
            employee_id,
            doc_type,
            file.filename,
            tmp_path,
            notes=notes or None,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return RedirectResponse(f"/employees/{employee_id}", status_code=303)


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: int):
    doc = crud.get_document(doc_id)
    if not doc:
        return RedirectResponse("/employees", status_code=303)
    path = UPLOADS_DIR / doc["stored_filename"]
    if not path.is_file():
        return RedirectResponse("/employees", status_code=303)
    return FileResponse(
        path,
        filename=doc["original_filename"],
        media_type="application/octet-stream",
    )


@router.post("/documents/{doc_id}/delete")
async def document_delete(doc_id: int):
    doc = crud.get_document(doc_id)
    eid = doc["employee_id"] if doc else None
    crud.delete_document(doc_id)
    if eid:
        return RedirectResponse(f"/employees/{eid}", status_code=303)
    return RedirectResponse("/employees", status_code=303)
