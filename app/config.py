"""Application configuration for RedmondHR."""
from __future__ import annotations

import os
from pathlib import Path

# Project root (parent of app/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Local data directory for SQLite + uploads (alongside company cloud storage for other docs)
DATA_DIR = Path(os.environ.get("REDMONDHR_DATA_DIR", BASE_DIR / "data"))
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "redmondhr.db"

# Optional manager password — if empty/unset, app is open (local-only use)
MANAGER_PASSWORD = os.environ.get("REDMONDHR_PASSWORD", "").strip()

# Session / cookie signing secret (override in production-ish local use)
SECRET_KEY = os.environ.get("REDMONDHR_SECRET_KEY", "redmondhr-dev-change-me")

# Notification / report default look-ahead window (days)
DEFAULT_WINDOW_DAYS = int(os.environ.get("REDMONDHR_WINDOW_DAYS", "30"))

# Load demo data on first run when DB is empty
LOAD_DEMO_ON_FIRST_RUN = os.environ.get("REDMONDHR_LOAD_DEMO", "1").strip() not in (
    "0",
    "false",
    "False",
    "",
)

APP_NAME = "RedmondHR"
COMPANY_NAME = "Redmond & Associates"


def ensure_data_dirs() -> None:
    """Create local data and uploads directories if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
