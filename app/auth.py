"""Minimal optional manager password protection."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from app.config import MANAGER_PASSWORD

# Paths that never require auth (static + login itself)
PUBLIC_PATHS = {"/login", "/static", "/health"}


def password_required() -> bool:
    return bool(MANAGER_PASSWORD)


def verify_password(password: str) -> bool:
    if not MANAGER_PASSWORD:
        return True
    return password == MANAGER_PASSWORD


def is_authenticated(request: Request) -> bool:
    if not password_required():
        return True
    return request.session.get("authenticated") is True


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not password_required():
            return await call_next(request)
        if path.startswith("/static") or path in ("/login", "/health"):
            return await call_next(request)
        if path == "/logout":
            return await call_next(request)
        if is_authenticated(request):
            return await call_next(request)
        return RedirectResponse(url="/login", status_code=303)
