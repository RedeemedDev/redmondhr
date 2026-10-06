# APPLY — RedmondHR close-window lifecycle (2026-10-06)

Adam applies via archive extract. Unpack
`redmondhr-files-lifecycle-2026-10-06.tar.gz` over the project root
(relative paths), or copy the listed files from `/workspace/redmondhr`.

## Goal

Match normal desktop-app lifecycle: **start opens a window; closing that
window stops the server**. No separate stop shortcut for everyday use.

## What changed

| Path | Action |
|------|--------|
| `start-redmondhr.sh` | **replace** — background uvicorn, open browser, foreground wait; `EXIT`/`INT`/`TERM`/`HUP` trap stops via pid file |
| `stop-redmondhr.sh` | **replace** — header notes emergency-only (logic unchanged) |
| `install-desktop-shortcut.ps1` | **replace** — `WindowStyle=1` (normal console, not minimized) |
| `redmondhr.desktop` | **replace** — `Terminal=true` so Linux has a closable console |
| `install-desktop-shortcut.sh` | **replace** — quit hint in install message |
| `README.md` | **replace** — close-window UX + WindowStyle=1 one-liner |
| `APPLY-lifecycle.md` | **new** — this file |

`stop-redmondhr.sh` / `.bat` remain as **optional emergency** tools.

## Behaviour (`start-redmondhr.sh`)

1. Start uvicorn as a background child (not `nohup` / not disowned).
2. Write `data/redmondhr.pid`, open the browser (Windows browser under WSL).
3. Print: **Close this window to stop RedmondHR.**
4. Wait on the server process (or poll if attaching to an already-running pid).
5. On console close / Ctrl+C / HUP: trap kills uvicorn via the pid file.

## For Carl → Adam: PowerShell one-liner (recreate .lnk NOW)

Paste into **Windows PowerShell** (any folder). `WindowStyle=1` = normal console:

```powershell
$d="$env:USERPROFILE\OneDrive - Redmond Movers\Desktop"; if(!(Test-Path $d)){$d=[Environment]::GetFolderPath('Desktop')}; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'RedmondHR.lnk')); $s.TargetPath='wsl.exe'; $s.Arguments='-d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh'; $s.WorkingDirectory=$env:USERPROFILE; $s.WindowStyle=1; $s.Description='Start RedmondHR (WSL Ubuntu)'; $s.IconLocation='shell32.dll,165'; $s.Save(); Write-Host "Installed:" $s.FullName
```

Or re-run the installer after extract:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr\install-desktop-shortcut.ps1" -WslDistro Ubuntu -WslLinuxPath /home/adamredmond/workspace/redmondhr
```

## How to quit

**Close the RedmondHR console window** (or Ctrl+C). Do not rely on a separate stop icon for normal UX.

## After extract inside WSL

```bash
cd /home/adamredmond/workspace/redmondhr
chmod +x start-redmondhr.sh stop-redmondhr.sh install-desktop-shortcut.sh
```

Then recreate the Desktop `.lnk` with the one-liner above (old shortcuts used `WindowStyle=7` minimized and would hide the control console).

Do **not** push from the agent; Adam decides when to commit/push.
