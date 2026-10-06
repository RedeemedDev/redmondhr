# APPLY — RedmondHR offline packaging + Windows Desktop shortcut (2026-10-06)

Adam applies via archive extract. Unpack
`redmondhr-files-packaging-win-desktop-2026-10-06.tar.gz` over the project root
(relative paths), or copy the listed files from `/workspace/redmondhr`.

## Files in this batch

| Path | Action |
|------|--------|
| `start-redmondhr.sh` | keep — Linux background launcher |
| `stop-redmondhr.sh` | keep — Linux stop via pid file |
| `start-redmondhr.bat` | **replace** — quieter Windows launcher (minimized / no linger) |
| `stop-redmondhr.bat` | keep — Windows stop |
| `redmondhr.desktop` | keep — Linux desktop entry template |
| `install-desktop-shortcut.sh` | keep — Linux Desktop + app-menu shortcuts |
| `install-desktop-shortcut.bat` | **new** — Windows installer wrapper |
| `install-desktop-shortcut.ps1` | **new** — resolves OneDrive Desktop, writes `.lnk` |
| `README.md` | **replace** — Windows OneDrive Desktop steps |
| `.gitignore` | keep — ignore `*.pid`, `*.log`, `logs/` |

## After extract (Windows — Adam's active Desktop)

His Desktop is OneDrive-synced:

`C:\Users\AdamRedmond\OneDrive - Redmond Movers\Desktop`

From **Command Prompt** or **PowerShell** in the `redmondhr` folder:

```bat
cd /d C:\path\to\redmondhr

REM One-time if .venv missing (needs internet once):
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

REM Install Desktop + Start Menu shortcut (resolves OneDrive Desktop):
install-desktop-shortcut.bat

REM Or start without a shortcut:
start-redmondhr.bat

REM When done:
stop-redmondhr.bat
```

Desktop-only (skip Start Menu):

```bat
install-desktop-shortcut.bat --no-start-menu
```

After install, double-click **RedmondHR** on the Desktop (or Start Menu). The
shortcut points at `start-redmondhr.bat` with an absolute path and runs
minimized.

Logs: `data\redmondhr.log` · Pid: `data\redmondhr.pid`

## After extract (Linux — AdamLenovo / optional)

```bash
cd /path/to/redmondhr
chmod +x start-redmondhr.sh stop-redmondhr.sh install-desktop-shortcut.sh

# One-time if .venv missing:
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

./start-redmondhr.sh
./install-desktop-shortcut.sh   # optional
./stop-redmondhr.sh
```

Do **not** push from the agent; Adam decides when to commit/push.
