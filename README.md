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

## Install & run (dev / foreground)

For day-to-day offline use on a work laptop, prefer **Offline / double-click start** below.

### Windows-friendly

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

## Offline / double-click start

Once dependencies are installed in `.venv`, you can run RedmondHR **without internet**. Starting opens a small console window; **closing that window stops the server** (normal app lifecycle).

### Windows Desktop + WSL Ubuntu (Adam's setup)

Adam develops in **Ubuntu/WSL** via VS Code. The project lives at:

`\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr`

His Windows Desktop (OneDrive) is typically:

`C:\Users\AdamRedmond\OneDrive - Redmond Movers\Desktop`

**Important:** CMD cannot use a UNC path as the current directory, and a `.lnk` cannot reliably set `TargetPath` / `WorkingDirectory` to a WSL UNC path (PowerShell `ArgumentException`). The Desktop shortcut therefore launches via `wsl.exe` with `--cd` (Linux path), and `WorkingDirectory` is `%USERPROFILE%` (or System32) — **never** the UNC project path.

#### One-time install inside WSL (needs internet once)

```bash
cd /home/adamredmond/workspace/redmondhr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x start-redmondhr.sh stop-redmondhr.sh
```

#### Drop RedmondHR.lnk on the OneDrive Desktop (PowerShell, run NOW)

From **Windows PowerShell** (any folder — no need to cd into the project):

```powershell
$d="$env:USERPROFILE\OneDrive - Redmond Movers\Desktop"; if(!(Test-Path $d)){$d=[Environment]::GetFolderPath('Desktop')}; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'RedmondHR.lnk')); $s.TargetPath='wsl.exe'; $s.Arguments='-d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh'; $s.WorkingDirectory=$env:USERPROFILE; $s.WindowStyle=1; $s.Description='Start RedmondHR (WSL Ubuntu)'; $s.IconLocation='shell32.dll,165'; $s.Save(); Write-Host "Installed:" $s.FullName
```

That creates **RedmondHR.lnk** which runs:

`wsl.exe -d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh`

#### Installer script (detects WSL UNC or accepts flags)

From PowerShell, pointing at the project UNC (or after extracting updates):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr\install-desktop-shortcut.ps1"
```

Or with explicit flags (no UNC detection needed):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr\install-desktop-shortcut.ps1" -WslDistro Ubuntu -WslLinuxPath /home/adamredmond/workspace/redmondhr
```

`install-desktop-shortcut.bat` also works when double-clicked from the WSL UNC share **without** `cd`ing into it; pass `--wsl Ubuntu /home/adamredmond/workspace/redmondhr` to force WSL mode. Use `--no-start-menu` to skip the Start Menu entry.

The installer also writes a **RedmondHR.bat** fallback on the Desktop (same `wsl.exe` command) in WSL mode.

Then double-click **RedmondHR** on the Desktop (or Start Menu). A **console window stays open** (WindowStyle normal). `start-redmondhr.sh` opens the **Windows** default browser when it detects WSL, then waits in the foreground. **Close that console window to stop RedmondHR** (Ctrl+C also stops). No separate stop shortcut is required for normal use.

#### Native Windows project folder (non-WSL)

If the repo is on a real drive letter (not `\\wsl...`), the installer writes a `.lnk` to `start-redmondhr.bat` instead:

```bat
install-desktop-shortcut.bat
start-redmondhr.bat
stop-redmondhr.bat
```

Adam's primary path is **WSL** (close-console-to-quit). Native `start-redmondhr.bat` still:
- Use `.venv` (exits with setup instructions if missing; prefers `pythonw` so the server has no console)
- Start uvicorn in the **background** on `http://127.0.0.1:8000`
- Open your default browser
- Append logs to `data\redmondhr.log`
- Write a pid file at `data\redmondhr.pid`
- If already running on port 8000, just open the browser
- Stop with `stop-redmondhr.bat` (native Windows does not yet use the close-window lifecycle)

#### Quit (normal)

**Close the RedmondHR console window** (or press Ctrl+C in it). The launcher EXIT trap stops uvicorn via the pid file.

#### Emergency stop (optional)

Only if the console was killed without cleanup, or you started uvicorn some other way:

```bash
# inside Ubuntu/WSL:
/home/adamredmond/workspace/redmondhr/stop-redmondhr.sh
# or:
wsl.exe -d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./stop-redmondhr.sh
```

### Linux (AdamLenovo / optional)

#### One-time install (needs internet once)

```bash
cd /path/to/redmondhr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Start / quit / shortcut

```bash
./start-redmondhr.sh              # console stays open; close it (or Ctrl+C) to quit
./install-desktop-shortcut.sh     # optional: ~/Desktop + app menu (Terminal=true)
# emergency only:
./stop-redmondhr.sh
```

The Linux installer writes a trusted-ish `.desktop` entry with absolute paths and `Terminal=true` so closing the terminal stops the server.

### Dev / foreground (reload)

For development with auto-reload, keep using the classic foreground command from **Install & run** above (`uvicorn … --reload`).

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
