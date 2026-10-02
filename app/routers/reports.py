"""Reports: upcoming birthdays and anniversaries (+ CSV export)."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app import crud
from app.config import DEFAULT_WINDOW_DAYS
from app.notifications import build_notifications, filter_by_kind

router = APIRouter(tags=["reports"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, days: int = DEFAULT_WINDOW_DAYS):
    if days < 1:
        days = DEFAULT_WINDOW_DAYS
    if days > 365:
        days = 365
    employees = crud.list_employees()
    all_items = build_notifications(employees, window_days=days)
    birthdays = filter_by_kind(all_items, {"birthday"})
    anniversaries = filter_by_kind(all_items, {"anniversary"})
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "birthdays": birthdays,
            "anniversaries": anniversaries,
            "window_days": days,
        },
    )


@router.get("/reports/export.csv")
async def reports_csv(days: int = DEFAULT_WINDOW_DAYS, kind: str = "all"):
    if days < 1:
        days = DEFAULT_WINDOW_DAYS
    employees = crud.list_employees()
    all_items = build_notifications(employees, window_days=days)
    if kind == "birthdays":
        items = filter_by_kind(all_items, {"birthday"})
    elif kind == "anniversaries":
        items = filter_by_kind(all_items, {"anniversary"})
    else:
        items = filter_by_kind(all_items, {"birthday", "anniversary"})

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["employee_id", "employee_name", "kind", "label", "event_date", "days", "status", "detail"]
    )
    for i in items:
        writer.writerow(
            [
                i["employee_id"],
                i["employee_name"],
                i["kind"],
                i["label"],
                i["event_date"],
                i["days"],
                i["status"],
                i.get("detail") or "",
            ]
        )
    buf.seek(0)
    filename = f"redmondhr_report_{kind}_{days}d.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
