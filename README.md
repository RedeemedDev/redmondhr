# RedmondHR

Manager-only HR toolkit for **Redmond & Associates**.

RedmondHR helps a manager keep employee records, expiry reminders, roles/specialties, and review/disciplinary uploads on a local machine. It sits **alongside** company-wide cloud storage — large shared company documents and general info can continue to live there; this app focuses on manager HR workflows.

**Out of scope for this MVP:** cloud hosting, payroll, leave management, mobile apps, RigReady.

---

## Features

### Employee records (CRUD)
- Name, date of birth, phone, address
- Driver's license number + expiration
- Health card number + expiration (Canadian PII — treat as sensitive)
- Hire / start date (stored as both date_of_hire and company_start_date), wage, notes
- Role (Mover Year 1–3 / Team Lead) + Specialty (None / AZ / Millwright) + Millwright level when applicable
- Wage & promotion history (manual; Team Lead promotion checkbox on edit)
- Uploads: past reviews and disciplinary documents (files on disk; metadata in SQLite)

### Notifications (default 30-day window)
Upcoming **and** overdue:
- Driver's license expiry
- Health card expiry
- Birthday (shows turning age)
- Work anniversary (**uses hire / start date**)
- Follow-Up Orientation (**hire / start date + 21 days**)
- Probation Over (**hire / start date + 3 calendar months**)

Dismissed reminders can be Cleared from the dashboard / notifications page.

### Employees list sorting
Click column headers to sort (▴ ascending / ▾ descending). Search (`q`) is preserved when toggling.
- `?sort=name|hire|role|specialty|wage` with `?dir=asc|desc` (alias `order=`)
- Natural ascending: name A→Z; hire earliest→latest; role Year 1→Team Lead; specialty Millwright (Y2→Full Cert)→AZ→None; wage low→high when parseable
- Second click on the same header reverses; clicking a different header starts that column ascending

### Reports
- Upcoming birthdays
- Upcoming anniversaries (hire / start date)
- CSV export for birthdays, anniversaries, or both

---

## Requirements

- Python 3.10+ (3.11/3.12 recommended)
- Windows, macOS, or Linux

---

## Install & run (Windows-friendly)

Open **Command Prompt** or **PowerShell** in this folder (`redmondhr`).

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Optional manager password

By default the app is open for local use. To require a simple password in the browser:

**Windows (Command Prompt):**
```bat
set REDMONDHR_PASSWORD=your-password-here
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Windows (PowerShell):**
```powershell
$env:REDMONDHR_PASSWORD="your-password-here"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**macOS / Linux:**
```bash
export REDMONDHR_PASSWORD=your-password-here
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Other useful env vars:
| Variable | Default | Meaning |
|----------|---------|---------|
| `REDMONDHR_PASSWORD` | _(empty)_ | If set, login required |
| `REDMONDHR_SECRET_KEY` | dev default | Cookie signing secret |
| `REDMONDHR_DATA_DIR` | `./data` | SQLite + uploads folder |
| `REDMONDHR_WINDOW_DAYS` | `30` | Default notification window |
| `REDMONDHR_LOAD_DEMO` | `1` | Load demo employees when DB is empty |

---

## Demo / sample data

On first run with an empty database, a few **[DEMO]** employees are inserted automatically so notifications and reports have something to show.

To reload demo rows later:

```bat
.venv\Scripts\python scripts\load_demo.py
.venv\Scripts\python scripts\load_demo.py --force
```

Demo names are prefixed with `[DEMO]` and flagged in the UI. Delete them anytime.

---

## Data layout

```
data/
  redmondhr.db      # SQLite database
  uploads/          # Review / disciplinary files
```

Keep `data/` on a private disk or backup path. Do not commit it to git (see `.gitignore`).

---

## Pushing to GitHub

This project was created as a fresh local app. To put it in an empty GitHub repo:

```bat
git init
git add .
git commit -m "Initial RedmondHR MVP"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Do **not** commit `.venv/`, `data/`, or real passwords.

---

## Future notes

- **Multi-manager:** Today this is a single optional shared password for local use. A future path could add real user accounts, roles, and audit logs while keeping the same SQLite/local-first model (or migrating the DB to a shared host if the team outgrows one machine).
- **Cloud storage:** Continue using company cloud storage for large shared documents and org-wide information. RedmondHR is the manager toolkit for employee HR fields, reminders, and attached review/disciplinary files.

---

## Tech

- Python **FastAPI**
- **SQLite** (local)
- **Jinja2** templates + light **HTMX**
- Local `./data` for database and uploads
