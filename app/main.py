"""RedmondHR — manager-only HR toolkit for Redmond & Associates."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import crud
from app.auth import AuthMiddleware, password_required, verify_password
from app.config import (
    APP_NAME,
    COMPANY_NAME,
    DEFAULT_WINDOW_DAYS,
    LOAD_DEMO_ON_FIRST_RUN,
    SECRET_KEY,
    ensure_data_dirs,
)
from app.database import init_db, db_session
from app.demo_data import load_demo_data
from app.notifications import build_notifications, list_dismissed_keys, filter_dismissed, dismiss_reminder
from app.routers import employees, notifications, reports

BASE = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE / "templates"
STATIC_DIR = BASE / "static"

app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app.include_router(employees.router)
app.include_router(notifications.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup() -> None:
    ensure_data_dirs()
    init_db()
    if LOAD_DEMO_ON_FIRST_RUN and crud.employee_count() == 0:
        load_demo_data()


@app.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME}


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if not password_required():
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error, "app_name": APP_NAME},
    )


@app.post("/login")
async def login_submit(request: Request, password: str = Form("")):
    if verify_password(password):
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Incorrect password.",
            "app_name": APP_NAME,
        },
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    if password_required():
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    employees = crud.list_employees()
    items = build_notifications(employees, window_days=DEFAULT_WINDOW_DAYS)
    with db_session() as conn:
        dismissed = list_dismissed_keys(conn)
    items = filter_dismissed(items, dismissed)
    overdue = [i for i in items if i["status"] == "overdue"]
    soon = [i for i in items if i["status"] != "overdue"][:8]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "employee_count": len(employees),
            "overdue": overdue,
            "soon": soon,
            "window_days": DEFAULT_WINDOW_DAYS,
            "password_on": password_required(),
            "app_name": APP_NAME,
            "company_name": COMPANY_NAME,
        },
    )

@app.post("/reminders/dismiss")
async def reminders_dismiss(
    event_key: str = Form(...),
    employee_id: int = Form(...),
    kind: str = Form(...),
    event_date: str = Form(...),
    next: str = Form("/"),
):
    with db_session() as conn:
        dismiss_reminder(conn, event_key, employee_id, kind, event_date)
    return RedirectResponse(next, status_code=303)
