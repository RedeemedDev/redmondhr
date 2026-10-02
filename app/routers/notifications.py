"""Notifications page — upcoming + overdue within window."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import crud
from app.config import DEFAULT_WINDOW_DAYS
from app.database import db_session
from app.notifications import (
    build_notifications,
    filter_dismissed,
    list_dismissed_keys,
)

router = APIRouter(tags=["notifications"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, days: int = DEFAULT_WINDOW_DAYS):
    if days < 1:
        days = DEFAULT_WINDOW_DAYS
    if days > 365:
        days = 365
    employees = crud.list_employees()
    items = build_notifications(employees, window_days=days)
    with db_session() as conn:
        dismissed = list_dismissed_keys(conn)
    items = filter_dismissed(items, dismissed)
    overdue = [i for i in items if i["status"] == "overdue"]
    upcoming = [i for i in items if i["status"] != "overdue"]
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "items": items,
            "overdue": overdue,
            "upcoming": upcoming,
            "window_days": days,
        },
    )